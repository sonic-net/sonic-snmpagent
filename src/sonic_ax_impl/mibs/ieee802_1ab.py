"""
http://www.ieee802.org/1/files/public/MIBs/LLDP-MIB-200505060000Z.txt
"""
import ipaddress
from enum import Enum, unique
from bisect import bisect_right

from swsssdk import port_util
from sonic_ax_impl import mibs, logger
from sonic_ax_impl.mibs import Namespace
from ax_interface.util import ip2byte_tuple
from ax_interface import MIBMeta, SubtreeMIBEntry, MIBEntry, MIBUpdater, ValueType


@unique
class LLDPRemoteTables(int, Enum):
    """
    REDIS_KEY_NAME <--> OID_INDEX
    """
    lldp_rem_time_mark = 1
    lldp_rem_local_port_num = 2
    lldp_rem_index = 3
    lldp_rem_chassis_id_subtype = 4
    lldp_rem_chassis_id = 5
    lldp_rem_port_id_subtype = 6
    lldp_rem_port_id = 7
    lldp_rem_port_desc = 8
    lldp_rem_sys_name = 9
    lldp_rem_sys_desc = 10
    lldp_rem_sys_cap_supported = 11
    lldp_rem_sys_cap_enabled = 12


@unique
class LLDPLocalChassis(int, Enum):
    """
    REDIS_KEY_NAME <--> OID_INDEX
    """
    lldp_loc_chassis_id_subtype = 1
    lldp_loc_chassis_id = 2
    lldp_loc_sys_name = 3
    lldp_loc_sys_desc = 4
    lldp_loc_sys_cap_supported = 5
    lldp_loc_sys_cap_enabled = 6


class ManAddrConst:
    man_addr_if_id = 0
    """
    Reference [RFC2453][RFC2677][RFC2858]
    Address Family Numbers
    1	IP (IP version 4)
    2	IP6 (IP version 6)
    """
    man_addr_subtype_ipv4 = 1
    man_addr_subtype_ipv6 = 2
    """
    The enumeration 'ifIndex(2)' represents interface identifier
    based on the ifIndex MIB object.
    """
    man_addr_if_subtype = 2
    """
    "The total length of the management address subtype and the
    management address fields in LLDPDUs transmitted by the
    local LLDP agent.
    """
    man_addr_len = 5
    """
    "The OID value used to identify the type of hardware component
    or protocol entity associated with the management address
    advertised by the local system agent."
    """
    man_addr_oid = (1, 3, 6, 1, 2, 1, 2, 2, 1, 1)

def poll_lldp_entry_updates(pubsub):
    ret = None, None, None
    msg = pubsub.get_message()
    if not msg:
        return ret

    try:
        interface = msg["channel"].split(":")[-1]
        data = msg['data']
    except (KeyError, AttributeError) as e:
        logger.error("Invalid msg when polling for lldp updates: {}\n"
                     "The error seems to be: {}".format(msg, e))
        return ret

    # get interface from interface name
    if_index = port_util.get_index_from_str(interface)

    if if_index is None:
        # interface name invalid, skip this entry
        logger.warning("Invalid interface name in {} in APP_DB, skipping"
                       .format(interface))
        return ret
    return data, interface, if_index

def parse_sys_capability(sys_cap):
    return bytearray([int (x, 16) for x in sys_cap.split()])

class LLDPLocalSystemDataUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()

        self.db_conn = Namespace.init_namespace_dbs()
        self.loc_chassis_data = {}

    def reinit_data(self):
        """
        Subclass update data routine.
        """
        # establish connection to application database.
        Namespace.connect_all_dbs(self.db_conn, mibs.APPL_DB)
        self.loc_chassis_data = Namespace.dbs_get_all(self.db_conn, mibs.APPL_DB, mibs.LOC_CHASSIS_TABLE)
        if self.loc_chassis_data:
            self.loc_chassis_data['lldp_loc_sys_cap_supported'] = parse_sys_capability(self.loc_chassis_data['lldp_loc_sys_cap_supported'])
            self.loc_chassis_data['lldp_loc_sys_cap_enabled'] = parse_sys_capability(self.loc_chassis_data['lldp_loc_sys_cap_enabled'])

    def update_data(self):
        """
        Avoid NotImplementedError
        The data is mostly static, reinit it once a minute is enough.
        """
        pass

    def table_lookup(self, table_name):
        try:
            _table_name = getattr(table_name, 'name', table_name)
            return self.loc_chassis_data[_table_name]
        except KeyError as e:
            logger.warning(" 0 - b'LOC_CHASSIS' missing attribute '{}'.".format(e))
            return None

    def table_lookup_integer(self, table_name):
        subtype_str = self.table_lookup(table_name)
        return int(subtype_str) if subtype_str is not None else None


