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

from sonic_ax_impl.mibs.ietf.rfc2863 import InterfaceMIBUpdater
from sonic_ax_impl.mibs.ietf.rfc2863 import DbTables64

class TestInterfaceMIBUpdater(TestCase):

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
    def test_InterfaceMIBUpdater_get_high_speed(self):
        updater = InterfaceMIBUpdater()

        with mock.patch('sonic_ax_impl.mibs.logger.warning') as mocked_warning:
            updater.reinit_data()
            updater.update_data()
            
            # get speed of port-channel 103, OID is 1103
            speed = updater.get_high_speed((1103,))
            print("103 speed: {}".format(speed))
            self.assertTrue(speed == 40000)
            
            # get speed of port-channel 999, OID is 1999
            speed = updater.get_high_speed((1999,))
            print("999 speed: {}".format(speed))
            self.assertTrue(speed == 0)


    @mock.patch('sonic_ax_impl.mibs.Namespace.get_sync_d_from_all_namespace', mock_get_sync_d_from_all_namespace)
    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_get_all', mock_dbs_get_all)
    @mock.patch('sonic_ax_impl.mibs.lag_entry_table', mock_lag_entry_table)
    @mock.patch('sonic_ax_impl.mibs.init_mgmt_interface_tables', mock_init_mgmt_interface_tables)
    def test_InterfaceMIBUpdater_get_counters(self):
        updater = InterfaceMIBUpdater()

        updater.reinit_data()
        updater.update_data()
        def mock_get_counter(oid, table_name, mask):
            if oid == 121:
                return None
            else:
                return updater._get_counter(oid, table_name, mask)

        try:
            counter = updater.get_counter64((1103,), DbTables64(6))
        except TypeError:
            self.fail("Caught Type error")
        self.assertTrue(counter == None)

