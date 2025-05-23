import asyncio
import os
import sonic_ax_impl
import sys
from unittest import TestCase
import pytest
from unittest.mock import MagicMock
from sonic_ax_impl.mibs.ietf.rfc1213 import NetmaskUpdater

if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from sonic_ax_impl.mibs.ietf.rfc1213 import NextHopUpdater, InterfacesUpdater, DbTables, NetmaskUpdater


class TestNextHopUpdater(TestCase):

    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_keys', mock.MagicMock(return_value=(["ROUTE_TABLE:0.0.0.0/0"])))
    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_get_all', mock.MagicMock(return_value=({"nexthop": "10.0.0.1,10.0.0.3", "ifname": "Ethernet0,Ethernet4"})))
    def test_NextHopUpdater_route_has_next_hop(self):
        updater = NextHopUpdater()

        with mock.patch('sonic_ax_impl.mibs.logger.warning') as mocked_warning:
            updater.update_data()
            
            # check warning
            mocked_warning.assert_not_called()

        self.assertTrue(len(updater.route_list) == 1)
        self.assertTrue(updater.route_list[0] == (0,0,0,0))

    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_keys', mock.MagicMock(return_value=(["ROUTE_TABLE:0.0.0.0/0"])))
    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_get_all', mock.MagicMock(return_value=({"ifname": "Ethernet0,Ethernet4"})))
    def test_NextHopUpdater_route_no_next_hop(self):
        updater = NextHopUpdater()

        with mock.patch('sonic_ax_impl.mibs.logger.warning') as mocked_warning:
            updater.update_data()
            
            # check warning
            expected = [
                mock.call("Route has no nexthop: ROUTE_TABLE:0.0.0.0/0 {'ifname': 'Ethernet0,Ethernet4'}")
            ]
            mocked_warning.assert_has_calls(expected)

        self.assertTrue(len(updater.route_list) == 0)


class TestNextHopUpdaterRedisException(TestCase):
    def __init__(self, name):
        super().__init__(name)
        self.throw_exception = True
        self.updater = NextHopUpdater()
    
    # setup mock method, throw exception when first time call it
    def mock_dbs_keys(self, *args, **kwargs):
        if self.throw_exception:
            self.throw_exception = False
            raise RuntimeError

        self.updater.run_event.clear()
        return None

    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_get_all', mock.MagicMock(return_value=({"ifname": "Ethernet0,Ethernet4"})))
    def test_NextHopUpdater_redis_exception(self):
        with mock.patch('sonic_ax_impl.mibs.Namespace.dbs_keys', self.mock_dbs_keys):
            with mock.patch('ax_interface.logger.exception') as mocked_exception:
                self.updater.run_event.set()
                self.updater.frequency = 1
                self.updater.reinit_rate = 1
                self.updater.update_counter = 1
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.updater.start())
                loop.close()

                # check warning
                expected = [
                    mock.call("MIBUpdater.start() caught a RuntimeError during update_data(), will reinitialize the connections")
                ]
                mocked_exception.assert_has_calls(expected)


    @mock.patch('sonic_ax_impl.mibs.init_mgmt_interface_tables', mock.MagicMock(return_value=([{}, {}])))
    def test_InterfacesUpdater_re_init_redis_exception(self):

        def mock_get_sync_d_from_all_namespace(per_namespace_func, db_conn):
            if per_namespace_func == sonic_ax_impl.mibs.init_sync_d_interface_tables:
                return [{}, {}, {}, {}]

            if per_namespace_func == sonic_ax_impl.mibs.init_sync_d_vlan_tables:
                return [{}, {}, {}]

            if per_namespace_func == sonic_ax_impl.mibs.init_sync_d_rif_tables:
                return [{}, {}]
            
            return [{}, {}, {}, {}, {}]
        
        updater = InterfacesUpdater()
        with mock.patch('sonic_ax_impl.mibs.Namespace.get_sync_d_from_all_namespace', mock_get_sync_d_from_all_namespace):
            with mock.patch('sonic_ax_impl.mibs.Namespace.connect_namespace_dbs') as connect_namespace_dbs:
                updater.reinit_connection()
                updater.reinit_data()

                # check re-init
                connect_namespace_dbs.assert_called()


    def test_InterfaceUpdater_get_counters(self):

        def mock_lag_entry_table(lag_name):
            if lag_name == "PortChannel103":
                return "PORT_TABLE:Ethernet120"

            return

        def mock_get_counter(oid, table_name):
            if oid == 121:
                return None
            else:
                return updater._get_counter(oid, table_name, mask)

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

            if per_namespace_func == sonic_ax_impl.mibs.init_sync_d_rif_tables:
                return [{},{}]


            return [{},{},{}]

        def mock_init_mgmt_interface_tables(db_conn):
            return [{},{}]

        def mock_dbs_get_all(dbs, db_name, hash, *args, **kwargs):
            if hash == "PORT_TABLE:Ethernet120":
                return {'admin_status': 'up', 'alias': 'fortyGigE0/120', 'description': 'ARISTA03T1:Ethernet1', 'index': '30', 'lanes': '101,102,103,104', 'mtu': '9100', 'oper_status': 'up', 'pfc_asym': 'off', 'speed': '40000', 'tpid': '0x8100'}

            return

        with mock.patch('sonic_ax_impl.mibs.Namespace.get_sync_d_from_all_namespace', mock_get_sync_d_from_all_namespace):
            with mock.patch('sonic_ax_impl.mibs.lag_entry_table', mock_lag_entry_table):
                with mock.patch('sonic_ax_impl.mibs.init_mgmt_interface_tables', mock_init_mgmt_interface_tables):
                    with mock.patch('sonic_ax_impl.mibs.Namespace.dbs_get_all', mock_dbs_get_all):
                        updater = InterfacesUpdater()
                        updater.reinit_data()
                        updater.update_data()

        try:
            counter = updater.get_counter((1103,), DbTables(21))
        except TypeError:
            self.fail("Caught Type error")
        self.assertTrue(counter == None)

