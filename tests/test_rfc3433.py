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

    @mock.patch('swsscommon.swsscommon.SonicV2Connector.get_all', mock.MagicMock(return_value=({"position_in_parent" : '0', "parent_name" : "FABRIC-CARD0"})))
    def test_PhysicalSensorTableMIBUpdater_fabriccard_update_fan_sensor_data(self):
        updater = PhysicalSensorTableMIBUpdater()
        updater.fan_sensor = ['FABRIC_MODULE|FAN']

        with mock.patch('sonic_ax_impl.mibs.ietf.rfc3433.get_fabric_card_sub_id') as mocked_get_fc_subid:
            updater.update_fan_sensor_data()

            # check fabric card subid function is called to get parent's sub id
            mocked_get_fc_subid.assert_called()

    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_keys')
    @mock.patch('swsscommon.swsscommon.SonicV2Connector.keys', mock.MagicMock(return_value=None))
    def test_reinit_data_transceiver_dom_temperature_fallback(self, mock_dbs_keys):
        """
        Given: TRANSCEIVER_DOM_TEMPERATURE table is empty
        When: reinit_data is called
        Then: Should fallback to TRANSCEIVER_DOM_SENSOR table
        """
        # First call returns None (new table empty), second returns data (legacy table)
        mock_dbs_keys.side_effect = [
            None,  # TRANSCEIVER_DOM_TEMPERATURE returns empty
            ['TRANSCEIVER_DOM_SENSOR|Ethernet0'],  # TRANSCEIVER_DOM_SENSOR has data
        ]

        updater = PhysicalSensorTableMIBUpdater()
        updater.reinit_data()

        # Verify it used the fallback data
        self.assertEqual(updater.transceiver_dom, ['TRANSCEIVER_DOM_SENSOR|Ethernet0'])
        self.assertEqual(mock_dbs_keys.call_count, 2)

    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_keys')
    @mock.patch('swsscommon.swsscommon.SonicV2Connector.keys', mock.MagicMock(return_value=None))
    def test_reinit_data_transceiver_dom_temperature_preferred(self, mock_dbs_keys):
        """
        Given: TRANSCEIVER_DOM_TEMPERATURE table has data
        When: reinit_data is called
        Then: Should use new table, not fallback
        """
        mock_dbs_keys.return_value = ['TRANSCEIVER_DOM_TEMPERATURE|Ethernet0']

        updater = PhysicalSensorTableMIBUpdater()
        updater.reinit_data()

        # Verify it used the new table
        self.assertEqual(updater.transceiver_dom, ['TRANSCEIVER_DOM_TEMPERATURE|Ethernet0'])
        # Should only call once (no fallback needed)
        self.assertEqual(mock_dbs_keys.call_count, 1)

    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_get_all')
    @mock.patch('sonic_ax_impl.mibs.ietf.rfc3433.port_util.get_index_from_str')
    def test_update_xcvr_dom_data_temperature_table_fallback(self, mock_get_index, mock_dbs_get_all):
        """
        Given: TRANSCEIVER_DOM_TEMPERATURE table returns empty for an interface
        When: update_xcvr_dom_data is called
        Then: Should fallback to TRANSCEIVER_DOM_SENSOR table for that interface
        """
        mock_get_index.return_value = 1

        # Return transceiver info, then empty for new table, then data for legacy table
        def dbs_get_all_side_effect(statedb, db, key):
            if 'TRANSCEIVER_INFO' in key:
                return {'type': 'QSFP+'}
            elif 'TRANSCEIVER_DOM_TEMPERATURE' in key:
                return {}  # New table empty
            elif 'TRANSCEIVER_DOM_SENSOR' in key:
                return {'temperature': '35.0', 'voltage': '3.3'}
            return {}

        mock_dbs_get_all.side_effect = dbs_get_all_side_effect

        updater = PhysicalSensorTableMIBUpdater()
        updater.transceiver_dom = ['TRANSCEIVER_DOM_SENSOR|Ethernet0']

        updater.update_xcvr_dom_data()

        # Verify dbs_get_all was called for both tables
        calls = [str(call) for call in mock_dbs_get_all.call_args_list]
        self.assertTrue(any('TRANSCEIVER_DOM_TEMPERATURE' in call for call in calls))
        self.assertTrue(any('TRANSCEIVER_DOM_SENSOR' in call for call in calls))
