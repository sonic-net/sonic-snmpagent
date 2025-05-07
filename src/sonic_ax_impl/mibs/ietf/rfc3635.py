from enum import Enum, unique
from bisect import bisect_right

from sonic_ax_impl import mibs
from ax_interface.mib import MIBMeta, MIBUpdater, ValueType, SubtreeMIBEntry, OverlayAdpaterMIBEntry, OidMIBEntry
from sonic_ax_impl.mibs import Namespace

@unique
class DbTables32(int, Enum):
    """
    Maps database tables names to SNMP sub-identifiers.
    https://datatracker.ietf.org/doc/html/rfc3635#section-4

    REDIS_TABLE_NAME = (RFC3635 OID NUMBER)
    """

    # dot3StatsAlignmentErrors ::= { dot3StatsEntry 2 }
    SAI_PORT_STAT_DOT3_STATS_ALIGNMENT_ERRORS = 2
    # dot3StatsFCSErrors ::= { dot3StatsEntry 3 }
    SAI_PORT_STAT_DOT3_STATS_FCS_ERRORS = 3
    # dot3StatsSingleCollisionFrames ::= { dot3StatsEntry 4 }
    SAI_PORT_STAT_DOT3_STATS_SINGLE_COLLISION_FRAMES = 4
    # dot3StatsMultipleCollisionFrames ::= { dot3StatsEntry 5 }
    SAI_PORT_STAT_DOT3_STATS_MULTIPLE_COLLISION_FRAMES = 5
    # dot3StatsSQETestErrors ::= { dot3StatsEntry 6 }
    SAI_PORT_STAT_DOT3_STATS_SQE_TEST_ERRORS = 6
    # dot3StatsDeferredTransmissions ::= { dot3StatsEntry 7 }
    SAI_PORT_STAT_DOT3_STATS_DEFERRED_TRANSMISSIONS = 7
    # dot3StatsLateCollisions ::= { dot3StatsEntry 8 }
    SAI_PORT_STAT_DOT3_STATS_LATE_COLLISIONS = 8
    # dot3StatsExcessiveCollisions ::= { dot3StatsEntry 9 }
    SAI_PORT_STAT_DOT3_STATS_EXCESSIVE_COLLISIONS = 9
    # dot3StatsInternalMacTransmitErrors ::= { dot3StatsEntry 10 }
    SAI_PORT_STAT_DOT3_STATS_INTERNAL_MAC_TRANSMIT_ERRORS = 10
    # dot3StatsCarrierSenseErrors ::= { dot3StatsEntry 11 }
    SAI_PORT_STAT_DOT3_STATS_CARRIER_SENSE_ERRORS = 11
    # { dot3StatsEntry 12 } is not assigned
    # dot3StatsFrameTooLongs ::= { dot3StatsEntry 13 }
    SAI_PORT_STAT_DOT3_STATS_FRAME_TOO_LONGS = 13
    # { dot3StatsEntry 14 } is not assigned
    # { dot3StatsEntry 15 } is not assigned
    # dot3StatsInternalMacReceiveErrors ::= { dot3StatsEntry 16 }
    SAI_PORT_STAT_DOT3_STATS_INTERNAL_MAC_RECEIVE_ERRORS = 16
    # dot3StatsEtherChipSet ::= { dot3StatsEntry 17 } -- deprecated
    # dot3StatsSymbolErrors ::= { dot3StatsEntry 18 }
    SAI_PORT_STAT_DOT3_STATS_SYMBOL_ERRORS = 18
    # dot3StatsDuplexStatus ::= { dot3StatsEntry 19} -- no SAI stat
    # dot3StatsRateControlAbility ::= { dot3StatsEntry 20 } -- no SAI stat
    # dot3StatsRateControlStatus ::= { dot3StatsEntry 21 } -- no SAI stat


@unique
class DbTables64(int, Enum):
    # dot3HCStatsAlignmentErrors ::= { dot3HCStatsEntry 1 }
    SAI_PORT_STAT_DOT3_STATS_ALIGNMENT_ERRORS = 1
    # dot3HCStatsFCSErrors ::= { dot3HCStatsEntry 2 }
    SAI_PORT_STAT_DOT3_STATS_FCS_ERRORS = 2
    # dot3HCStatsInternalMacTransmitErrors ::= { dot3HCStatsEntry 3 }
    SAI_PORT_STAT_DOT3_STATS_INTERNAL_MAC_TRANSMIT_ERRORS = 3
    # dot3HCStatsFrameTooLongs ::= { dot3HCStatsEntry 4 }
    SAI_PORT_STAT_DOT3_STATS_FRAME_TOO_LONGS = 4
    # dot3HCStatsInternalMacReceiveErrors ::= { dot3HCStatsEntry 5 }
    SAI_PORT_STAT_DOT3_STATS_INTERNAL_MAC_RECEIVE_ERRORS = 5
    # dot3HCStatsSymbolErrors ::= { dot3HCStatsEntry 6 }
    SAI_PORT_STAT_DOT3_STATS_SYMBOL_ERRORS = 6


