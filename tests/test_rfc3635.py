import os
import sys
import sonic_ax_impl
from unittest import TestCase

if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from sonic_ax_impl.mibs.ietf.rfc3635 import dot3MIBUpdater
from sonic_ax_impl.mibs.ietf.rfc3635 import DbTables32
from sonic_ax_impl.mibs.ietf.rfc3635 import DbTables64
from sonic_ax_impl.mibs.ietf.rfc3635 import etherMIBObjects
from ax_interface import util
from ax_interface.mib import MIBMeta

def make_updater():
    # Ethernet0 -> 1, Ethernet4 -> 5, PortChannel01 -> 1001, eth0 -> 10000, Vlan1000 -> 3000.
    updater = dot3MIBUpdater()
    updater.oid_name_map = {1: 'Ethernet0', 5: 'Ethernet4'}
    updater.oid_lag_name_map = {1001: 'PortChannel01'}
    updater.lag_name_if_name_map = {'PortChannel01': ['Ethernet0', 'Ethernet4']}
    updater.mgmt_oid_name_map = {10000: 'eth0'}
    updater.vlan_oid_name_map = {3000: 'Vlan1000'}
    updater.if_counters = {
        1: {'SAI_PORT_STAT_DOT3_STATS_FCS_ERRORS': '7'},
        5: {'SAI_PORT_STAT_DOT3_STATS_FCS_ERRORS': str(2**32 + 3)},
    }
    updater.if_range = [(1,), (5,), (1001,), (3000,), (10000,)]
    return updater


class Testdot3MIBUpdater(TestCase):

    def mock_get_sync_d_from_all_namespace(per_namespace_func, dbs):
        if per_namespace_func == sonic_ax_impl.mibs.init_sync_d_lag_tables:
            return [{'PortChannel999': [], 'PortChannel103': ['Ethernet120']}, # lag_name_if_name_map
                    {},
                    {1999: 'PortChannel999', 1103: 'PortChannel103'}, # oid_lag_name_map
                    {},
                    {}]

        if per_namespace_func == sonic_ax_impl.mibs.init_sync_d_interface_tables:
            return [{},
                    {},
                    {},
                    {121: 'Ethernet120'}]

        return [{},{},{}]

    def mock_lag_entry_table(lag_name):
        if lag_name == "PortChannel103":
            return "PORT_TABLE:Ethernet120"

        return

    def mock_dbs_get_all(dbs, db_name, hash, *args, **kwargs):
        if hash == "PORT_TABLE:Ethernet120":
            return {'admin_status': 'up', 'alias': 'fortyGigE0/120', 'description': 'ARISTA03T1:Ethernet1', 'index': '30', 'lanes': '101,102,103,104', 'mtu': '9100', 'oper_status': 'up', 'pfc_asym': 'off', 'speed': '40000', 'tpid': '0x8100'}

        return

    def mock_init_mgmt_interface_tables(db_conn):
        return [{},{}]

    @mock.patch('sonic_ax_impl.mibs.Namespace.get_sync_d_from_all_namespace', mock_get_sync_d_from_all_namespace)
    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_get_all', mock_dbs_get_all)
    @mock.patch('sonic_ax_impl.mibs.lag_entry_table', mock_lag_entry_table)
    @mock.patch('sonic_ax_impl.mibs.init_mgmt_interface_tables', mock_init_mgmt_interface_tables)
    def test_dot3MIBUpdater_get_counters(self):
        updater = dot3MIBUpdater()

        updater.reinit_data()
        updater.update_data()
        try:
            counter = updater.get_counter64((1103,), DbTables64(6))
        except TypeError:
            self.fail("Caught Type error")
        self.assertTrue(counter == None)

    def test_get_next(self):
        updater = make_updater()
        self.assertEqual(updater.get_next(()), (1,))
        self.assertEqual(updater.get_next((1,)), (5,))
        self.assertIsNone(updater.get_next((10000,)))

    def test_get_oid_and_if_index(self):
        updater = make_updater()
        self.assertEqual(updater.get_oid((5,)), 5)
        self.assertIsNone(updater.get_oid((2,)))
        self.assertEqual(updater.if_index((5,)), 4)
        self.assertIsNone(updater.if_index(()))

    def test_port_counters(self):
        updater = make_updater()
        self.assertEqual(updater.get_counter64((1,), DbTables64(2)), 7)
        self.assertEqual(updater.get_counter64((5,), DbTables64(2)), 2**32 + 3)
        # The 32-bit table truncates the 64-bit DB value.
        self.assertEqual(updater.get_counter32((5,), DbTables32(3)), 3)
        # A counter missing from COUNTERS_DB reads as None.
        self.assertIsNone(updater.get_counter32((1,), DbTables32(2)))
        # An unknown index reads as None.
        self.assertIsNone(updater.get_counter32((2,), DbTables32(3)))
        self.assertIsNone(updater.get_counter64((2,), DbTables64(2)))

    def test_lag_counter_is_sum_of_members(self):
        updater = make_updater()
        self.assertEqual(updater.get_counter64((1001,), DbTables64(2)), 2**32 + 10)
        self.assertEqual(updater.get_counter32((1001,), DbTables32(3)), 10)

    def test_mgmt_counter_is_zero(self):
        updater = make_updater()
        self.assertEqual(updater.get_counter64((10000,), DbTables64(2)), 0)

    def test_get_if_entry_tables(self):
        updater = make_updater()
        calls = []

        def fake_dbs_get_all(dbs, db_name, table, *args, **kwargs):
            calls.append((db_name, table))
            return {'table': table}

        with mock.patch('sonic_ax_impl.mibs.Namespace.dbs_get_all', fake_dbs_get_all):
            self.assertEqual(updater._get_if_entry(1), {'table': 'PORT_TABLE:Ethernet0'})
            self.assertEqual(updater._get_if_entry(1001), {'table': 'LAG_TABLE:PortChannel01'})
            self.assertEqual(updater._get_if_entry(3000), {'table': 'VLAN_TABLE:Vlan1000'})
            self.assertEqual(updater._get_if_entry(10000), {'table': 'MGMT_PORT|eth0'})
            self.assertIsNone(updater._get_if_entry(2))

        self.assertEqual(calls[3][0], sonic_ax_impl.mibs.CONFIG_DB)
        self.assertTrue(all(db == sonic_ax_impl.mibs.APPL_DB for db, _ in calls[:3]))

    def test_hc_stats_oids_registered(self):
        prefix = util.oid2tuple('.1.3.6.1.2.1.10.7.11.1')
        subids = getattr(etherMIBObjects, MIBMeta.KEYSTORE)
        for i in range(1, 7):
            self.assertIn(prefix + (i,), subids)
