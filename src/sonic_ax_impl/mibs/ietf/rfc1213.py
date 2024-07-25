import ipaddress
import python_arptable
import re
import socket
import psutil
from enum import unique, Enum
from bisect import bisect_right

from sonic_ax_impl import mibs
from sonic_ax_impl.mibs import Namespace
from ax_interface.mib import MIBMeta, ValueType, MIBUpdater, MIBEntry, SubtreeMIBEntry, OverlayAdpaterMIBEntry, OidMIBEntry
from ax_interface.encodings import ObjectIdentifier
from ax_interface.util import mac_decimals, ip2byte_tuple

@unique
class DbTables(int, Enum):
    """
    Maps database tables names to SNMP sub-identifiers.
    https://tools.ietf.org/html/rfc1213#section-6.4

    REDIS_TABLE_NAME = (RFC1213 OID NUMBER)
    """

    # ifOperStatus ::= { ifEntry 8 }
    # ifLastChange :: { ifEntry 9 }
    # ifInOctets ::= { ifEntry 10 }
    SAI_PORT_STAT_IF_IN_OCTETS = 10
    # ifInUcastPkts ::= { ifEntry 11 }
    SAI_PORT_STAT_IF_IN_UCAST_PKTS = 11
    # ifInNUcastPkts ::= { ifEntry 12 }
    SAI_PORT_STAT_IF_IN_NON_UCAST_PKTS = 12
    # ifInDiscards ::= { ifEntry 13 }
    SAI_PORT_STAT_IF_IN_DISCARDS = 13
    # ifInErrors ::= { ifEntry 14 }
    SAI_PORT_STAT_IF_IN_ERRORS = 14
    # ifInUnknownProtos ::= { ifEntry 15 }
    SAI_PORT_STAT_IF_IN_UNKNOWN_PROTOS = 15
    # ifOutOctets  ::= { ifEntry 16 }
    SAI_PORT_STAT_IF_OUT_OCTETS = 16
    # ifOutUcastPkts ::= { ifEntry 17 }
    SAI_PORT_STAT_IF_OUT_UCAST_PKTS = 17
    # ifOutNUcastPkts ::= { ifEntry 18 }
    SAI_PORT_STAT_IF_OUT_NON_UCAST_PKTS = 18
    # ifOutDiscards ::= { ifEntry 19 }
    SAI_PORT_STAT_IF_OUT_DISCARDS = 19
    # ifOutErrors ::= { ifEntry 20 }
    SAI_PORT_STAT_IF_OUT_ERRORS = 20
    # ifOutQLen ::= { ifEntry 21 }
    SAI_PORT_STAT_IF_OUT_QLEN = 21

@unique
class IfTypes(int, Enum):
    """ IANA ifTypes """
    ethernetCsmacd = 6
    l3ipvlan       = 136
    ieee8023adLag  = 161

class ArpUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.db_conn = Namespace.init_namespace_dbs()
        self.arp_dest_map = {}
        self.arp_dest_list = []
        self.arp_dest_map = {}
        self.arp_dest_list = []
        self.neigh_key_list = {}

    def reinit_data(self):
        Namespace.connect_all_dbs(self.db_conn, mibs.APPL_DB)
        self.neigh_key_list = Namespace.dbs_keys_namespace(self.db_conn, mibs.APPL_DB, "NEIGH_TABLE:*")

    def _update_from_arptable(self):
        for entry in python_arptable.get_arp_table():
            dev = entry['Device']
            mac = entry['HW address']
            ip = entry['IP address']
            self._update_arp_info(dev, mac, ip)

    def _update_from_db(self):
        for neigh_key in self.neigh_key_list:
            neigh_str = neigh_key
            db_index = self.neigh_key_list[neigh_key]
            neigh_info = self.db_conn[db_index].get_all(mibs.APPL_DB, neigh_key, blocking=False)
            if not neigh_info:
                continue
            ip_family = neigh_info['family']
            if ip_family == "IPv4":
                dev, ip = mibs.get_neigh_info(neigh_str)
                mac = neigh_info['neigh']
                # eth0 interface in a namespace is not management interface
                # but is a part of docker0 bridge. Ignore this interface.
                if len(self.db_conn) > 1 and dev == "eth0":
                    continue
                self._update_arp_info(dev, mac, ip)

    def _update_arp_info(self, dev, mac, ip):
        if_index = mibs.get_index_from_str(dev)
        if if_index is None: return

        mactuple = mac_decimals(mac)
        machex = ''.join(chr(b) for b in mactuple)
        # if MAC is all zero
        #if not any(mac): continue

        iptuple = ip2byte_tuple(ip)

        subid = (if_index,) + iptuple
        self.arp_dest_map[subid] = machex
        self.arp_dest_list.append(subid)

    def update_data(self):
        self.arp_dest_map = {}
        self.arp_dest_list = []
        # Update arp table of host.
        # In case of multi-asic platform, get host arp table
        # from kernel and namespace arp table from NEIGH_TABLE in APP_DB
        # in each namespace.
        self._update_from_db()
        if len(self.db_conn) > 1:
            self._update_from_arptable()
        self.arp_dest_list.sort()

    def arp_dest(self, sub_id):
        return self.arp_dest_map.get(sub_id, None)

    def get_next(self, sub_id):
        right = bisect_right(self.arp_dest_list, sub_id)
        if right >= len(self.arp_dest_list):
            return None
        return self.arp_dest_list[right]

class NextHopUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.db_conn = Namespace.init_namespace_dbs()
        self.nexthop_map = {}
        self.route_list = []

    def reinit_connection(self):
        Namespace.connect_all_dbs(self.db_conn, mibs.APPL_DB)

    def update_data(self):
        """
        Update redis (caches config)
        Pulls the table references for each interface.
        """
        self.nexthop_map = {}
        self.route_list = []

        route_entries = Namespace.dbs_keys(self.db_conn, mibs.APPL_DB, "ROUTE_TABLE:*")
        if not route_entries:
            return

        for route_entry in route_entries:
            routestr = route_entry
            ipnstr = routestr[len("ROUTE_TABLE:"):]
            if ipnstr == "0.0.0.0/0":
                ipn = ipaddress.ip_network(ipnstr)
                ent = Namespace.dbs_get_all(self.db_conn, mibs.APPL_DB, routestr, blocking=False)
                if ent:
                    nexthops = ent.get("nexthop", None)
                    if nexthops is None:
                        mibs.logger.warning("Route has no nexthop: {} {}".format(routestr, str(ent)))
                        continue
                    for nh in nexthops.split(','):
                        # TODO: if ipn contains IP range, create more sub_id here
                        sub_id = ip2byte_tuple(ipn.network_address)
                        self.route_list.append(sub_id)
                        self.nexthop_map[sub_id] = ipaddress.ip_address(nh).packed
                        break # Just need the first nexthop

        self.route_list.sort()

    def nexthop(self, sub_id):
        return self.nexthop_map.get(sub_id, None)

    def get_next(self, sub_id):
        right = bisect_right(self.route_list, sub_id)
        if right >= len(self.route_list):
            return None

        return self.route_list[right]

class IfIndexUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.db_conn = Namespace.init_namespace_dbs()
        self.if_index_map = {}
        self.if_index_list = []

    def _update_if_index_info(self, dev, ip):
        if ip is None: return

        if_index = mibs.get_index_from_str(dev)
        if if_index is None: return

        try:
            ipaddr = ipaddress.ip_address(ip)
        except Exception as e:
            mibs.logger.warning("Failed to convert IP address '{}', error: {}.".format(ip, e))
            return

        iptuple = ip2byte_tuple(ip)
        ip_type = 1 if isinstance(ipaddr, ipaddress.IPv4Address) else 2
        ip_len = 4 if isinstance(ipaddr, ipaddress.IPv4Address) else 16
        subid = (ip_type, ip_len,) + iptuple
        self.if_index_map[subid] = if_index
        self.if_index_list.append(subid)

    def _getIfaceAddress(self, iface):
        return [x.address if x.family == socket.AddressFamily.AF_INET else x.address.replace('%{}'.format(iface), '') for x in psutil.net_if_addrs().get(iface, []) if x.address and (x.family == socket.AddressFamily.AF_INET or x.family == socket.AddressFamily.AF_INET6)]

    def _getIfaceBrdAddress(self, iface):
        return [x.broadcast if x.family == socket.AddressFamily.AF_INET else x.broadcast.replace('{}'.format(iface), '') for x in psutil.net_if_addrs().get(iface, []) if x.broadcast and (x.family == socket.AddressFamily.AF_INET or x.family == socket.AddressFamily.AF_INET6)]

    def update_data(self):
        self.if_index_map = {}
        self.if_index_list = []

        interfaces = Namespace.dbs_keys(self.db_conn, mibs.APPL_DB, "INTF_TABLE:*")
        loopback_intf_list = set()
        for interface in interfaces:
            ethTablePrefix = re.search(r"INTF_TABLE\:[A-Za-z]+[0-9]+\:[0-9.\:A-Fa-f]+", interface)
            if ethTablePrefix is None:
                continue
            else:
                dev = ethTablePrefix.group().split(':')[1]
                ip = ':'.join(ethTablePrefix.group().split(':')[2:])
                if dev.startswith('Loopback'):
                    loopback_intf_list.add(dev)
                    # continue
            self._update_if_index_info(dev, ip)

        # For the Loopback interface, since its link-local address is not recorded in APPLDB, its IP needs to be retrieved separately and updated.
        for dev in loopback_intf_list:
            for ip in self._getIfaceAddress(dev):
                self._update_if_index_info(dev, ip)

        for mgmt_ip in self._getIfaceAddress('eth0'):
            self._update_if_index_info("eth0", mgmt_ip)

        for ip in self._getIfaceAddress('docker0') + self._getIfaceBrdAddress('docker0'):
            self._update_if_index_info("docker0", ip)

        for ip in self._getIfaceAddress('Bridge'):
            self._update_if_index_info("Bridge", ip)

        self.if_index_list.sort()

    def get_if_index(self, sub_id):
        return self.if_index_map.get(sub_id, None)

    def get_next(self, sub_id):
        right = bisect_right(self.if_index_list, sub_id)
        if right >= len(self.if_index_list):
            return None

        return self.if_index_list[right]


class NetmaskUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.db_conn = Namespace.init_namespace_dbs()
        self.netmask_map = {}
        self.netmask_list = []

    def _update_netmask_info(self, dev, ip_mask):
        if ip_mask is None: return

        if_index = mibs.get_index_from_str(dev)
        if if_index is None: return

        try:
            netip = ipaddress.ip_network(ip_mask, False)
        except Exception as e:
            mibs.logger.warning("Failed to convert IP address '{}', error: {}.".format(ip_mask, e))
            return

        netmask = ip_mask.split('/')[1]
        netmask = int(netmask)
        ip = ip_mask.split('/')[0]

        iptuple = ip2byte_tuple(ip)
        ip_type = 1 if netip.version == 4 else 2
        ip_len = 4 if netip.version == 4 else 16
        subid = (ip_type, ip_len,) + iptuple

        netip = str(netip)
        netip = netip.split('/')[0]
        netiptuple = ip2byte_tuple(netip)

        # Create map beteen subid and OID
        oid_tuple = (1, 3, 6, 1, 2, 1, 4, 32, 1, 5)
        self.netmask_map[subid] = oid_tuple + (if_index,) + (ip_type, ip_len,)  + netiptuple + (netmask,)
        self.netmask_list.append(subid)

    def _getIfaceAddress(self, iface):
        return [ (x.address, x.netmask) if x.family == socket.AddressFamily.AF_INET else (x.address.replace('%{}'.format(iface), ''), x.netmask) for x in psutil.net_if_addrs().get(iface, []) if x.address and (x.family == socket.AddressFamily.AF_INET or x.family == socket.AddressFamily.AF_INET6)]

    def _getIfaceBrdAddress(self, iface):
        return [ (x.broadcast, x.netmask) if x.family == socket.AddressFamily.AF_INET else (x.broadcast.replace('{}'.format(iface), ''), x.netmask) for x in psutil.net_if_addrs().get(iface, []) if x.broadcast and (x.family == socket.AddressFamily.AF_INET or x.family == socket.AddressFamily.AF_INET6)]

    def update_data(self):
        self.netmask_map = {}
        self.netmask_list = []

        interfaces = Namespace.dbs_keys(self.db_conn, mibs.APPL_DB, "INTF_TABLE:*")
        for interface in interfaces:
            ethTablePrefix = re.search(r"INTF_TABLE\:[A-Za-z]+[0-9]+\:[0-9.\:A-Fa-f]+/[0-9]+", interface)
            if ethTablePrefix is None:
                continue
            else:
                dev = ethTablePrefix.group().split(':')[1]
                ip_mask = ':'.join(ethTablePrefix.group().split(':')[2:])

            self._update_netmask_info(dev, ip_mask)

        for ip, mask in self._getIfaceAddress('eth0'):
            ipaddr = ipaddress.ip_address(ip)

            if isinstance(ipaddr, ipaddress.IPv4Address):
                ip_mask = str(ipaddress.ip_interface('{}/{}'.format(ip, mask)))
            else:
                masktuple = ip2byte_tuple(mask)
                prefix_length = sum(bin(x).count("1") for x in masktuple)
                ip_mask = str(ipaddress.ip_interface('{}/{}'.format(ip, prefix_length)))

            self._update_netmask_info("eth0", ip_mask)

        for ip, mask in self._getIfaceAddress('docker0') + self._getIfaceBrdAddress('docker0'):
            ipaddr = ipaddress.ip_address(ip)

            if isinstance(ipaddr, ipaddress.IPv4Address):
                ip_mask = str(ipaddress.ip_interface('{}/{}'.format(ip, mask)))
            else:
                masktuple = ip2byte_tuple(mask)
                prefix_length = sum(bin(x).count("1") for x in masktuple)
                ip_mask = str(ipaddress.ip_interface('{}/{}'.format(ip, prefix_length)))

            self._update_netmask_info("docker0", ip_mask)

        self.netmask_list.sort()

    def get_netmask_oid(self, sub_id):
        return self.netmask_map.get(sub_id, None)

    def get_next(self, sub_id):
        right = bisect_right(self.netmask_list, sub_id)
        if right >= len(self.netmask_list):
            return None

        return self.netmask_list[right]