class TestNetmaskUpdater(TestCase):
    @mock.patch("sonic_ax_impl.mibs.Namespace.init_namespace_dbs", return_value="mock_db_conn")
    @mock.patch('sonic_ax_impl.mibs.get_index_from_str', return_value=1)
    @mock.patch('ax_interface.util.ip2byte_tuple', side_effect=lambda ip: tuple(map(int, ip.split('.'))))
    def test_update_netmask_info(self, mock_ip2byte, mock_get_index, mock_namespace):
        updater = NetmaskUpdater()
        updater._update_netmask_info("eth0", "192.168.1.1/24")

        expected_key = (4, 192, 168, 1, 1)
        self.assertIn(expected_key, updater.netmask_map)
        self.assertIn(expected_key, updater.netmask_list)

    @mock.patch("ax_interface.util.ip2byte_tuple", side_effect=lambda ip: tuple(map(int, ip.split('.'))))
    @mock.patch("sonic_ax_impl.mibs.get_index_from_str", return_value=2)
    @mock.patch("sonic_ax_impl.mibs.ietf.rfc1213.Namespace.init_namespace_dbs", return_value="mock_db_conn")
    @mock.patch("sonic_ax_impl.mibs.ietf.rfc1213.os.popen")
    def test_update_data(self, mock_popen, mock_init_ns, mock_get_index, mock_ip2byte):
        mock_dbs_keys = mock.MagicMock(return_value=[
            "INTF_TABLE:Eth0:192.168.1.1/24",
            "INTF_TABLE:Docker0:10.0.0.1/8"
        ])
        mock_init_ns.return_value = "mock_db_conn"

        with mock.patch("sonic_ax_impl.mibs.ietf.rfc1213.Namespace.dbs_keys", mock_dbs_keys):
            def popen_side_effect(cmd):
                mock_proc = MagicMock()
                if "Eth0" in cmd and "print $2" in cmd:
                    mock_proc.read.return_value = "192.168.1.1/24\n"
                elif "docker0" in cmd and "print $2" in cmd:
                    mock_proc.read.return_value = "172.17.0.1/24\n"
                elif "docker0" in cmd and "print $4" in cmd:
                    mock_proc.read.return_value = "172.17.255.255/24\n"
                else:
                    mock_proc.read.return_value = "192.168.1.1/24\n"
                return mock_proc

            mock_popen.side_effect = popen_side_effect

            updater = NetmaskUpdater()
            updater.update_data()

            self.assertGreater(len(updater.netmask_map), 0)
            self.assertTrue(all(isinstance(k, tuple) for k in updater.netmask_list))

    def test_get_next(self):
        updater = NetmaskUpdater()
        updater.netmask_list = [(4, 10, 0, 0, 1), (4, 192, 168, 1, 1), (4, 192, 168, 1, 2)]
        self.assertEqual(updater.get_next((4, 10, 0, 0, 1)), (4, 192, 168, 1, 1))
        self.assertEqual(updater.get_next((4, 192, 168, 1, 2)), None)