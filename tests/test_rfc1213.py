import asyncio
import os
import sys
from unittest import TestCase

if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from sonic_ax_impl.mibs.ietf.rfc1213 import NextHopUpdater


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
                    mock.call("MIBUpdater.start() caught an unexpected exception during update_data()")
                ]
                mocked_exception.assert_has_calls(expected)

        self.assertTrue(len(self.updater.route_list) == 0)