class dot3MIBUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()

        self.db_conn = Namespace.init_namespace_dbs()

        self.lag_name_if_name_map = {}
        self.if_name_lag_name_map = {}
        self.oid_lag_name_map = {}
        self.mgmt_oid_name_map = {}
        self.mgmt_alias_map = {}
        self.vlan_oid_name_map = {}
        self.vlan_name_map = {}
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

        self.lag_name_if_name_map, \
        self.if_name_lag_name_map, \
        self.oid_lag_name_map, _, _ = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_lag_tables, self.db_conn)
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

        self.if_range = sorted(list(self.oid_name_map.keys()) +
                               list(self.oid_lag_name_map.keys()) +
                               list(self.mgmt_oid_name_map.keys()) +
                               list(self.vlan_oid_name_map.keys()))
        self.if_range = [(i,) for i in self.if_range]

    def update_data(self):
        """
        Update redis (caches config)
        Pulls the table references for each interface.
        """
        for sai_id_key in self.if_id_map:
            namespace, sai_id = mibs.split_sai_id_key(sai_id_key)
            if_idx = mibs.get_index_from_str(self.if_id_map[sai_id_key])
            counter_table = self.namespace_db_map[namespace].get_all(mibs.COUNTERS_DB, \
                    mibs.counter_table(sai_id))
            if counter_table is None:
                counter_table = {}
            self.if_counters[if_idx] = counter_table

        self.lag_name_if_name_map, \
        self.if_name_lag_name_map, \
        self.oid_lag_name_map, \
        self.lag_sai_map, _ = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_lag_tables, self.db_conn)

        self.if_range = sorted(list(self.oid_name_map.keys()) +
                               list(self.oid_lag_name_map.keys()) +
                               list(self.mgmt_oid_name_map.keys()) +
                               list(self.vlan_oid_name_map.keys()))
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
            return self.get_oid(sub_id) - 1

    def get_counter32(self, sub_id, table_name):
        oid = self.get_oid(sub_id)
        if not oid:
            return

        return self._get_counter(oid, table_name, 0x00000000ffffffff)

    def get_counter64(self, sub_id, table_name):
        oid = self.get_oid(sub_id)
        if not oid:
            return

        return self._get_counter(oid, table_name, 0xffffffffffffffff)

    def _get_counter(self, oid, table_name, mask):
        """
        :param oid: The 1-based sub-identifier query.
        :param table_name: the redis table (either IntEnum or string literal) to query.
        :param mask: mask to apply to counter
        :return: the counter for the respective sub_id/table.
        """

        if oid in self.mgmt_oid_name_map:
            # TODO: mgmt counters not available through SNMP right now
            # COUNTERS DB does not have support for generic linux (mgmt) interface counters
            return 0

        if oid in self.oid_lag_name_map:
            counter_value = 0
            for lag_member in self.lag_name_if_name_map[self.oid_lag_name_map[oid]]:
                member_counter = self._get_counter(mibs.get_index_from_str(lag_member), table_name, mask)
                if member_counter is not None:
                    counter_value += member_counter
                else:
                    return None

            return counter_value & mask

        # Enum.name or table_name = 'name_of_the_table'
        _table_name = getattr(table_name, 'name', table_name)
        try:
            counter_value = self.if_counters[oid][_table_name]
            # truncate to 32-bit counter (database implements 64-bit counters)
            counter_value = int(counter_value) & mask
            # done!
            return counter_value
        except KeyError as e:
            mibs.logger.warning("SyncD 'COUNTERS_DB' missing attribute '{}'.".format(e))
            return None

    def _get_if_entry(self, oid):
        """
        :param oid: The 1-based sub-identifier query.
        :return: the DB entry for the respective sub_id.
        """
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