class LocPortUpdater(MIBUpdater):

    def __init__(self):
        super().__init__()

        self.db_conn = Namespace.init_namespace_dbs()
        # establish connection to application database.
        Namespace.connect_all_dbs(self.db_conn, mibs.APPL_DB)
        self.if_name_map = {}
        self.if_alias_map = {}
        self.if_id_map = {}
        self.oid_name_map = {}

        self.mgmt_oid_name_map = {}
        self.mgmt_alias_map = {}

        self.if_range = []

        # cache of port data
        # { if_name -> { 'key': 'value' } }
        self.loc_port_data = {}
        self.pubsub = [None] * len(self.db_conn)

    def reinit_data(self):
        """
        Subclass update interface information
        """
        self.if_name_map, \
        self.if_alias_map, \
        self.if_id_map, \
        self.oid_name_map = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_interface_tables, self.db_conn)

        self.mgmt_oid_name_map, \
        self.mgmt_alias_map = mibs.init_mgmt_interface_tables(self.db_conn[0])

        # merge dataplane and mgmt ports
        self.oid_name_map.update(self.mgmt_oid_name_map)
        self.if_alias_map.update(self.mgmt_alias_map)

        self.if_range = []
        # get local port kvs from APP_BD's PORT_TABLE
        self.loc_port_data = {}
        for if_oid, if_name in self.oid_name_map.items():
            self.update_interface_data(if_name)
            self.if_range.append((if_oid, ))
        self.if_range.sort()
        if not self.loc_port_data:
            logger.debug("0 - b'PORT_TABLE' is empty. No local port information could be retrieved.")

    def _get_if_entry(self, if_name):
        if_table = ""

        # Once PORT_TABLE will be moved to CONFIG DB
        # we will get entry from CONFIG_DB for all cases
        db = mibs.APPL_DB
        if if_name in self.if_name_map:
            if_table = mibs.if_entry_table(if_name)
        elif if_name in self.mgmt_oid_name_map.values():
            if_table = mibs.mgmt_if_entry_table(if_name)
            db = mibs.CONFIG_DB
        else:
            return None

        return Namespace.dbs_get_all(self.db_conn, db, if_table, blocking=True)

    def update_interface_data(self, if_name):
        """
        Update data from the DB for a single interface
        """

        loc_port_kvs = self._get_if_entry(if_name)
        if not loc_port_kvs:
            return
        self.loc_port_data.update({if_name: loc_port_kvs})

    def get_next(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query.
        :return: the next sub id.
        """
        right = bisect_right(self.if_range, sub_id)
        if right == len(self.if_range):
            return None
        return self.if_range[right]

    def _update_per_namespace_data(self, pubsub):
        """
        Listen to updates in APP DB, update local cache
        """
        while True:
            data, interface, if_id = poll_lldp_entry_updates(pubsub)

            if not data:
                break

            if "set" in data:
                self.update_interface_data(interface)

    def update_data(self):
        for i in range(len(self.db_conn)):
            if not self.pubsub[i]:
                pattern = mibs.lldp_entry_table('*')
                self.pubsub[i] = mibs.get_redis_pubsub(self.db_conn[i], self.db_conn[i].APPL_DB, pattern)
            self._update_per_namespace_data(self.pubsub[i])

    def local_port_num(self, sub_id):
        if len(sub_id) == 0:
            return None
        sub_id = sub_id[0]
        if sub_id not in self.oid_name_map:
            return None
        return int(sub_id)

    def local_port_id(self, sub_id):
        if len(sub_id) == 0:
            return None
        sub_id = sub_id[0]
        if sub_id not in self.oid_name_map:
            return None
        if_name = self.oid_name_map[sub_id]
        if if_name not in self.loc_port_data:
            # no LLDP data for this interface
            return None
        return self.if_alias_map[if_name]

    def port_table_lookup(self, sub_id, table_name):
        if len(sub_id) == 0:
            return None
        sub_id = sub_id[0]
        if sub_id not in self.oid_name_map:
            return None
        if_name = self.oid_name_map[sub_id]
        if if_name not in self.loc_port_data:
            # no data for this interface
            return None
        counters = self.loc_port_data[if_name]
        _table_name = getattr(table_name, 'name', table_name)

        return counters.get(_table_name, '')

    def port_id_subtype(self, sub_id):
        """
        return port_id_subtype 7(local)
        for every port
        """
        if len(sub_id) == 0:
            return None
        return 7


class LLDPLocManAddrUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()

        self.db_conn = mibs.init_db()
        self.loc_chassis_data = {}
        self.man_addr_list = []
        self.mgmt_ip_str = None

    def reinit_data(self):
        """
        Subclass update data routine.
        """
        self.man_addr_list = []
        self.mgmt_ip_str = None

        # establish connection to application database.
        self.db_conn.connect(mibs.APPL_DB)
        mgmt_ip_bytes = self.db_conn.get(mibs.APPL_DB, mibs.LOC_CHASSIS_TABLE, 'lldp_loc_man_addr')

        if not mgmt_ip_bytes:
            logger.warning("Missing lldp_loc_man_addr from APPL DB")
            return

        self.mgmt_ip_str = mgmt_ip_bytes
        logger.debug("Got mgmt ip from db : {}".format(self.mgmt_ip_str))
        try:
            addr_subtype_sub_oid = 4
            mgmt_ip_sub_oid = None
            for mgmt_ip in self.mgmt_ip_str.split(','):
                if '.' in mgmt_ip:
                    mgmt_ip_tuple = ip2byte_tuple(mgmt_ip)
                    mgmt_ip_sub_oid = (addr_subtype_sub_oid, *mgmt_ip_tuple)
                    break
            else:
                logger.error("Could not find IPv4 address in lldp_loc_man_addr")
                return
        except ValueError:
            logger.error("Invalid local mgmt IP {}".format(self.mgmt_ip_str))
            return

        sub_oid = (ManAddrConst.man_addr_subtype_ipv4,
                   *mgmt_ip_sub_oid)
        self.man_addr_list.append(sub_oid)

    def update_data(self):
        """
        Avoid NotImplementedError
        The data is mostly static, reinit it once a minute is enough.
        """
        pass

    def get_next(self, sub_id):
        right = bisect_right(self.man_addr_list, sub_id)
        if right >= len(self.man_addr_list):
            return None
        return self.man_addr_list[right]

    def lookup(self, sub_id, callable):
        if sub_id not in self.man_addr_list:
            return None
        return callable(sub_id)

    @staticmethod
    def man_addr_subtype(sub_id): return ManAddrConst.man_addr_subtype_ipv4

    def man_addr(self, sub_id):
        """
        :param sub_id:
        :return: MGMT IP in HEX
        """
        if self.mgmt_ip_str:
            hex_ip = ''
            for mgmt_ip in self.mgmt_ip_str.split(','):
                if '.' in mgmt_ip:
                    hex_ip = " ".join([format(int(i), '02X') for i in mgmt_ip.split('.')])
                    break
            return hex_ip

    @staticmethod
    def man_addr_len(sub_id): return ManAddrConst.man_addr_len

    @staticmethod
    def man_addr_if_subtype(sub_id): return ManAddrConst.man_addr_if_subtype

    @staticmethod
    def man_addr_if_id(sub_id): return ManAddrConst.man_addr_if_id

    @staticmethod
    def man_addr_OID(sub_id): return ManAddrConst.man_addr_oid


class LLDPRemTableUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()

        self.db_conn = Namespace.init_namespace_dbs()
        self.if_name_map = {}
        self.if_alias_map = {}
        self.if_id_map = {}
        self.oid_name_map = {}

        self.mgmt_oid_name_map = {}

        self.if_range = []

        # cache of interface counters
        # { sai_id -> { 'counter': 'value' } }
        self.lldp_counters = {}

    def reinit_data(self):
        """
        Subclass update interface information
        """
        self.if_name_map, \
        self.if_alias_map, \
        self.if_id_map, \
        self.oid_name_map = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_interface_tables, self.db_conn)

        self.mgmt_oid_name_map, _ = mibs.init_mgmt_interface_tables(self.db_conn[0])

        self.oid_name_map.update(self.mgmt_oid_name_map)

    def get_next(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query.
        :return: the next sub id.
        """
        right = bisect_right(self.if_range, sub_id)
        if right == len(self.if_range):
            return None
        return self.if_range[right]

    def update_data(self):
        """
        Subclass update data routine. Updates available LLDP counters.
        """
        # establish connection to application database.

        self.if_range = []
        self.lldp_counters = {}
        for if_oid, if_name in self.oid_name_map.items():
            lldp_kvs = Namespace.dbs_get_all(self.db_conn, mibs.APPL_DB, mibs.lldp_entry_table(if_name))
            if not lldp_kvs:
                continue
            try:
                # OID index for this MIB consists of remote time mark, if_oid, remote_index.
                # For multi-asic platform, it can happen that same interface index result 
                # is seen in SNMP walk, with a different remote time mark.
                # To avoid repeating the data of same interface index with different remote 
                # time mark, remote time mark is made as 0 in the OID indexing.
                time_mark = 0
                remote_index = int(lldp_kvs['lldp_rem_index'])
                self.if_range.append((time_mark,
                                      if_oid,
                                      remote_index))
                lldp_kvs['lldp_rem_sys_cap_supported'] = parse_sys_capability(lldp_kvs['lldp_rem_sys_cap_supported'])
                lldp_kvs['lldp_rem_sys_cap_enabled'] = parse_sys_capability(lldp_kvs['lldp_rem_sys_cap_enabled'])
                self.lldp_counters.update({if_name: lldp_kvs})
            except (KeyError, AttributeError) as e:
                logger.warning("Exception when updating lldpRemTable: {}".format(e))
                continue

        self.if_range.sort()

    def local_port_num(self, sub_id):
        if len(sub_id) == 0:
            return None
        sub_id = sub_id[1]
        if sub_id not in self.oid_name_map:
            return None
        return int(sub_id)

    def lldp_table_lookup(self, sub_id, table_name):
        if len(sub_id) == 0:
            return None
        sub_id = sub_id[1]
        if sub_id not in self.oid_name_map:
            return None
        if_name = self.oid_name_map[sub_id]
        if if_name not in self.lldp_counters:
            # no LLDP data for this interface
            return None
        counters = self.lldp_counters[if_name]
        _table_name = getattr(table_name, 'name', table_name)
        try:
            return counters[_table_name]
        except KeyError as e:
            logger.warning(" 0 - b'LLDP_ENTRY_TABLE' missing attribute '{}'.".format(e))
            return None

    def lldp_table_lookup_integer(self, sub_id, table_name):
        """
        :param sub_id: Given sub_id
        :param table_name: name of the table to query.
        :return: int(the subtype)
        """
        subtype_str = self.lldp_table_lookup(sub_id, table_name)
        return int(subtype_str) if subtype_str is not None else None


class LLDPRemManAddrUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()

        self.db_conn = Namespace.init_namespace_dbs()
        # establish connection to application database.
        Namespace.connect_all_dbs(self.db_conn, mibs.APPL_DB)
        self.if_range = []
        self.oid_name_map = {}
        self.mgmt_oid_name_map = {}
        self.pubsub = [None] * len(self.db_conn)

    def update_rem_if_mgmt(self, if_oid, if_name):
        lldp_kvs = Namespace.dbs_get_all(self.db_conn, mibs.APPL_DB, mibs.lldp_entry_table(if_name))
        if not lldp_kvs or 'lldp_rem_man_addr' not in lldp_kvs:
            # this interfaces doesn't have remote lldp data, or the peer doesn't advertise his mgmt address
            return
        try:
            mgmt_ip_str = lldp_kvs['lldp_rem_man_addr']
            mgmt_ip_str = mgmt_ip_str.strip()
            if len(mgmt_ip_str) == 0:
                # the peer advertise an emtpy mgmt address
                return
            mgmt_ip_set=set()
            for mgmt_ip in mgmt_ip_str.split(','):
                time_mark = int(lldp_kvs['lldp_rem_time_mark'])
                remote_index = int(lldp_kvs['lldp_rem_index'])
                subtype = self.get_subtype(mgmt_ip)
                if not subtype:
                    logger.warning("Invalid management IP {}".format(mgmt_ip))
                    continue
                mgmt_ip_tuple = ip2byte_tuple(mgmt_ip)
                if mgmt_ip_tuple in mgmt_ip_set:
                    continue
                elif subtype == ManAddrConst.man_addr_subtype_ipv4:
                    addr_subtype_sub_oid = 4
                else:
                    addr_subtype_sub_oid = 16
                mgmt_ip_set.add(mgmt_ip_tuple)
                mgmt_ip_sub_oid = (addr_subtype_sub_oid, *mgmt_ip_tuple)
                self.if_range.append((time_mark,
                                      if_oid,
                                      remote_index,
                                      subtype,
                                      *mgmt_ip_sub_oid))
        except (KeyError, AttributeError) as e:
            logger.warning("Error updating remote mgmt addr: {}".format(e))
            return
        self.if_range.sort()

    def _update_per_namespace_data(self, pubsub):
        """
        Listen to updates in APP DB, update local cache
        """
        while True:
            data, interface, if_index = poll_lldp_entry_updates(pubsub)

            if not data:
                break

            if "set" in data:
                self.update_rem_if_mgmt(if_index, interface)
            elif "del" in data:
                # some remote data about that neighbor is gone, del it and try to query again
                self.if_range = [sub_oid for sub_oid in self.if_range if sub_oid[0] != if_index]
                self.update_rem_if_mgmt(if_index, interface)

    def update_data(self):
        for i in range(len(self.db_conn)):
            if not self.pubsub[i]:
                pattern = mibs.lldp_entry_table('*')
                self.pubsub[i] = mibs.get_redis_pubsub(self.db_conn[i], self.db_conn[i].APPL_DB, pattern)
            self._update_per_namespace_data(self.pubsub[i])

    def reinit_data(self):
        """
        Subclass reinit data routine.
        """
        _, _, _, self.oid_name_map = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_interface_tables, self.db_conn)

        self.mgmt_oid_name_map, _ = mibs.init_mgmt_interface_tables(self.db_conn[0])

        self.oid_name_map.update(self.mgmt_oid_name_map)

        # establish connection to application database.
        Namespace.connect_all_dbs(self.db_conn, mibs.APPL_DB)

        self.if_range = []
        for if_oid, if_name in self.oid_name_map.items():
            self.update_rem_if_mgmt(if_oid, if_name)

    def get_next(self, sub_id):
        right = bisect_right(self.if_range, sub_id)
        if right == len(self.if_range):
            return None
        return self.if_range[right]

    def lookup(self, sub_id, callable):
        if sub_id not in self.if_range:
            return None
        return callable(sub_id)

    def get_subtype(self, ip_str):
        try:
            ipaddress.IPv4Address(ip_str)
            return ManAddrConst.man_addr_subtype_ipv4
        except ipaddress.AddressValueError:
            # not a valid IPv4
            pass
        try:
            ipaddress.IPv6Address(ip_str)
            return ManAddrConst.man_addr_subtype_ipv6
        except ipaddress.AddressValueError:
            # not a valid IPv6
            logger.warning("Invalid mgmt IP {}".format(ip_str))
        return None

    @staticmethod
    def man_addr_if_subtype(sub_id): return ManAddrConst.man_addr_if_subtype

    @staticmethod
    def man_addr_if_id(sub_id): return ManAddrConst.man_addr_if_id

    @staticmethod
    def man_addr_OID(sub_id): return ManAddrConst.man_addr_oid


