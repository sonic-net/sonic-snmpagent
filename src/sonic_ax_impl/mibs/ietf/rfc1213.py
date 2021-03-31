import ipaddress
import python_arptable
import socket
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
    ieee8023adLag = 161

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
            if neigh_info is None:
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
                ent = Namespace.dbs_get_all(self.db_conn, mibs.APPL_DB, routestr, blocking=True)
                nexthops = ent["nexthop"]
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

class IpMib(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.4'):
    arp_updater = ArpUpdater()
    nexthop_updater = NextHopUpdater()

    ipRouteNextHop = \
        SubtreeMIBEntry('21.1.7', nexthop_updater, ValueType.IP_ADDRESS, nexthop_updater.nexthop)

    ipNetToMediaPhysAddress = \
        SubtreeMIBEntry('22.1.2', arp_updater, ValueType.OCTET_STRING, arp_updater.arp_dest)

class InterfacesUpdater(MIBUpdater):

    RFC1213_MAX_SPEED = 4294967295

    def __init__(self):
        super().__init__()
        self.db_conn = Namespace.init_namespace_dbs()

        self.lag_name_if_name_map = {}
        self.if_name_lag_name_map = {}
        self.oid_lag_name_map = {}
        self.mgmt_oid_name_map = {}
        self.mgmt_alias_map = {}

        # cache of interface counters
        self.if_counters = {}
        self.if_range = []
        self.if_name_map = {}
        self.if_alias_map = {}
        self.if_id_map = {}
        self.oid_name_map = {}
        self.namespace_db_map = Namespace.get_namespace_db_map(self.db_conn)

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

    def update_data(self):
        """
        Update redis (caches config)
        Pulls the table references for each interface.
        """
        for sai_id_key in self.if_id_map:
            namespace, sai_id = mibs.split_sai_id_key(sai_id_key)
            if_idx = mibs.get_index_from_str(self.if_id_map[sai_id_key])
            self.if_counters[if_idx] = self.namespace_db_map[namespace].get_all(mibs.COUNTERS_DB, \
                    mibs.counter_table(sai_id), blocking=True)

        self.lag_name_if_name_map, \
        self.if_name_lag_name_map, \
        self.oid_lag_name_map, _ = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_lag_tables, self.db_conn)

        self.if_range = sorted(list(self.oid_name_map.keys()) +
                               list(self.oid_lag_name_map.keys()) +
                               list(self.mgmt_oid_name_map.keys()))
        self.if_range = [(i,) for i in self.if_range]

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
            return self.get_oid(sub_id)

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

        return self.if_alias_map[self.oid_name_map[oid]]

    def _get_counter(self, oid, table_name):
        """
        :param sub_id: The interface OID.
        :param table_name: the redis table (either IntEnum or string literal) to query.
        :return: the counter for the respective sub_id/table.
        """
        # Enum.name or table_name = 'name_of_the_table'
        _table_name = getattr(table_name, 'name', table_name)

        try:
            counter_value = self.if_counters[oid][_table_name]
            # truncate to 32-bit counter (database implements 64-bit counters)
            counter_value = int(counter_value) & 0x00000000ffffffff
            # done!
            return counter_value
        except KeyError as e:
            mibs.logger.warning("SyncD 'COUNTERS_DB' missing attribute '{}'.".format(e))
            return None

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
            for lag_member in self.lag_name_if_name_map[self.oid_lag_name_map[oid]]:
                counter_value += self._get_counter(mibs.get_index_from_str(lag_member), table_name)

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
        ieee8023adLag(161) -- IEEE 802.3ad Link Aggregate
        """
        oid = self.get_oid(sub_id)
        if not oid:
            return

        if oid in self.oid_lag_name_map:
            return IfTypes.ieee8023adLag
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
