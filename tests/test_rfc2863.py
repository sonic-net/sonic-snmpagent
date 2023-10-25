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

class TestInterfaceMIBUpdater(TestCase):

    def mock_get_sync_d_from_all_namespace(per_namespace_func, dbs):
        if per_namespace_func == sonic_ax_impl.mibs.init_sync_d_lag_tables:
            return [{b'PortChannel999': [], b'PortChannel103': [b'Ethernet120']}, # lag_name_if_name_map
                    {},
                    {1999: b'PortChannel999', 1103: b'PortChannel103'}, # oid_lag_name_map
                    {}]

        if per_namespace_func == sonic_ax_impl.mibs.init_sync_d_interface_tables:
            return [{},
                    {},
                    {},
                    {121: b'Ethernet120'}]

        return [{},{},{}]

    def mock_lag_entry_table(lag_name):
        if lag_name == b"PortChannel103":
            return b"PORT_TABLE:Ethernet120"

        return

    def mock_dbs_get_all(dbs, db_name, hash, *args, **kwargs):
        if hash == b"PORT_TABLE:Ethernet120":
            return {b'admin_status': b'up', b'alias': b'fortyGigE0/120', b'description': b'ARISTA03T1:Ethernet1', b'index': b'30', b'lanes': b'101,102,103,104', b'mtu': b'9100', b'oper_status': b'up', b'pfc_asym': b'off', b'speed': b'40000', b'tpid': b'0x8100'}

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