class LLDPLocalSystemData(metaclass=MIBMeta, prefix='.1.0.8802.1.1.2.1.3'):
    """
    lldpLocalSystemData  OBJECT IDENTIFIER
    ::= { lldpObjects 3 }
    """
    chassis_updater = LLDPLocalSystemDataUpdater()

    lldpLocChassisIdSubtype = MIBEntry('1', ValueType.INTEGER, chassis_updater.table_lookup_integer,
                                       LLDPLocalChassis(1))

    lldpLocChassisId = MIBEntry('2', ValueType.OCTET_STRING, chassis_updater.table_lookup, LLDPLocalChassis(2))

    lldpLocSysName = MIBEntry('3', ValueType.OCTET_STRING, chassis_updater.table_lookup, LLDPLocalChassis(3))

    lldpLocSysDesc = MIBEntry('4', ValueType.OCTET_STRING, chassis_updater.table_lookup, LLDPLocalChassis(4))

    lldpLocSysCapSupported = MIBEntry('5', ValueType.OCTET_STRING, chassis_updater.table_lookup, LLDPLocalChassis(5))

    lldpLocSysCapEnabled = MIBEntry('6', ValueType.OCTET_STRING, chassis_updater.table_lookup, LLDPLocalChassis(6))

    class LLDPLocPortTable(metaclass=MIBMeta, prefix='.1.0.8802.1.1.2.1.3.7'):
        """
        lldpLocPortTable OBJECT-TYPE
            SYNTAX      SEQUENCE OF LldpLocPortEntry
            MAX-ACCESS  not-accessible
            STATUS      current
            DESCRIPTION
              "This table contains one or more rows per port information
               associated with the local system known to this agent."
            ::= { lldpLocalSystemData 7 }

            LldpLocPortEntry ::= SEQUENCE {
                lldpLocPortNum                LldpPortNumber,
                lldpLocPortIdSubtype          LldpPortIdSubtype,
                lldpLocPortId                 LldpPortId,
                lldpLocPortDesc               SnmpAdminString
            }

        """
        port_updater = LocPortUpdater()

        # lldpLocPortEntry = '1'

        # We're using locally assigned name, so according to textual convention, the subtype is 7
        lldpLocPortIdSubtype = SubtreeMIBEntry('1.2', port_updater, ValueType.INTEGER, port_updater.port_id_subtype)

        lldpLocPortId = SubtreeMIBEntry('1.3', port_updater, ValueType.OCTET_STRING, port_updater.local_port_id)

        lldpLocPortDesc = SubtreeMIBEntry('1.4', port_updater, ValueType.OCTET_STRING, port_updater.port_table_lookup,
                                          "description")

    class LLDPLocManAddrTable(metaclass=MIBMeta, prefix='.1.0.8802.1.1.2.1.3.8'):
        """
        lldpLocManAddrTable OBJECT-TYPE
        SYNTAX      SEQUENCE OF LldpLocManAddrEntry
        MAX-ACCESS  not-accessible
        STATUS      current
        DESCRIPTION
                "This table contains management address information on the
                local system known to this agent."
        ::= { lldpLocalSystemData 8 }
        """
        updater = LLDPLocManAddrUpdater()

        lldpLocManAddrLen = SubtreeMIBEntry('1.3', updater, ValueType.INTEGER,
                                            updater.lookup, updater.man_addr_len)

        lldpLocManAddrIfSubtype = SubtreeMIBEntry('1.4', updater, ValueType.INTEGER,
                                                  updater.lookup, updater.man_addr_if_subtype)

        lldpLocManAddrIfId = SubtreeMIBEntry('1.5', updater, ValueType.INTEGER,
                                             updater.lookup, updater.man_addr_if_id)

        lldpLocManAddrOID = SubtreeMIBEntry('1.6', updater, ValueType.OBJECT_IDENTIFIER,
                                            updater.lookup, updater.man_addr_OID)


