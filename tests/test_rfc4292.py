import os
import sys
from unittest import TestCase

if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from sonic_ax_impl.mibs.ietf.rfc4292 import RouteUpdater

class TestRouteUpdater(TestCase):

    @mock.patch('sonic_py_common.multi_asic.get_all_namespaces', mock.MagicMock(return_value=({"front_ns": ['']})))
    @mock.patch('swsscommon.swsscommon.SonicV2Connector.get_all', mock.MagicMock(return_value=({"nexthop": "10.0.0.1", "ifname": "Ethernet0"})))
    def test_RouteUpdater_route_has_next_hop_and_iframe(self):
        updater = RouteUpdater()

        with mock.patch('sonic_ax_impl.mibs.logger.warning') as mocked_warning:
            updater.update_data()
            
            # check warning
            mocked_warning.assert_not_called()

        self.assertTrue(len(updater.route_dest_list) == 1)
        self.assertTrue(updater.route_dest_list[0] == (0, 0, 0, 0, 0, 0, 0, 0, 0, 10, 0, 0, 1))

    @mock.patch('sonic_py_common.multi_asic.get_all_namespaces', mock.MagicMock(return_value=({"front_ns": ['']})))
    @mock.patch('swsscommon.swsscommon.SonicV2Connector.get_all', mock.MagicMock(return_value=({"ifname": "Ethernet0"})))
    def test_RouteUpdater_route_no_next_hop(self):
        updater = RouteUpdater()

        with mock.patch('sonic_ax_impl.mibs.logger.warning') as mocked_warning:
            updater.update_data()
            
            # check warning
            expected = [
                mock.call("Route has no nexthop: ROUTE_TABLE:0.0.0.0/0 {'ifname': 'Ethernet0'}")
            ]
            mocked_warning.assert_has_calls(expected)

        self.assertTrue(len(updater.route_dest_list) == 0)

    @mock.patch('sonic_py_common.multi_asic.get_all_namespaces', mock.MagicMock(return_value=({"front_ns": ['']})))
    @mock.patch('swsscommon.swsscommon.SonicV2Connector.get_all', mock.MagicMock(return_value=({"nexthop": "10.0.0.1"})))
    def test_RouteUpdater_route_no_iframe(self):
        updater = RouteUpdater()

        with mock.patch('sonic_ax_impl.mibs.logger.warning') as mocked_warning:
            updater.update_data()
            
            # check warning
            expected = [
                mock.call("Route has no ifname: ROUTE_TABLE:0.0.0.0/0 {'nexthop': '10.0.0.1'}")
            ]
            mocked_warning.assert_has_calls(expected)

        self.assertTrue(len(updater.route_dest_list) == 0)