class IpMib(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.4'):
    arp_updater = ArpUpdater()
    nexthop_updater = NextHopUpdater()
    ifindex_updater = IfIndexUpdater()
    netmask_updater = NetmaskUpdater()

    ipRouteNextHop = \
        SubtreeMIBEntry('21.1.7', nexthop_updater, ValueType.IP_ADDRESS, nexthop_updater.nexthop)

    ipNetToMediaPhysAddress = \
        SubtreeMIBEntry('22.1.2', arp_updater, ValueType.OCTET_STRING, arp_updater.arp_dest)

    ipNetToIfIndex = \
        SubtreeMIBEntry('34.1.3', ifindex_updater, ValueType.INTEGER, ifindex_updater.get_if_index)

    ipNetToNetMask = \
        SubtreeMIBEntry('34.1.5', netmask_updater, ValueType.OBJECT_IDENTIFIER, netmask_updater.get_netmask_oid)

class InterfacesUpdater(MIBUpdater):

    RFC1213_MAX_SPEED = 4294967295

    def __init__(self):
        super().__init__()
        self.db_conn = Namespace.init_namespace_dbs()

        self.lag_name_if_name_map = {}
        self.if_name_lag_name_map = {}
        self.oid_lag_name_map = {}
        self.lag_sai_map = {}
        self.mgmt_oid_name_map = {}
        self.mgmt_alias_map = {}
        self.vlan_oid_name_map = {}
        self.vlan_name_map = {}
        self.rif_port_map = {}
        self.port_rif_map = {}

        # cache of interface counters
        self.if_counters = {}
        self.if_range = []
        self.if_name_map = {}
        self.if_alias_map = {}
        self.if_id_map = {}
        self.oid_name_map = {}
        self.rif_counters = {}

        self.namespace_db_map = Namespace.get_namespace_db_map(self.db_conn)

    def reinit_connection(self):
        Namespace.connect_namespace_dbs(self.db_conn)

    def reinit_data(self):
        """
        Subclass update interface information
        """
        self.if_name_map, \
        self.if_alias_map, \
        self.if_id_map, \
        self.oid_name_map = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_interface_tables, self.db_conn)
        """
        db_conn - will have db_conn to all namespace DBs and
        global db. First db in the list is global db.
        Use first global db to get management interface table.
        """
        self.mgmt_oid_name_map, \
        self.mgmt_alias_map = mibs.init_mgmt_interface_tables(self.db_conn[0])

        self.vlan_name_map, \
        self.vlan_oid_sai_map, \
        self.vlan_oid_name_map = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_vlan_tables, self.db_conn)

        self.rif_port_map, \
        self.port_rif_map = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_rif_tables, self.db_conn)

        self.lag_name_if_name_map, \
        self.if_name_lag_name_map, \
        self.oid_lag_name_map, \
        self.lag_sai_map, self.sai_lag_map = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_lag_tables, self.db_conn)

    def update_data(self):
        """
        Update redis (caches config)
        Pulls the table references for each interface.
        """

        self.update_if_counters()
        self.update_rif_counters()

        self.aggregate_counters()

        self.if_range = sorted(list(self.oid_name_map.keys()) +
                               list(self.oid_lag_name_map.keys()) +
                               list(self.mgmt_oid_name_map.keys()) +
                               list(self.vlan_oid_name_map.keys()))
        self.if_range = [(i,) for i in self.if_range]

    def update_if_counters(self):
        for sai_id_key in self.if_id_map:
            namespace, sai_id = mibs.split_sai_id_key(sai_id_key)
            if_idx = mibs.get_index_from_str(self.if_id_map[sai_id_key])
            counters_db_data = self.namespace_db_map[namespace].get_all(mibs.COUNTERS_DB,
                                                                        mibs.counter_table(sai_id))
            if counters_db_data is None:
                counters_db_data = {}
            self.if_counters[if_idx] = {
                counter: int(value) for counter, value in counters_db_data.items()
            }

    def update_rif_counters(self):
        rif_sai_ids = list(self.rif_port_map) + list(self.vlan_name_map)
        for sai_id in rif_sai_ids:
            counters_db_data = Namespace.dbs_get_all(self.db_conn, mibs.COUNTERS_DB,
                                                     mibs.counter_table(mibs.split_sai_id_key(sai_id)[1]))
            if counters_db_data is None:
                counters_db_data = {}
            self.rif_counters[sai_id] = {
                counter: int(value) for counter, value in counters_db_data.items()
            }

    def get_next(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query.
        :return: the next sub id.
        """
        right = bisect_right(self.if_range, sub_id)
        if right == len(self.if_range):
            return None
        return self.if_range[right]

    def get_oid(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query.
        :return: the interface OID.
        """
        if sub_id not in self.if_range:
            return

        return sub_id[0]

    def if_index(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query.
        :return: the 0-based interface ID.
        """
        if sub_id:
            return self.get_oid(sub_id) - 1

    def interface_description(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query.
        :return: the interface description (simply the name) for the respective sub_id
        """
        oid = self.get_oid(sub_id)
        if not oid:
            return

        if oid in self.oid_lag_name_map:
            return self.oid_lag_name_map[oid]
        elif oid in self.mgmt_oid_name_map:
            return self.mgmt_alias_map[self.mgmt_oid_name_map[oid]]
        elif oid in self.vlan_oid_name_map:
            return self.vlan_oid_name_map[oid]

        return self.if_alias_map[self.oid_name_map[oid]]

    def _get_counter(self, oid, table_name):
        """
        :param sub_id: The interface OID.
        :param table_name: the redis table (either IntEnum or string literal) to query.
        :return: the counter for the respective sub_id/table.
        """
        # Enum.name or table_name = 'name_of_the_table'
        # Example: 
        # table_name = <DbTables.SAI_PORT_STAT_IF_OUT_ERRORS: 20>
        # _table_name = 'SAI_PORT_STAT_IF_OUT_ERRORS'
        _table_name = getattr(table_name, 'name', table_name)

        try:
            counter_value = self.if_counters[oid][_table_name]
            # truncate to 32-bit counter (database implements 64-bit counters)
            counter_value = counter_value & 0x00000000ffffffff
            # done!
            return counter_value
        except KeyError as e:
            mibs.logger.warning("SyncD 'COUNTERS_DB' missing attribute '{}'.".format(e))
            return None

    def aggregate_counters(self):
        """
        For ports with l3 router interfaces l3 drops may be counted separately (RIF counters)
        add l3 drops to l2 drop counters cache according to mapping

        For l3vlan map l3 counters to l2 counters
        """
        for rif_sai_id, port_sai_id in self.rif_port_map.items():
            if port_sai_id in self.if_id_map:
                port_idx = mibs.get_index_from_str(self.if_id_map[port_sai_id])
                for port_counter_name, rif_counter_name in mibs.RIF_DROPS_AGGR_MAP.items():
                    self.if_counters[port_idx][port_counter_name] = \
                    self.if_counters[port_idx].get(port_counter_name, 0) + \
                    self.rif_counters[rif_sai_id].get(rif_counter_name, 0)

        for vlan_sai_id, vlan_name in self.vlan_name_map.items():
            for port_counter_name, rif_counter_name in mibs.RIF_COUNTERS_AGGR_MAP.items():
                vlan_idx = mibs.get_index_from_str(vlan_name)
                vlan_rif_counters = self.rif_counters[vlan_sai_id]
                if rif_counter_name in vlan_rif_counters:
                    self.if_counters.setdefault(vlan_idx, {})
                    self.if_counters[vlan_idx][port_counter_name] = \
                        vlan_rif_counters[rif_counter_name]


    def get_counter(self, sub_id, table_name):
        """
        :param sub_id: The 1-based sub-identifier query.
        :param table_name: the redis table (either IntEnum or string literal) to query.
        :return: the counter for the respective sub_id/table.
        """

        oid = self.get_oid(sub_id)
        if not oid:
            return

        if oid in self.mgmt_oid_name_map:
            # TODO: mgmt counters not available through SNMP right now
            # COUNTERS DB does not have support for generic linux (mgmt) interface counters
            return 0
        elif oid in self.oid_lag_name_map:
            counter_value = 0
            # Sum the values of this counter for all ports in the LAG.
            # Example: 
            # table_name = <DbTables.SAI_PORT_STAT_IF_OUT_ERRORS: 20>
            # oid = 1001
            # self.oid_lag_name_map = {1001: 'PortChannel01', 1002: 'PortChannel02', 1003: 'PortChannel03'}
            # self.oid_lag_name_map[oid] = 'PortChannel01'
            # self.lag_name_if_name_map = {'PortChannel01': ['Ethernet112'], 'PortChannel02': ['Ethernet116'], 'PortChannel03': ['Ethernet120']}
            # self.lag_name_if_name_map['PortChannel01'] = ['Ethernet112']
            # mibs.get_index_from_str('Ethernet112') = 113 (because Ethernet N = N + 1)
            # self._get_counter retrieves the counter per oid and table.
            for lag_member in self.lag_name_if_name_map[self.oid_lag_name_map[oid]]:
                counter_value += self._get_counter(mibs.get_index_from_str(lag_member), table_name)
            # Check if we need to add a router interface count.
            # Example:
            # self.lag_sai_map = {'PortChannel01': '2000000000006', 'PortChannel02': '2000000000005', 'PortChannel03': '2000000000004'}
            # self.port_rif_map = {'2000000000006': '6000000000006', '2000000000005': '6000000000005', '2000000000004': '6000000000004'}
            # self.rif_port_map = {'6000000000006': '2000000000006', '6000000000005': '2000000000005', '6000000000004': '2000000000004'}
            # self.lag_sai_map['PortChannel01'] = '2000000000006'
            # self.port_rif_map['2000000000006'] = '6000000000006'
            sai_lag_id = self.lag_sai_map[self.oid_lag_name_map[oid]]
            sai_lag_rif_id = self.port_rif_map[sai_lag_id] if sai_lag_id in self.port_rif_map else None
            if sai_lag_rif_id in self.rif_port_map:
                # Extract the 'name' part of 'table_name'.
                # Example: 
                # table_name = <DbTables.SAI_PORT_STAT_IF_OUT_ERRORS: 20>
                # _table_name = 'SAI_PORT_STAT_IF_OUT_ERRORS'
                table_name = getattr(table_name, 'name', table_name)
                # Find rif counter table if applicable and add the count for this table.
                # Example:
                # mibs.RIF_DROPS_AGGR_MAP = {'SAI_PORT_STAT_IF_IN_ERRORS': 'SAI_ROUTER_INTERFACE_STAT_IN_ERROR_PACKETS', 'SAI_PORT_STAT_IF_OUT_ERRORS': 'SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS'}
                # self.rif_counters['6000000000006'] = {'SAI_ROUTER_INTERFACE_STAT_IN_PACKETS': 6, ... 'SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS': 6, ...} 
                if table_name in mibs.RIF_DROPS_AGGR_MAP:
                    rif_table_name = mibs.RIF_DROPS_AGGR_MAP[table_name]
                    counter_value += self.rif_counters[sai_lag_rif_id].get(rif_table_name, 0)
            # truncate to 32-bit counter
            return counter_value & 0x00000000ffffffff
        else:
            return self._get_counter(oid, table_name)

    def get_if_number(self):
        """
        :return: the number of interfaces.
        """
        return len(self.if_range)

    def _get_if_entry(self, sub_id):
        """
        :param oid: The 1-based sub-identifier query.
        :return: the DB entry for the respective sub_id.
        """
        oid = self.get_oid(sub_id)
        if not oid:
            return

        if_table = ""
        # Once PORT_TABLE will be moved to CONFIG DB
        # we will get entry from CONFIG_DB for all cases
        db = mibs.APPL_DB
        if oid in self.oid_lag_name_map:
            if_table = mibs.lag_entry_table(self.oid_lag_name_map[oid])
        elif oid in self.mgmt_oid_name_map:
            if_table = mibs.mgmt_if_entry_table(self.mgmt_oid_name_map[oid])
            db = mibs.CONFIG_DB
        elif oid in self.vlan_oid_name_map:
            if_table = mibs.vlan_entry_table(self.vlan_oid_name_map[oid])
        elif oid in self.oid_name_map:
            if_table = mibs.if_entry_table(self.oid_name_map[oid])
        else:
            return None

        return Namespace.dbs_get_all(self.db_conn, db, if_table, blocking=True)

    def _get_if_entry_state_db(self, sub_id):
        """
        :param oid: The 1-based sub-identifier query.
        :return: the DB entry for the respective sub_id.
        """
        oid = self.get_oid(sub_id)
        if not oid:
            return

        if_table = ""
        db = mibs.STATE_DB
        if oid in self.mgmt_oid_name_map:
            mgmt_if_name = self.mgmt_oid_name_map[oid]
            if_table = mibs.mgmt_if_entry_table_state_db(mgmt_if_name)
        else:
            return None

        return Namespace.dbs_get_all(self.db_conn, db, if_table, blocking=False)

    def _get_status(self, sub_id, key):
        """
        :param sub_id: The 1-based sub-identifier query.
        :param key: Status to get (admin_state or oper_state).
        :return: state value for the respective sub_id/key.
        """
        status_map = {
            "up": 1,
            "down": 2,
            "testing": 3,
            "unknown": 4,
            "dormant": 5,
            "notPresent": 6,
            "lowerLayerDown": 7
        }

        # Once PORT_TABLE will be moved to CONFIG DB
        # we will get rid of this if-else
        # and read oper status from STATE_DB
        if self.get_oid(sub_id) in self.mgmt_oid_name_map and key == "oper_status":
            entry = self._get_if_entry_state_db(sub_id)
        else:
            entry = self._get_if_entry(sub_id)

        if not entry:
            return status_map.get("unknown")

        # Note: If interface never become up its state won't be reflected in DB entry
        # If state key is not in DB entry assume interface is down
        state = entry.get(key, "down")

        return status_map.get(state, status_map["down"])

    def get_admin_status(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query.
        :return: admin state value for the respective sub_id.
        """
        return self._get_status(sub_id, "admin_status")

    def get_oper_status(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query.
        :return: oper state value for the respective sub_id.
        """
        return self._get_status(sub_id, "oper_status")

    def get_mtu(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query.
        :return: MTU value for the respective sub_id.
        """
        entry = self._get_if_entry(sub_id)
        if not entry:
            return

        return int(entry.get("mtu", 0))

    def get_speed_bps(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query.
        :return: min of RFC1213_MAX_SPEED or speed value for the respective sub_id.
        """
        entry = self._get_if_entry(sub_id)
        if not entry:
            return

        speed = int(entry.get("speed", 0))
        # speed is reported in Mbps in the db
        return min(self.RFC1213_MAX_SPEED, speed * 1000000)

    def get_if_type(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query.
        :return: integer representing a type according to textual convention

        ethernetCsmacd(6), -- for all ethernet-like interfaces,
                           -- regardless of speed, as per RFC3635
        l3ipvlan(136)      -- Layer 3 Virtual LAN using IP
        ieee8023adLag(161) -- IEEE 802.3ad Link Aggregate
        """
        oid = self.get_oid(sub_id)
        if not oid:
            return

        if oid in self.oid_lag_name_map:
            return IfTypes.ieee8023adLag
        elif oid in self.vlan_oid_name_map:
            return IfTypes.l3ipvlan
        else:
            return IfTypes.ethernetCsmacd

class InterfacesMIB(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.2'):
    """
    'interfaces' https://tools.ietf.org/html/rfc1213#section-3.5
    """

    if_updater = InterfacesUpdater()

    oidtree_updater = mibs.RedisOidTreeUpdater(prefix_str='1.3.6.1.2.1.2')

    # (subtree, value_type, callable_, *args, handler=None)
    ifNumber = MIBEntry('1', ValueType.INTEGER, if_updater.get_if_number)

    # ifTable ::= { interfaces 2 }
    # ifEntry ::= { ifTable 1 }

    ifIndex = \
        SubtreeMIBEntry('2.1.1', if_updater, ValueType.INTEGER, if_updater.if_index)

    ifDescr = \
        SubtreeMIBEntry('2.1.2', if_updater, ValueType.OCTET_STRING, if_updater.interface_description)

    ifType = \
        SubtreeMIBEntry('2.1.3', if_updater, ValueType.INTEGER, if_updater.get_if_type)

    ifMtu = \
        SubtreeMIBEntry('2.1.4', if_updater, ValueType.INTEGER, if_updater.get_mtu)

    ifSpeed = \
        SubtreeMIBEntry('2.1.5', if_updater, ValueType.GAUGE_32, if_updater.get_speed_bps)

    # FIXME Placeholder.
    ifPhysAddress = \
        SubtreeMIBEntry('2.1.6', if_updater, ValueType.OCTET_STRING, lambda sub_id: '')

    ifAdminStatus = \
        SubtreeMIBEntry('2.1.7', if_updater, ValueType.INTEGER, if_updater.get_admin_status)

    ifOperStatus = \
        SubtreeMIBEntry('2.1.8', if_updater, ValueType.INTEGER, if_updater.get_oper_status)

    # FIXME Placeholder.
    ifLastChange = \
        SubtreeMIBEntry('2.1.9', if_updater, ValueType.TIME_TICKS, lambda sub_id: 0)

    ifInOctets = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.10', if_updater, ValueType.COUNTER_32, if_updater.get_counter,
                           DbTables(10)),
            OidMIBEntry('2.1.10', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    ifInUcastPkts = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.11', if_updater, ValueType.COUNTER_32, if_updater.get_counter,
                           DbTables(11)),
            OidMIBEntry('2.1.11', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    ifInNUcastPkts = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.12', if_updater, ValueType.COUNTER_32, if_updater.get_counter,
                           DbTables(12)),
            OidMIBEntry('2.1.12', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    ifInDiscards = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.13', if_updater, ValueType.COUNTER_32, if_updater.get_counter,
                           DbTables(13)),
            OidMIBEntry('2.1.13', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    ifInErrors = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.14', if_updater, ValueType.COUNTER_32, if_updater.get_counter,
                           DbTables(14)),
            OidMIBEntry('2.1.14', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    ifInUnknownProtos = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.15', if_updater, ValueType.COUNTER_32, if_updater.get_counter,
                           DbTables(15)),
            OidMIBEntry('2.1.15', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    ifOutOctets = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.16', if_updater, ValueType.COUNTER_32, if_updater.get_counter,
                           DbTables(16)),
            OidMIBEntry('2.1.16', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    ifOutUcastPkts = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.17', if_updater, ValueType.COUNTER_32, if_updater.get_counter,
                           DbTables(17)),
            OidMIBEntry('2.1.17', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    ifOutNUcastPkts = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.18', if_updater, ValueType.COUNTER_32, if_updater.get_counter,
                           DbTables(18)),
            OidMIBEntry('2.1.18', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    ifOutDiscards = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.19', if_updater, ValueType.COUNTER_32, if_updater.get_counter,
                           DbTables(19)),
            OidMIBEntry('2.1.19', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    ifOutErrors = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.20', if_updater, ValueType.COUNTER_32, if_updater.get_counter,
                           DbTables(20)),
            OidMIBEntry('2.1.20', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    ifOutQLen = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.21', if_updater, ValueType.GAUGE_32, if_updater.get_counter,
                           DbTables(21)),
            OidMIBEntry('2.1.21', ValueType.GAUGE_32, oidtree_updater.get_oidvalue)
        )

    # FIXME Placeholder
    ifSpecific = \
        SubtreeMIBEntry('2.1.22', if_updater, ValueType.OBJECT_IDENTIFIER, lambda sub_id: ObjectIdentifier.null_oid())

class sysNameUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.db_conn = mibs.init_db()
        self.hostname = socket.gethostname()

    def reinit_data(self):
        self.db_conn.connect(self.db_conn.CONFIG_DB)
        device_metadata = self.db_conn.get_all(self.db_conn.CONFIG_DB, "DEVICE_METADATA|localhost")

        if device_metadata and device_metadata.get('hostname'):
            self.hostname = device_metadata['hostname']

    def update_data(self):
        return

    def get_sys_name(self):
        """
        Subclass update interface information
        """
        return self.hostname


class SysNameMIB(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.1.5'):
    updater = sysNameUpdater()

    sysName = MIBEntry('0', ValueType.OCTET_STRING, updater.get_sys_name)
