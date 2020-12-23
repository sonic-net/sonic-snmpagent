import json
import time

from sonic_ax_impl import mibs
from swsssdk import port_util
from sonic_ax_impl.mibs import Namespace
from ax_interface import MIBMeta, ValueType, MIBUpdater, SubtreeMIBEntry, MIBEntry
from ax_interface.util import mac_decimals
from bisect import bisect_right
from bitstring import BitArray
from sonic_ax_impl.mibs import Namespace

class TpFdbStatusConst:
    other = 1
    invalid = 2
    learned = 3
    self = 4
    mgmt = 5

class CacheRefreshInterval:
    fdbUpdater = 180.0
    dot1qVlanCurr = 60.0

class FdbUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.db_conn = Namespace.init_namespace_dbs()

        self.if_name_map = {}
        self.if_alias_map = {}
        self.if_id_map = {}
        self.oid_name_map = {}
        self.if_id_map_all = {}
        self.vlanmac_ifindex_map = {}
        self.vlanmac_ifindex_list = []
        self.vlan_keys = []
        self.if_bpid_map = {}
        self.bvid_vlan_map = {}
        self.tp_fdb_status_map = {}
        self.vlan_dynamic_count_map = {}
        self.vlan_id_list = []
        self.cache_time = 0.0

    def fdb_vlanmac(self, fdb):
        if 'vlan' in fdb:
            vlan_id = fdb["vlan"]
        elif 'bvid' in fdb:
            if fdb["bvid"] in self.bvid_vlan_map:
                vlan_id = self.bvid_vlan_map[fdb["bvid"]]
            else:
                vlan_id = Namespace.dbs_get_vlan_id_from_bvid(self.db_conn, fdb["bvid"])
                self.bvid_vlan_map[fdb["bvid"]] = vlan_id
        return (int(vlan_id),) + mac_decimals(fdb["mac"]), int(vlan_id)

    def get_tp_fdb_status(self, ent, fdb):
        if 'SAI_FDB_ENTRY_ATTR_TYPE' not  in ent:
            return  TpFdbStatusConst.invalid
        ent_type = ent['SAI_FDB_ENTRY_ATTR_TYPE']
        if ent_type == 'SAI_FDB_ENTRY_TYPE_DYNAMIC':
            status = TpFdbStatusConst.learned
        else:
            status = TpFdbStatusConst.mgmt
        return status

    def reinit_data(self):
        """
        Subclass update interface information
        """
        self.if_name_map, \
        self.if_alias_map, \
        self.if_id_map, \
        self.oid_name_map, \
        self.if_id_map_all = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_interface_tables, self.db_conn)

        self.if_bpid_map = Namespace.dbs_get_bridge_port_map(self.db_conn, mibs.ASIC_DB)
        self.bvid_vlan_map.clear()

    def update_data(self):
        """
        Update redis (caches config)
        Pulls the table references for each interface.
        """
        curr_time = time.time()
        if curr_time - self.cache_time < CacheRefreshInterval.fdbUpdater:
            return
        Namespace.connect_all_dbs(self.db_conn, mibs.ASIC_DB)
        self.vlanmac_ifindex_map = {}
        self.vlanmac_ifindex_list = []
        self.vlan_dynamic_count_map = {}
        self.vlan_id_list = []

        # connect to config and get VLAN keys
        Namespace.connect_all_dbs(self.db_conn, mibs.CONFIG_DB)
        self.vlan_keys = []
        self.vlan_keys = Namespace.dbs_keys(self.db_conn, mibs.CONFIG_DB, "VLAN|*")
        fdb_strings = Namespace.dbs_keys(self.db_conn, mibs.ASIC_DB, "ASIC_STATE:SAI_OBJECT_TYPE_FDB_ENTRY:*")
        if not fdb_strings:
            return

        for s in fdb_strings:
            fdb_str = s
            try:
                fdb = json.loads(fdb_str.split(":", maxsplit=2)[-1])
            except ValueError as e:  # includes simplejson.decoder.JSONDecodeError
                mibs.logger.error("SyncD 'ASIC_DB' includes invalid FDB_ENTRY '{}': {}.".format(fdb_str, e))
                break

            try:
                ent = Namespace.dbs_get_all(self.db_conn, mibs.ASIC_DB, s, blocking=True)
            except Exception as ex:
                mibs.logger.warning("Exception connecting to ASIC_DB '{}'".format(ex))
                continue

            # Example output: oid:0x3a000000000608
            bridge_port_id = ent["SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID"][6:]

            if bridge_port_id not in self.if_bpid_map:
                continue

            port_id = self.if_bpid_map[bridge_port_id]

            vlanmac, vlanid = self.fdb_vlanmac(fdb)
            self.tp_fdb_status_map[vlanmac] = self.get_tp_fdb_status(ent, fdb)
            #get interface name given the sai port oid
            #use if_id_map_all to get interfacename as it includes portchannel interfaces also

            try:
                self.vlanmac_ifindex_map[vlanmac] = mibs.get_index_from_str(self.if_id_map[port_id])
            except Exception as ex:
                mibs.logger.warning("Exception getting vlanmac to ifindex '{}'".format(ex))
                continue

            self.vlanmac_ifindex_list.append(vlanmac)

            #vlanid = self.fdb_vlan(fdb)
            try:
                ent_type = ent["SAI_FDB_ENTRY_ATTR_TYPE"]
                if ent_type == 'SAI_FDB_ENTRY_TYPE_DYNAMIC':
                    if vlanid in self.vlan_dynamic_count_map:
                        self.vlan_dynamic_count_map[vlanid] = self.vlan_dynamic_count_map[vlanid] + 1
                    else:
                        self.vlan_dynamic_count_map[vlanid] = 1
                self.vlan_id_list.append(vlanid)
            except Exception as ex:
                mibs.logger.warning("Exception getting vlanid '{}'".format(ex))
                continue

        self.cache_time = time.time()
        self.vlan_id_list.sort()
        self.vlan_id_list = [(i,) for i in self.vlan_id_list]
        mibs.logger.debug('vlan_dynamic_count_map={}'.format(self.vlan_dynamic_count_map))

        self.vlanmac_ifindex_list.sort()

    def fdb_ifindex(self, sub_id):
        return self.vlanmac_ifindex_map.get(sub_id, None)

    def fdb_status(self, sub_id):
        return self.tp_fdb_status_map.get(sub_id, None)

    def get_vlan_version(self):
        return 2

    def get_MaxVlanId(self):
        return 4094

    def get_MaxSupportedVlans(self):
        return 4094

    def get_dot1qNumVlans(self):
        if self.vlan_keys:
            return len(self.vlan_keys)
        else:
            return 0

    def get_next(self, sub_id):
        right = bisect_right(self.vlanmac_ifindex_list, sub_id)
        if right >= len(self.vlanmac_ifindex_list):
            return None

        return self.vlanmac_ifindex_list[right]