class etherMIBObjects(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.10.7'):
    """
    'etherMIBObjects' https://datatracker.ietf.org/doc/html/rfc3635#section-4
    """
    if_updater = dot3MIBUpdater()

    oidtree_updater = mibs.RedisOidTreeUpdater(prefix_str='1.3.6.1.2.1.10.7')

    # dot3StatsTable = '2'
    # dot3StatsEntry = '2.1'

    ifIndex = \
        SubtreeMIBEntry('2.1.1', if_updater, ValueType.INTEGER, if_updater.if_index)

    dot3StatsAlignmentErrors = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.2', if_updater, ValueType.COUNTER_32, if_updater.get_counter32,
                           DbTables32(2)),
            OidMIBEntry('2.1.2', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    dot3StatsFCSErrors = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.3', if_updater, ValueType.COUNTER_32, if_updater.get_counter32,
                           DbTables32(3)),
            OidMIBEntry('2.1.3', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    dot3StatsSingleCollisionFrames = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.4', if_updater, ValueType.COUNTER_32, if_updater.get_counter32,
                           DbTables32(4)),
            OidMIBEntry('2.1.4', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )
   
    dot3StatsMultipleCollisionFrames = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.5', if_updater, ValueType.COUNTER_32, if_updater.get_counter32,
                           DbTables32(5)),
            OidMIBEntry('2.1.5', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    dot3StatsSQETestErrors = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.6', if_updater, ValueType.COUNTER_32, if_updater.get_counter32,
                           DbTables32(6)),
            OidMIBEntry('2.1.6', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    dot3StatsDeferredTransmissions = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.7', if_updater, ValueType.COUNTER_32, if_updater.get_counter32,
                           DbTables32(7)),
            OidMIBEntry('2.1.7', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    dot3StatsLateCollisions = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.8', if_updater, ValueType.COUNTER_32, if_updater.get_counter32,
                           DbTables32(8)),
            OidMIBEntry('2.1.8', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    dot3StatsExcessiveCollisions = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.9', if_updater, ValueType.COUNTER_32, if_updater.get_counter32,
                           DbTables32(9)),
            OidMIBEntry('2.1.9', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    dot3StatsInternalMacTransmitErrors = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.10', if_updater, ValueType.COUNTER_32, if_updater.get_counter32,
                           DbTables32(10)),
            OidMIBEntry('2.1.10', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    dot3StatsCarrierSenseErrors = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.11', if_updater, ValueType.COUNTER_32, if_updater.get_counter32,
                           DbTables32(11)),
            OidMIBEntry('2.1.11', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    dot3StatsFrameTooLongs = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.13', if_updater, ValueType.COUNTER_32, if_updater.get_counter32,
                           DbTables32(13)),
            OidMIBEntry('2.1.13', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    dot3StatsInternalMacReceiveErrors = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.16', if_updater, ValueType.COUNTER_32, if_updater.get_counter32,
                           DbTables32(16)),
            OidMIBEntry('2.1.16', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    dot3StatsSymbolErrors = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('2.1.18', if_updater, ValueType.COUNTER_32, if_updater.get_counter32,
                           DbTables32(18)),
            OidMIBEntry('2.1.18', ValueType.COUNTER_32, oidtree_updater.get_oidvalue)
        )

    # dot3HCStatsTable = '11'
    # dot3HCStatsEntry = '11.1'

    dot3HCStatsAlignmentErrors = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('11.1.1', if_updater, ValueType.COUNTER_64, if_updater.get_counter64,
                           DbTables64(1)),
            OidMIBEntry('11.1.1', ValueType.COUNTER_64, oidtree_updater.get_oidvalue)
        )

    dot3HCStatsFCSErrors = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('11.1.2', if_updater, ValueType.COUNTER_64, if_updater.get_counter64,
                           DbTables64(2)),
            OidMIBEntry('11.1.2', ValueType.COUNTER_64, oidtree_updater.get_oidvalue)
        )

    dot3HCStatsInternalMacTransmitErrors = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('11.1.3', if_updater, ValueType.COUNTER_64, if_updater.get_counter64,
                           DbTables64(3)),
            OidMIBEntry('11.1.3', ValueType.COUNTER_64, oidtree_updater.get_oidvalue)
        )

    dot3HCStatsFrameTooLongs = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('11.1.4', if_updater, ValueType.COUNTER_64, if_updater.get_counter64,
                           DbTables64(4)),
            OidMIBEntry('11.1.4', ValueType.COUNTER_64, oidtree_updater.get_oidvalue)
        )

    dot3HCStatsInternalMacReceiveErrors = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('11.1.5', if_updater, ValueType.COUNTER_64, if_updater.get_counter64,
                           DbTables64(5)),
            OidMIBEntry('11.1.5', ValueType.COUNTER_64, oidtree_updater.get_oidvalue)
        )

    dot3HCStatsInternalMacReceiveErrors = \
        OverlayAdpaterMIBEntry(
            SubtreeMIBEntry('11.1.6', if_updater, ValueType.COUNTER_64, if_updater.get_counter64,
                           DbTables64(6)),
            OidMIBEntry('11.1.6', ValueType.COUNTER_64, oidtree_updater.get_oidvalue)
        )

