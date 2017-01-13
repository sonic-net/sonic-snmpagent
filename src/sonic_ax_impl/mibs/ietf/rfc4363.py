from enum import unique, Enum

from sonic_ax_impl import mibs
from ax_interface import MIBMeta, ValueType, MIBUpdater, MIBEntry, ContextualMIBEntry
from ax_interface.encodings import ObjectIdentifier


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
        fdb_strings = db_conn.keys(APPS_DB, "ASIC_STATE:SAI_OBJECT_TYPE_FDB_ENTRY:{")
        self.vlanmac_oid_map = {}
        for s in fdb_strings:
            fdb = json.from(s)
            ent = db_conn.get_all(s)
            port = ent["SAI_FDB_ENTRY_ATTR_PORT_ID"]
            ## TODO
            self.vlanmac_ifindex_map[fdb] = port

    def fdb_ifindex(self, vlanmac)
        return self.elf.vlanmac_ifindex_map[vlanmac]


class FdbMIB(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.17.7.1.2.2.1.2'):
    """
    'interfaces' https://tools.ietf.org/html/rfc4363
    """

    if_updater = FdbUpdater()
    _ifNumber = len(if_updater.if_name_map)

    # OID sub-identifiers are 1-based, while the actual interfaces are zero-based.
    # offset the interface range when registering the OIDs
    fdb_range = if_updater.vlanmac_ifindex_map.keys()

    # (subtree, value_type, callable_, *args, handler=None)
    #ifNumber = MIBEntry('1', ValueType.INTEGER, lambda: InterfacesMIB._ifNumber)

    # ifTable ::= { interfaces 2 }
    # ifEntry ::= { ifTable 1 }

    ifIndex = \
        ContextualMIBEntry('', fdb_range, ValueType.INTEGER, FdbUpdater.fdb_ifindex)