class LLDPRemTable(metaclass=MIBMeta, prefix='.1.0.8802.1.1.2.1.4.1'):
    """
    lldpRemTable OBJECT-TYPE
    SYNTAX      SEQUENCE OF LldpRemEntry
    MAX-ACCESS  not-accessible
    STATUS      current
    DESCRIPTION
            "This table contains one or more rows per physical network
            connection known to this agent.  The agent may wish to ensure
            that only one lldpRemEntry is present for each local port,
            or it may choose to maintain multiple lldpRemEntries for
            the same local port.

            The following procedure may be used to retrieve remote
            systems information updates from an LLDP agent:

               1. NMS polls all tables associated with remote systems
                  and keeps a local copy of the information retrieved.
                  NMS polls periodically the values of the following
                  objects:
                     a. lldpStatsRemTablesInserts
                     b. lldpStatsRemTablesDeletes
                     c. lldpStatsRemTablesDrops
                     d. lldpStatsRemTablesAgeouts
                     e. lldpStatsRxPortAgeoutsTotal for all ports.

               2. LLDP agent updates remote systems MIB objects, and
                  sends out notifications to a list of notification
                  destinations.

               3. NMS receives the notifications and compares the new
                  values of objects listed in step 1.

                  Periodically, NMS should poll the object
                  lldpStatsRemTablesLastChangeTime to find out if anything
                  has changed since the last poll.  if something has
                  changed, NMS will poll the objects listed in step 1 to
                  figure out what kind of changes occurred in the tables.

                  if value of lldpStatsRemTablesInserts has changed,
                  then NMS will walk all tables by employing TimeFilter
                  with the last-polled time value.  This request will
                  return new objects or objects whose values are updated
                  since the last poll.

                  if value of lldpStatsRemTablesAgeouts has changed,
                  then NMS will walk the lldpStatsRxPortAgeoutsTotal and
                  compare the new values with previously recorded ones.
                  For ports whose lldpStatsRxPortAgeoutsTotal value is
                  greater than the recorded value, NMS will have to
                  retrieve objects associated with those ports from
                  table(s) without employing a TimeFilter (which is
                  performed by specifying 0 for the TimeFilter.)

                  lldpStatsRemTablesDeletes and lldpStatsRemTablesDrops
                  objects are provided for informational purposes."
    ::= { lldpRemoteSystemsData 1 }

    lldpRemEntry OBJECT-TYPE
    SYNTAX      LldpRemEntry
    MAX-ACCESS  not-accessible
    STATUS      current
    DESCRIPTION
            "Information about a particular physical network connection.
            Entries may be created and deleted in this table by the agent,
            if a physical topology discovery process is active."
    INDEX   {
           lldpRemTimeMark,
           lldpRemLocalPortNum,
           lldpRemIndex
    }
    ::= { lldpRemTable 1 }

    LldpRemEntry ::= SEQUENCE {
          lldpRemTimeMark           TimeFilter,
          lldpRemLocalPortNum       LldpPortNumber,
          lldpRemIndex              Integer32,
          lldpRemChassisIdSubtype   LldpChassisIdSubtype,
          lldpRemChassisId          LldpChassisId,
          lldpRemPortIdSubtype      LldpPortIdSubtype,
          lldpRemPortId             LldpPortId,
          lldpRemPortDesc           SnmpAdminString,
          lldpRemSysName            SnmpAdminString,
          lldpRemSysDesc            SnmpAdminString,
          lldpRemSysCapSupported    LldpSystemCapabilitiesMap,
          lldpRemSysCapEnabled      LldpSystemCapabilitiesMap
    }
    """
    lldp_updater = LLDPRemTableUpdater()

    lldpRemChassisIdSubtype = \
        SubtreeMIBEntry('1.4', lldp_updater, ValueType.INTEGER, lldp_updater.lldp_table_lookup_integer,
                        LLDPRemoteTables(4))

    lldpRemChassisId = \
        SubtreeMIBEntry('1.5', lldp_updater, ValueType.OCTET_STRING, lldp_updater.lldp_table_lookup,
                        LLDPRemoteTables(5))

    lldpRemPortIdSubtype = \
        SubtreeMIBEntry('1.6', lldp_updater, ValueType.INTEGER, lldp_updater.lldp_table_lookup_integer,
                        LLDPRemoteTables(6))

    lldpRemPortId = \
        SubtreeMIBEntry('1.7', lldp_updater, ValueType.OCTET_STRING, lldp_updater.lldp_table_lookup,
                        LLDPRemoteTables(7))

    lldpRemPortDesc = \
        SubtreeMIBEntry('1.8', lldp_updater, ValueType.OCTET_STRING, lldp_updater.lldp_table_lookup,
                        LLDPRemoteTables(8))

    lldpRemSysName = \
        SubtreeMIBEntry('1.9', lldp_updater, ValueType.OCTET_STRING, lldp_updater.lldp_table_lookup,
                        LLDPRemoteTables(9))

    lldpRemSysDesc = \
        SubtreeMIBEntry('1.10', lldp_updater, ValueType.OCTET_STRING, lldp_updater.lldp_table_lookup,
                        LLDPRemoteTables(10))

    lldpRemSysCapSupported = \
        SubtreeMIBEntry('1.11', lldp_updater, ValueType.OCTET_STRING, lldp_updater.lldp_table_lookup,
                        LLDPRemoteTables(11))

    lldpRemSysCapEnabled = \
        SubtreeMIBEntry('1.12', lldp_updater, ValueType.OCTET_STRING, lldp_updater.lldp_table_lookup,
                        LLDPRemoteTables(12))


class LLDPRemManAddrTable(metaclass=MIBMeta, prefix='.1.0.8802.1.1.2.1.4.2'):
    """
    lldpRemManAddrTable OBJECT-TYPE
    SYNTAX      SEQUENCE OF LldpRemManAddrEntry
    MAX-ACCESS  not-accessible
    STATUS      current
    DESCRIPTION
            "This table contains one or more rows per management address
            information on the remote system learned on a particular port
            contained in the local chassis known to this agent."
    ::= { lldpRemoteSystemsData 2 }
    """
    updater = LLDPRemManAddrUpdater()

    lldpRemManAddrIfSubtype = SubtreeMIBEntry('1.3', updater, ValueType.INTEGER,
                                              updater.lookup, updater.man_addr_if_subtype)

    lldpRemManAddrIfId = SubtreeMIBEntry('1.4', updater, ValueType.INTEGER,
                                         updater.lookup, updater.man_addr_if_id)

    lldpRemManAddrOID = SubtreeMIBEntry('1.5', updater, ValueType.OBJECT_IDENTIFIER,
                                        updater.lookup, updater.man_addr_OID)
