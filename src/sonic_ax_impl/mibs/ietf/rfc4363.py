import json

from sonic_ax_impl import mibs
from sonic_ax_impl.mibs import Namespace
from ax_interface import MIBMeta, ValueType, MIBUpdater, SubtreeMIBEntry
from ax_interface.util import mac_decimals
from bisect import bisect_right

class FdbUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.db_conn = Namespace.init_namespace_dbs()

        self.if_name_map = {}
        self.if_alias_map = {}
        self.if_id_map = {}
        self.oid_name_map = {}
        self.sai_lag_map = {}
        self.vlanmac_ifindex_map = {}
        self.vlanmac_ifindex_list = []
        self.if_bpid_map = {}
        self.bvid_vlan_map = {}
        self.broken_fdbs = []

    def fdb_vlanmac(self, fdb):
        if 'vlan' in fdb:
            vlan_id = fdb["vlan"]
        elif 'bvid' in fdb:
            if fdb["bvid"] in self.bvid_vlan_map:
                vlan_id = self.bvid_vlan_map[fdb["bvid"]]
            else:
                vlan_id = Namespace.dbs_get_vlan_id_from_bvid(self.db_conn, fdb["bvid"])
                if isinstance(vlan_id, bytes):
                    vlan_id = vlan_id.decode()
                # only cache vlan_id if valid
                if vlan_id is not None:
                    self.bvid_vlan_map[fdb["bvid"]] = vlan_id
        else:
            return None
        if not isinstance(vlan_id, str):
            return None
        return (int(vlan_id),) + mac_decimals(fdb["mac"])

    def reinit_connection(self):
        Namespace.connect_namespace_dbs(self.db_conn)

    def reinit_data(self):
        """
        Subclass update interface information
        """
        (
            self.if_name_map,
            self.if_alias_map,
            self.if_id_map,
            self.oid_name_map,
        ) = Namespace.get_sync_d_from_all_namespace(
            mibs.init_sync_d_interface_tables, self.db_conn
        )

        self.lag_name_if_name_map, \
        self.if_name_lag_name_map, \
        self.oid_lag_name_map,     \
        _, self.sai_lag_map = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_lag_tables, self.db_conn)

        self.if_bpid_map = Namespace.dbs_get_bridge_port_map(self.db_conn, mibs.ASIC_DB)
        self.bvid_vlan_map.clear()
        self.broken_fdbs.clear()

    def update_data(self):
        """
        Update redis (caches config)
        Pulls the table references for each interface.
        """
        self.vlanmac_ifindex_map = {}
        self.vlanmac_ifindex_list = []

        fdb_strings = Namespace.dbs_keys(self.db_conn, mibs.ASIC_DB, "ASIC_STATE:SAI_OBJECT_TYPE_FDB_ENTRY:*")
        if not fdb_strings:
            return

        for s in fdb_strings:
            fdb_str = s
            try:
                fdb = json.loads(fdb_str.split(":", maxsplit=2)[-1])
            except ValueError as e:  # includes simplejson.decoder.JSONDecodeError
                mibs.logger.error("SyncD 'ASIC_DB' includes invalid FDB_ENTRY '{}': {}.".format(fdb_str, e))
                continue

            ent = Namespace.dbs_get_all(self.db_conn, mibs.ASIC_DB, s, blocking=False)
            if not ent:
                continue

            bridge_port_id_attr = ""
            try:
                bridge_port_id_attr = ent["SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID"]
            except KeyError as e:
                # Only write warning log once
                if fdb_str not in self.broken_fdbs:
                    mibs.logger.warn("SyncD 'ASIC_DB' includes invalid FDB_ENTRY '{}': failed to get bridge_port_id, exception: {}".format(fdb_str, e))
                    self.broken_fdbs.append(fdb_str)
                continue

            # Example output: oid:0x3a000000000608
            bridge_port_id = bridge_port_id_attr[6:]
            if bridge_port_id not in self.if_bpid_map:
                continue
            port_id = self.if_bpid_map[bridge_port_id]
            if port_id in self.if_id_map:
                port_name = self.if_id_map[port_id]
                port_index = mibs.get_index_from_str(port_name)
            elif port_id in self.sai_lag_map:
                port_name = self.sai_lag_map[port_id]
                port_index = mibs.get_index_from_str(port_name)
            else:
                continue

            vlanmac = self.fdb_vlanmac(fdb)
            if not vlanmac:
                mibs.logger.debug("SyncD 'ASIC_DB' includes invalid FDB_ENTRY '{}': failed in fdb_vlanmac().".format(fdb_str))
                continue
            self.vlanmac_ifindex_map[vlanmac] = port_index
            self.vlanmac_ifindex_list.append(vlanmac)
        self.vlanmac_ifindex_list.sort()

    def fdb_ifindex(self, sub_id):
        return self.vlanmac_ifindex_map.get(sub_id, None)

    def get_next(self, sub_id):
        right = bisect_right(self.vlanmac_ifindex_list, sub_id)
        if right >= len(self.vlanmac_ifindex_list):
            return None

        return self.vlanmac_ifindex_list[right]