class QBridgeMIBObjects(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.17.7.1'):
    """
    'Forwarding Database' https://tools.ietf.org/html/rfc4363
    """

    fdb_updater = FdbUpdater()

    dot1qVlanVersionNumber = \
        MIBEntry('1.1.0', ValueType.INTEGER, fdb_updater.get_vlan_version)

    dot1qMaxVlanId = \
        MIBEntry('1.2.0', ValueType.INTEGER, fdb_updater.get_MaxVlanId)

    dot1qMaxSupportedVlans = \
        MIBEntry('1.3.0', ValueType.GAUGE_32, fdb_updater.get_MaxSupportedVlans)

    dot1qNumVlans = \
        MIBEntry('1.4.0', ValueType.GAUGE_32, fdb_updater.get_dot1qNumVlans)

    dot1qTpFdbPort = \
        SubtreeMIBEntry('2.2.1.2', fdb_updater, ValueType.INTEGER, fdb_updater.fdb_ifindex)

    dot1qTpFdbStatus = \
        SubtreeMIBEntry('2.2.1.3', fdb_updater, ValueType.INTEGER, fdb_updater.fdb_status)

class FdbTableUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.db_conn = mibs.init_db()

        self.vlan_dynamic_count_map = {}
        self.vlan_id_list = []

    def update_data(self):
        """
        Update redis (caches config)
        Pulls the table references for each interface.
        """
        fdb_data = QBridgeMIBObjects.fdb_updater
        self.vlan_dynamic_count_map = fdb_data.vlan_dynamic_count_map
        self.vlan_id_list = fdb_data.vlan_id_list

    def fdb_dynamic_count(self, sub_id):
        if sub_id:
            if sub_id[0] in self.vlan_dynamic_count_map:
                return self.vlan_dynamic_count_map.get(sub_id[0], None)
            else:
                return 0

    def get_next(self, sub_id):
        right = bisect_right(self.vlan_id_list, sub_id)
        if right >= len(self.vlan_id_list):
            return None

        return self.vlan_id_list[right]

class Dot1qFdbMIBObjects(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.17.7.1'):
    """
    'Forwarding Database' https://tools.ietf.org/html/rfc4363
    """

    fdb_table_updater = FdbTableUpdater()

    dot1qFdbDynamicCount = \
        SubtreeMIBEntry('2.1.1.2', fdb_table_updater, ValueType.COUNTER_32, fdb_table_updater.fdb_dynamic_count)

class Dot1qVlanStatusConst:
    other = 1
    permanent = 2
    dynamicGvrp = 3

class Dot1qVlanCurrentUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.db_conn = mibs.init_db()
        self.vlan_egress_ports_map = {}
        self.vlan_untag_ports_map = {}
        self.vlan_static_egress_ports_map = {}
        self.vlan_static_untag_ports_map = {}
        self.vlan_time_index_list = []
        self.vlan_name_map = {}
        self.vlan_max_port = {}
        self.vlan_index_list = []
        self.dot1q_pvid = {}
        self.dot1q_port_vlan_list = []
        self.cache_time = 0.0

    def update_data(self):
        """
        Update redis (caches config)
        Pulls the table references for each interface.
        """
        curr_time = time.time()
        if curr_time - self.cache_time < CacheRefreshInterval.dot1qVlanCurr:
            return
        self.vlan_egress_ports_map = {}
        self.vlan_untag_ports_map = {}
        self.vlan_static_egress_ports_map = {}
        self.vlan_static_untag_ports_map = {}
        self.vlan_time_index_list = []
        self.vlan_name_map = {}
        self.vlan_max_port = {}
        self.vlan_index_list = []
        self.dot1q_pvid = {}
        self.dot1q_port_vlan_list = []

        self.db_conn.connect(mibs.CONFIG_DB)
        vlan_entries = self.db_conn.keys(mibs.CONFIG_DB, "VLAN|*")
        if not vlan_entries:
            return
        for vlan_entry in vlan_entries:
            vlan = vlan_entry.split('|')[1]
            vlan_id = int(vlan.strip('Vlan'))
            vlan_index = (0, vlan_id)
            self.vlan_time_index_list.append(vlan_index)
            self.vlan_index_list.append(vlan_id)
            self.vlan_name_map[vlan_id] = vlan
        self.vlan_index_list.sort()
        self.vlan_index_list = [(i,) for i in self.vlan_index_list]

        vlanmem_entries = self.db_conn.keys(mibs.CONFIG_DB, "VLAN_MEMBER|*")
        if not vlanmem_entries:
            return
        for vmem_entry in vlanmem_entries:
            vlan = vmem_entry.split('|')[1]
            vlan_id = int(vlan.strip('Vlan'))
            vlan_index = (0, vlan_id)
            port_name = vmem_entry.split('|')[2]
            if 'Ethernet' in port_name:
                port = port_name[len('Ethernet'):]
            else:
                port = port_name[len('PortChannel'):]
            port = int(port)
            tag_type = self.db_conn.get(mibs.CONFIG_DB, vmem_entry, 'tagging_mode')
            if tag_type:
                if vlan_index in self.vlan_egress_ports_map:
                    portBitArray = self.vlan_egress_ports_map[vlan_index]
                    portBitArray[port] = True
                    if port >  self.vlan_max_port[vlan_id]:
                        self.vlan_max_port[vlan_id] = port
                    self.vlan_egress_ports_map[vlan_index] = portBitArray
                    self.vlan_static_egress_ports_map[vlan_id] = portBitArray
                else:
                    portBitArray = BitArray(4096)
                    portBitArray[port] = True
                    self.vlan_max_port[vlan_id] = port
                    self.vlan_egress_ports_map[vlan_index] = portBitArray
                    self.vlan_static_egress_ports_map[vlan_id] = portBitArray
            if tag_type == 'untagged':
                if vlan_index in self.vlan_untag_ports_map:
                    portBitArray = self.vlan_egress_ports_map[vlan_index]
                    portBitArray[port] = True
                    if port >  self.vlan_max_port[vlan_id]:
                        self.vlan_max_port[vlan_id] = port
                    self.vlan_untag_ports_map[vlan_index] = portBitArray
                    self.vlan_static_untag_ports_map[vlan_id] = portBitArray
                else:
                    portBitArray = BitArray(4096)
                    portBitArray[port] = True
                    self.vlan_max_port[vlan_id] = port
                    self.vlan_untag_ports_map[vlan_index] = portBitArray
                    self.vlan_static_untag_ports_map[vlan_id] = portBitArray

            if_index = port_util.get_index_from_str(port_name)
            if tag_type == 'untagged':
                self.dot1q_pvid[if_index-1] = vlan_id
            else:
                self.dot1q_pvid[if_index-1] = 0
        self.cache_time = time.time()
        self.dot1q_port_vlan_list = sorted(self.dot1q_pvid.keys())
        self.dot1q_port_vlan_list = [(i,) for i in self.dot1q_port_vlan_list]
        self.vlan_time_index_list.sort()
        mibs.logger.debug('vlan_egress_ports_map={}'.format(self.vlan_egress_ports_map))
        mibs.logger.debug('vlan_untag_ports_map={}'.format(self.vlan_untag_ports_map))
        mibs.logger.debug('vlan_time_index_list={}'.format(self.vlan_time_index_list))
        mibs.logger.debug('vlan_index_list={}'.format(self.vlan_index_list))
        mibs.logger.debug('vlan_name_map={}'.format(self.vlan_name_map))


    def dot1q_vlan_current_egress_ports(self, sub_id):
        if sub_id:
            if sub_id in self.vlan_egress_ports_map:
                data = self.vlan_egress_ports_map.get(sub_id, None)
                if data:
                    byts = data.tobytes()
                    bs = byts[0:self.vlan_max_port[sub_id[1]]//8 +2]
                    bs_hex = " ".join([format(i, '02x') for i in bs])
                    return bs_hex
            else:
                return '0'

    def dot1q_vlan_current_untag_ports(self, sub_id):
        if sub_id:
            if sub_id in self.vlan_untag_ports_map:
                data = self.vlan_untag_ports_map.get(sub_id, None)
                if data:
                    byts = data.tobytes()
                    bs = byts[0:self.vlan_max_port[sub_id[1]]//8 +2]
                    bs_hex = " ".join([format(i, '02x') for i in bs])
                    return bs_hex
            else:
                return '0'

    def dot1q_vlan_status(self, sub_id):
        if sub_id:
            return Dot1qVlanStatusConst.permanent

    def get_vlan_deletes(self):
        return 0

    def get_next(self, sub_id):
        right = bisect_right(self.vlan_time_index_list, sub_id)
        if right == len(self.vlan_time_index_list):
            return None

        return self.vlan_time_index_list[right]

class Dot1qVlanCurrentMIBObjects(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.17.7.1'):
    """
    'Forwarding Database' https://tools.ietf.org/html/rfc4363
    """

    fdb_vlan_updater = Dot1qVlanCurrentUpdater()

    dot1qVlanNumDeletes = \
        MIBEntry('4.1.0', ValueType.COUNTER_32, fdb_vlan_updater.get_vlan_deletes)

    dot1qVlanCurrentEgressPorts = \
        SubtreeMIBEntry('4.2.1.4', fdb_vlan_updater, ValueType.OCTET_STRING, fdb_vlan_updater.dot1q_vlan_current_egress_ports)
    dot1qVlanCurrentUntaggedPorts = \
        SubtreeMIBEntry('4.2.1.5', fdb_vlan_updater, ValueType.OCTET_STRING, fdb_vlan_updater.dot1q_vlan_current_untag_ports)
    dot1qVlanStatus = \
        SubtreeMIBEntry('4.2.1.6', fdb_vlan_updater, ValueType.INTEGER, fdb_vlan_updater.dot1q_vlan_status)

class Dot1qVlanRowStatusConst:
    active = 1
    notInService = 2

class Dot1qVlanStaticUpdater(Dot1qVlanCurrentUpdater):
    def __init__(self):
        super().__init__()
        self.vlan_static_egress_ports_map = {}
        self.vlan_static_untag_ports_map = {}
        self.vlan_name_map = {}
        self.vlan_max_port = {}
        self.vlan_index_list = []

    def update_data(self):
        """
        Update redis (caches config)
        Pulls the table references for each interface.
        """
        fdb_vlan = Dot1qVlanCurrentMIBObjects.fdb_vlan_updater
        self.vlan_static_egress_ports_map = fdb_vlan.vlan_static_egress_ports_map
        self.vlan_static_untag_ports_map = fdb_vlan.vlan_static_untag_ports_map
        self.vlan_name_map = fdb_vlan.vlan_name_map
        self.vlan_max_port = fdb_vlan.vlan_max_port
        self.vlan_index_list = fdb_vlan.vlan_index_list

    def dot1q_vlan_static_egress_ports(self, sub_id):
        if sub_id:
            if sub_id[0] in self.vlan_static_egress_ports_map:
                data = self.vlan_static_egress_ports_map.get(sub_id[0], None)
                if data:
                    byts = data.tobytes()
                    bs = byts[0:self.vlan_max_port[sub_id[0]]//8 +2]
                    bs_hex = " ".join([format(i, '02x') for i in bs])
                    return bs_hex
            else:
                return '0'

    def dot1q_vlan_static_untag_ports(self, sub_id):
        if sub_id:
            if sub_id[0] in self.vlan_static_untag_ports_map:
                data =  self.vlan_static_untag_ports_map.get(sub_id[0], None)
                if data:
                    byts = data.tobytes()
                    bs = byts[0:self.vlan_max_port[sub_id[0]]//8 +2]
                    bs_hex = " ".join([format(i, '02x') for i in bs])
                    return bs_hex
            else:
                return '0'

    def dot1q_vlan_static_name(self, sub_id):
        if sub_id:
            if sub_id[0] in self.vlan_name_map:
                return self.vlan_name_map.get(sub_id[0], None)


    def dot1q_vlan_static_row_status(self, sub_id):
        if sub_id:
            return Dot1qVlanRowStatusConst.active

    def get_next(self, sub_id):
        right = bisect_right(self.vlan_index_list, sub_id)
        if right == len(self.vlan_index_list):
            return None

        return self.vlan_index_list[right]

class Dot1qVlanStaticMIBObjects(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.17.7.1'):
    """
    'Forwarding Database' https://tools.ietf.org/html/rfc4363
    """

    fdb_vlan_updater = Dot1qVlanStaticUpdater()

    dot1qVlanStaticName = \
        SubtreeMIBEntry('4.3.1.1', fdb_vlan_updater, ValueType.OCTET_STRING, fdb_vlan_updater.dot1q_vlan_static_name)
    dot1qVlanStaticEgressPorts = \
        SubtreeMIBEntry('4.3.1.2', fdb_vlan_updater, ValueType.OCTET_STRING, fdb_vlan_updater.dot1q_vlan_static_egress_ports)
    dot1qVlanStaticUntaggedPorts = \
        SubtreeMIBEntry('4.3.1.4', fdb_vlan_updater, ValueType.OCTET_STRING, fdb_vlan_updater.dot1q_vlan_static_untag_ports)
    dot1qVlanStaticRowStatus = \
        SubtreeMIBEntry('4.3.1.5', fdb_vlan_updater, ValueType.INTEGER, fdb_vlan_updater.dot1q_vlan_static_row_status)


class Dot1qPortVlanUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.db_conn = mibs.init_db()
        self.dot1q_pvid = {}
        self.dot1q_port_vlan_list = []

    def update_data(self):
        """
        Update redis (caches config)
        Pulls the table references for each interface.
        """
        port_updater = Dot1qVlanCurrentMIBObjects.fdb_vlan_updater
        self.dot1q_pvid = port_updater.dot1q_pvid
        self.dot1q_port_vlan_list = port_updater.dot1q_port_vlan_list

    def get_dot1dbase_port(self, sub_id):
        if sub_id:
            if sub_id in self.dot1q_port_vlan_list:
               return sub_id[0]
        return

    def get_dot1q_pvid(self, sub_id):
        if sub_id:
            return self.dot1q_pvid.get(sub_id[0], None)

    def get_next(self, sub_id):
        right = bisect_right(self.dot1q_port_vlan_list, sub_id)
        if right == len(self.dot1q_port_vlan_list):
            return None

        return self.dot1q_port_vlan_list[right]

class Dot1qPortVlanMIBObjects(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.17.7.1'):
    """
    'Forwarding Database' https://tools.ietf.org/html/rfc4363
    """

    fdb_vlan_updater = Dot1qPortVlanUpdater()

    dot1qPvid = \
        SubtreeMIBEntry('4.5.1.1', fdb_vlan_updater, ValueType.INTEGER, fdb_vlan_updater.get_dot1q_pvid)


