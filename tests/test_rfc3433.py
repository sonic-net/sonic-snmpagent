import os
import sys
from unittest import TestCase

if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from sonic_ax_impl.mibs.ietf.rfc3433 import PhysicalSensorTableMIBUpdater

class TestPhysicalSensorTableMIBUpdater(TestCase):

    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_get_all', mock.MagicMock(return_value=({"hardwarerev": "1.0"})))
    def test_PhysicalSensorTableMIBUpdater_transceiver_info_key_missing(self):
        updater = PhysicalSensorTableMIBUpdater()
        updater.transceiver_dom.append("TRANSCEIVER_INFO|Ethernet0")

        with mock.patch('sonic_ax_impl.mibs.logger.warn') as mocked_warn:
            updater.update_data()

            # check warning
            mocked_warn.assert_called()

        self.assertTrue(len(updater.sub_ids) == 0)

    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_keys', mock.MagicMock(return_value=(None)))
    @mock.patch('swsscommon.swsscommon.SonicV2Connector.keys', mock.MagicMock(return_value=(None)))
    def test_PhysicalSensorTableMIBUpdater_re_init_redis_exception(self):
        updater = PhysicalSensorTableMIBUpdater()

        with mock.patch('sonic_ax_impl.mibs.Namespace.connect_all_dbs') as connect_all_dbs:
            updater.reinit_connection()

            # check re-init
            connect_all_dbs.assert_called()