class Dot1qPortUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.db_conn = Namespace.init_namespace_dbs()

        self.if_name_map = {}
        self.if_alias_map = {}
        self.if_id_map = {}
        self.oid_name_map = {}
        self.sai_lag_map = {}
        self.ifindex_pvid_map = {}
        self.ifindex_pvid_list = []

    def reinit_data(self):
        """
        Subclass update interface information
        """
        (
            self.if_name_map,
            self.if_alias_map,
            self.if_id_map,
            self.oid_name_map,
        ) = Namespace.get_sync_d_from_all_namespace(
            mibs.init_sync_d_interface_tables, self.db_conn
        )

        self.lag_name_if_name_map, \
        self.if_name_lag_name_map, \
        self.oid_lag_name_map,     \
        _, self.sai_lag_map = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_lag_tables, self.db_conn)


    def update_data(self):
        """
        Update redis (caches config)
        Pulls the table references for each interface.
        """
        self.ifindex_pvid_map = {}
        self.ifindex_pvid_list = []

        vlan_member_strings = Namespace.dbs_keys(self.db_conn, mibs.CONFIG_DB, "VLAN_MEMBER|*")
        if not vlan_member_strings:
            return

        for s in vlan_member_strings:
            vlan_member = s

            try:
                _, vlan_id, port_name = s.split("|", maxsplit=2)
                vlan_id = int(vlan_id.split("Vlan")[1])
                port_index = (mibs.get_index_from_str(port_name),)
            except ValueError as e:  # includes simplejson.decoder.JSONDecodeError
                mibs.logger.error("'CONFIG_DB' includes invalid Vlan member: {}.".format(s))
                continue

            ent = Namespace.dbs_get_all(self.db_conn, mibs.CONFIG_DB, s, blocking=True)
            untagged = ent["tagging_mode"] == "untagged"
            if untagged:
                self.ifindex_pvid_map[port_index] = vlan_id
                mibs.logger.info("vid = {}".format(vlan_id))
            else:
                if port_index not in self.ifindex_pvid_map.keys():
                    self.ifindex_pvid_map[port_index] = 0

            self.ifindex_pvid_list.append(port_index)
        self.ifindex_pvid_list.sort()

    def port_vid(self, sub_id):
        return self.ifindex_pvid_map.get(sub_id, None)

    def get_next(self, sub_id):
        right = bisect_right(self.ifindex_pvid_list, sub_id)
        if right >= len(self.ifindex_pvid_list):
            return None

        return self.ifindex_pvid_list[right]

class QBridgeMIBObjects(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.17.7.1'):
    """
    'Forwarding Database' https://tools.ietf.org/html/rfc4363
    """

    fdb_updater = FdbUpdater()
    dot1q_port_updater = Dot1qPortUpdater()

    dot1qTpFdbPort = \
        SubtreeMIBEntry('2.2.1.2', fdb_updater, ValueType.INTEGER, fdb_updater.fdb_ifindex)

    dot1qPvid = \
        SubtreeMIBEntry('4.5.1.1', dot1q_port_updater, ValueType.INTEGER, dot1q_port_updater.port_vid)
