import json
from enum import unique, Enum

from sonic_ax_impl import mibs
from sonic_ax_impl.mibs.ietf import *
from ax_interface import MIBMeta, ValueType, MIBUpdater, MIBEntry, ContextualMIBEntry
from ax_interface.encodings import ObjectIdentifier
from ax_interface.util import mac_decimals

def fdb_vlanmac(fdb):
    return (int(fdb["vlan"]),) + mac_decimals(fdb["mac"])

class FdbUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.db_conn, \
        self.if_name_map, \
        self.if_alias_map, \
        self.if_id_map, \
        self.oid_sai_map, \
        self.oid_name_map = mibs.init_sync_d_interface_tables()
        # cache of interface counters
        self.if_counters = {}
        # call our update method once to "seed" data before the "Agent" starts accepting requests.
        self.update_data()

    def update_data(self):
        """
        Update redis (caches config)
        Pulls the table references for each interface.
        """
        self.db_conn.connect(mibs.ASIC_DB)
        fdb_strings = self.db_conn.keys(mibs.ASIC_DB, "ASIC_STATE:SAI_OBJECT_TYPE_FDB_ENTRY:*")
        self.vlanmac_ifindex_map = {}
        if fdb_strings is None:
            return
        for s in fdb_strings:
            fdb_str = s.decode()
            try:
                fdb = json.loads(fdb_str.split(":", maxsplit=2)[-1])
            except ValueError as e:  # includes simplejson.decoder.JSONDecodeError
                mibs.logger.error("SyncD 'ASIC_DB' includes invalid FDB_ENTRY '{}': {}.".format(fdb_str, e))
                self.vlanmac_ifindex_map = {}
                break

            ent = self.db_conn.get_all(mibs.ASIC_DB, s, blocking=True)
            port_oid = ent[b"SAI_FDB_ENTRY_ATTR_PORT_ID"]
            if port_oid.startswith(b"oid:0x"):
                port_oid = port_oid[6:]

            self.vlanmac_ifindex_map[fdb_vlanmac(fdb)] = mibs.get_index(self.if_id_map[port_oid])


    def fdb_ifindex(self, sub_id):
        assert sub_id is not None
        return self.vlanmac_ifindex_map[sub_id]

class FdbMIB(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.17.7.1.2.2.1'):
    """
    'Forwarding Database' https://tools.ietf.org/html/rfc4363
    """

    fdb_updater = FdbUpdater()

    fdb_range = fdb_updater.vlanmac_ifindex_map.keys()


    ifIndex = \
        ContextualMIBEntry('2', fdb_range, ValueType.INTEGER, fdb_updater.fdb_ifindex)
