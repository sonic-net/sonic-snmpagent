import os
import sys
from unittest import TestCase

import pytest
from sonic_ax_impl.mibs.ietf.rfc2737 import PhysicalTableMIBUpdater
from sonic_ax_impl.mibs.ietf.rfc2737 import FabricCardCacheUpdater
from sonic_ax_impl.mibs.ietf.rfc2737 import XcvrCacheUpdater

if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))


class TestPhysicalTableMIBUpdater(TestCase):

    # Given: 5 physical updaters are register into reinit of PhysicalTableMIBUpdater
    # When: The first updater(XcvrCacheUpdater) raises exception in the reinit
    # Then: The remaining updaters should execute reinit without any affection,
    #       and the redis un-subscription should be called
    @mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.XcvrCacheUpdater.reinit_data', side_effect=Exception('mocked error'))
    def test_PhysicalTableMIBUpdater_exception_in_reinit_data_wont_block_reinit_iteration_first(self, mocked_xcvr_reinit_data):
        updater = PhysicalTableMIBUpdater()

        with (pytest.raises(Exception) as excinfo,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.PsuCacheUpdater.reinit_data') as mocked_psu_reinit_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.FanDrawerCacheUpdater.reinit_data') as mocked_fan_drawer_reinit_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.FanCacheUpdater.reinit_data') as mocked_fan_cache_reinit_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.ThermalCacheUpdater.reinit_data') as mocked_thermal_reinit_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.FabricCardCacheUpdater.reinit_data') as mocked_fc_reinit_data,
              mock.patch('sonic_ax_impl.mibs.cancel_redis_pubsub') as mocked_cancel_redis_pubsub):
            updater.reinit_data()
            mocked_xcvr_reinit_data.assert_called()
            mocked_psu_reinit_data.assert_called()
            mocked_fan_drawer_reinit_data.assert_called()
            mocked_fan_cache_reinit_data.assert_called()
            mocked_thermal_reinit_data.assert_called()
            mocked_fc_reinit_data.assert_called()
            mocked_cancel_redis_pubsub.assert_called()
        assert str(excinfo.value) == "[Exception('mocked error')]"

    # Given: 5 physical updaters are register into reinit of PhysicalTableMIBUpdater
    # When: The last updater(ThermalCacheUpdater) raises exception in the reinit
    # Then: The remaining updaters should execute reinit without any affection,
    #       and the redis un-subscription should be called
    @mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.ThermalCacheUpdater.reinit_data', side_effect=Exception('mocked error'))
    def test_PhysicalTableMIBUpdater_exception_in_reinit_data_wont_block_reinit_iteration_last(self, mocked_thermal_reinit_data):
        updater = PhysicalTableMIBUpdater()

        with (pytest.raises(Exception) as excinfo,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.XcvrCacheUpdater.reinit_data') as mocked_xcvr_reinit_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.PsuCacheUpdater.reinit_data') as mocked_psu_reinit_data,
              mock.patch(
                  'sonic_ax_impl.mibs.ietf.rfc2737.FanDrawerCacheUpdater.reinit_data') as mocked_fan_drawer_reinit_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.FabricCardCacheUpdater.reinit_data') as mocked_fc_reinit_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.FanCacheUpdater.reinit_data') as mocked_fan_cache_reinit_data,
              mock.patch('sonic_ax_impl.mibs.cancel_redis_pubsub') as mocked_cancel_redis_pubsub):
            updater.reinit_data()
            mocked_xcvr_reinit_data.assert_called()
            mocked_psu_reinit_data.assert_called()
            mocked_fan_drawer_reinit_data.assert_called()
            mocked_fan_cache_reinit_data.assert_called()
            mocked_fc_reinit_data.assert_called()
            mocked_thermal_reinit_data.assert_called()
            mocked_cancel_redis_pubsub.assert_called()
        assert str(excinfo.value) == "[Exception('mocked error')]"

    # Given: 5 physical updaters are register into reinit of PhysicalTableMIBUpdater
    # When: The first updater(XcvrCacheUpdater) raises Runtime exception in the reinit
    # Then: The remaining updaters should execute reinit without any affection,
    #       and the redis un-subscription should be called
    @mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.ThermalCacheUpdater.reinit_data', side_effect=RuntimeError('mocked runtime error'))
    def test_PhysicalTableMIBUpdater_runtime_exc_in_reinit_data_wont_block_reinit_iteration_first(self, mocked_thermal_reinit_data):
        updater = PhysicalTableMIBUpdater()

        with (pytest.raises(RuntimeError) as excinfo,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.XcvrCacheUpdater.reinit_data') as mocked_xcvr_reinit_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.PsuCacheUpdater.reinit_data') as mocked_psu_reinit_data,
              mock.patch(
                  'sonic_ax_impl.mibs.ietf.rfc2737.FanDrawerCacheUpdater.reinit_data') as mocked_fan_drawer_reinit_data,
              mock.patch(
                  'sonic_ax_impl.mibs.ietf.rfc2737.FanCacheUpdater.reinit_data') as mocked_fan_cache_reinit_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.FabricCardCacheUpdater.reinit_data') as mocked_fc_reinit_data,
              mock.patch('sonic_ax_impl.mibs.cancel_redis_pubsub') as mocked_cancel_redis_pubsub):
            updater.reinit_data()
            mocked_thermal_reinit_data.assert_called()
            mocked_xcvr_reinit_data.assert_called()
            mocked_psu_reinit_data.assert_called()
            mocked_fan_drawer_reinit_data.assert_called()
            mocked_fan_cache_reinit_data.assert_called()
            mocked_fc_reinit_data.assert_called()
            mocked_cancel_redis_pubsub.assert_called()
        assert str(excinfo.value) == "[RuntimeError('mocked runtime error')]"

    # Given: 5 physical updaters are register into reinit of PhysicalTableMIBUpdater
    # When: The last updater(XcvrCacheUpdater) raises Runtime exception in the reinit
    # Then: The remaining updaters should execute reinit without any affection,
    #       and the redis un-subscription should be called
    @mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.XcvrCacheUpdater.reinit_data', side_effect=RuntimeError('mocked runtime error'))
    def test_PhysicalTableMIBUpdater_runtime_exc_in_reinit_data_wont_block_reinit_iteration_last(self, mocked_xcvr_reinit_data):
        updater = PhysicalTableMIBUpdater()

        with (pytest.raises(RuntimeError) as exc_info,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.PsuCacheUpdater.reinit_data') as mocked_psu_reinit_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.FanDrawerCacheUpdater.reinit_data') as mocked_fan_drawer_reinit_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.FanCacheUpdater.reinit_data') as mocked_fan_cache_reinit_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.ThermalCacheUpdater.reinit_data') as mocked_thermal_reinit_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.FabricCardCacheUpdater.reinit_data') as mocked_fc_reinit_data,
              mock.patch('sonic_ax_impl.mibs.cancel_redis_pubsub') as mocked_cancel_redis_pubsub):
            updater.reinit_data()
            mocked_xcvr_reinit_data.assert_called()
            mocked_psu_reinit_data.assert_called()
            mocked_fan_drawer_reinit_data.assert_called()
            mocked_fan_cache_reinit_data.assert_called()
            mocked_thermal_reinit_data.assert_called()
            mocked_fc_reinit_data.assert_called()
            mocked_cancel_redis_pubsub.assert_called()
        assert str(exc_info.value) == "[RuntimeError('mocked runtime error')]"

    # Given: 5 physical updaters are register into reinit of PhysicalTableMIBUpdater
    # When: The first(XcvrCacheUpdater) and last updater(ThermalCacheUpdater)
    #       raises Runtime exception and Exception in the reinit
    # Then: The remaining updaters should execute reinit without any affection,
    #       and the redis un-subscription should be called
    #       Both the RuntimeError and Exception should be caught and combined as RuntimeError then been raised
    @mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.XcvrCacheUpdater.reinit_data', side_effect=RuntimeError('mocked runtime error'))
    @mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.ThermalCacheUpdater.reinit_data', side_effect=Exception('mocked error'))
    def test_PhysicalTableMIBUpdater_multi_exception(self, mocked_xcvr_reinit_data, mocked_thermal_reinit_data):
        updater = PhysicalTableMIBUpdater()

        with (pytest.raises(RuntimeError) as exc_info,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.PsuCacheUpdater.reinit_data') as mocked_psu_reinit_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.FanDrawerCacheUpdater.reinit_data') as mocked_fan_drawer_reinit_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.FanCacheUpdater.reinit_data') as mocked_fan_cache_reinit_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.FabricCardCacheUpdater.reinit_data') as mocked_fc_reinit_data,
              mock.patch('sonic_ax_impl.mibs.cancel_redis_pubsub') as mocked_cancel_redis_pubsub):
            updater.reinit_data()
            mocked_xcvr_reinit_data.assert_called()
            mocked_psu_reinit_data.assert_called()
            mocked_fan_drawer_reinit_data.assert_called()
            mocked_fan_cache_reinit_data.assert_called()
            mocked_fc_reinit_data.assert_called()
            mocked_thermal_reinit_data.assert_called()
            mocked_cancel_redis_pubsub.assert_called()
        assert str(exc_info.value) == "[RuntimeError('mocked runtime error'), Exception('mocked error')]"


class TestFabricCardCacheUpdater(TestCase):
    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_get_all', mock.MagicMock(return_value=({"model": "Model000", "presence": "True", "serial" : "Serial000", "is_replaceable" : "False"})))
    @mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.PhysicalEntityCacheUpdater.get_physical_relation_info', mock.MagicMock(return_value=({"position_in_parent" : 0, "parent_name" : "Chassis 1"})))
    def test_update_entity_cache(self):
        updater = PhysicalTableMIBUpdater()
        fc_updater = FabricCardCacheUpdater(updater)
        update_entity_cache = getattr(fc_updater, '_update_entity_cache')

        with (mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.PhysicalTableMIBUpdater.set_phy_contained_in') as mocked_phy_contained_in,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.PhysicalTableMIBUpdater.set_phy_fru') as mocked_set_phy_fru):
            update_entity_cache('N/A')
            mocked_phy_contained_in.assert_called()
            mocked_set_phy_fru.assert_called()


class TestXcvrCacheUpdater(TestCase):
    """Test cases for XcvrCacheUpdater transceiver sensor cache with TRANSCEIVER_DOM_TEMPERATURE fallback"""

    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_get_all')
    @mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.port_util.get_index_from_str')
    def test_update_transceiver_sensor_cache_with_new_temperature_table(self, mock_get_index, mock_dbs_get_all):
        """
        Given: TRANSCEIVER_DOM_TEMPERATURE table exists in STATE_DB with sensor data
        When: _update_transceiver_sensor_cache is called
        Then: Should use TRANSCEIVER_DOM_TEMPERATURE table and skip fallback to TRANSCEIVER_DOM_SENSOR
        """
        mock_get_index.return_value = 1

        # Mock the dbs_get_all to return TRANSCEIVER_DOM_TEMPERATURE data
        mock_dbs_get_all.return_value = {
            'temperature': '35.0',
            'warn_threshold': '50.0',
            'crit_threshold': '60.0'
        }

        updater = PhysicalTableMIBUpdater()
        xcvr_updater = XcvrCacheUpdater(updater)
        xcvr_updater.if_alias_map = {'Ethernet0': 'etp1'}

        # Mock the mib_updater methods to track calls
        with (mock.patch.object(updater, 'add_sub_id'),
              mock.patch.object(updater, 'set_phy_class'),
              mock.patch.object(updater, 'set_phy_descr'),
              mock.patch.object(updater, 'set_phy_name'),
              mock.patch.object(updater, 'set_phy_contained_in'),
              mock.patch.object(updater, 'set_phy_parent_relative_pos'),
              mock.patch.object(updater, 'set_phy_fru'),
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.TransceiverSensorData.create_sensor_data') as mock_create_sensor_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.TransceiverSensorData.sort_sensor_data') as mock_sort_sensor_data):

            # Create mock sensor data
            mock_sensor = mock.MagicMock()
            mock_sensor.get_oid_offset.return_value = 1
            mock_sensor.get_name.return_value = "Temperature"
            mock_sensor.get_lane_number.return_value = 0
            mock_create_sensor_data.return_value = [mock_sensor]
            mock_sort_sensor_data.return_value = [mock_sensor]

            xcvr_updater._update_transceiver_sensor_cache('Ethernet0', 1)

            # Verify that dbs_get_all was called with TRANSCEIVER_DOM_TEMPERATURE table first
            calls = mock_dbs_get_all.call_args_list
            # First call should be for TRANSCEIVER_DOM_TEMPERATURE
            assert any('TRANSCEIVER_DOM_TEMPERATURE' in str(call) for call in calls), \
                "Expected call with TRANSCEIVER_DOM_TEMPERATURE table"

    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_get_all')
    @mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.port_util.get_index_from_str')
    def test_update_transceiver_sensor_cache_fallback_to_legacy(self, mock_get_index, mock_dbs_get_all):
        """
        Given: TRANSCEIVER_DOM_TEMPERATURE table is empty but TRANSCEIVER_DOM_SENSOR table exists
        When: _update_transceiver_sensor_cache is called
        Then: Should fallback to TRANSCEIVER_DOM_SENSOR table for sensor data
        """
        mock_get_index.return_value = 1

        # Mock the dbs_get_all to return empty for TRANSCEIVER_DOM_TEMPERATURE,
        # then return data for TRANSCEIVER_DOM_SENSOR
        mock_dbs_get_all.side_effect = [
            {},  # Empty response for TRANSCEIVER_DOM_TEMPERATURE
            {    # Data for TRANSCEIVER_DOM_SENSOR
                'temperature': '35.0',
                'warn_threshold': '50.0',
                'crit_threshold': '60.0'
            }
        ]

        updater = PhysicalTableMIBUpdater()
        xcvr_updater = XcvrCacheUpdater(updater)
        xcvr_updater.if_alias_map = {'Ethernet0': 'etp1'}

        with (mock.patch.object(updater, 'add_sub_id'),
              mock.patch.object(updater, 'set_phy_class'),
              mock.patch.object(updater, 'set_phy_descr'),
              mock.patch.object(updater, 'set_phy_name'),
              mock.patch.object(updater, 'set_phy_contained_in'),
              mock.patch.object(updater, 'set_phy_parent_relative_pos'),
              mock.patch.object(updater, 'set_phy_fru'),
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.TransceiverSensorData.create_sensor_data') as mock_create_sensor_data,
              mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.TransceiverSensorData.sort_sensor_data') as mock_sort_sensor_data):

            mock_sensor = mock.MagicMock()
            mock_sensor.get_oid_offset.return_value = 1
            mock_sensor.get_name.return_value = "Temperature"
            mock_sensor.get_lane_number.return_value = 0
            mock_create_sensor_data.return_value = [mock_sensor]
            mock_sort_sensor_data.return_value = [mock_sensor]

            xcvr_updater._update_transceiver_sensor_cache('Ethernet0', 1)

            # Verify that dbs_get_all was called twice (once for each table)
            assert mock_dbs_get_all.call_count == 2, \
                "Expected dbs_get_all to be called twice (once for TRANSCEIVER_DOM_TEMPERATURE, once for TRANSCEIVER_DOM_SENSOR)"

    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_get_all')
    @mock.patch('sonic_ax_impl.mibs.ietf.rfc2737.port_util.get_index_from_str')
    def test_update_transceiver_sensor_cache_no_data(self, mock_get_index, mock_dbs_get_all):
        """
        Given: Neither TRANSCEIVER_DOM_TEMPERATURE nor TRANSCEIVER_DOM_SENSOR tables have data
        When: _update_transceiver_sensor_cache is called
        Then: Should return early without setting any sensor data
        """
        mock_get_index.return_value = 1
        mock_dbs_get_all.return_value = {}  # Empty for both tables

        updater = PhysicalTableMIBUpdater()
        xcvr_updater = XcvrCacheUpdater(updater)
        xcvr_updater.if_alias_map = {'Ethernet0': 'etp1'}

        with (mock.patch.object(updater, 'add_sub_id') as mock_add_sub_id,
              mock.patch.object(updater, 'set_phy_class') as mock_set_phy_class):

            xcvr_updater._update_transceiver_sensor_cache('Ethernet0', 1)

            # Verify that no sensor OIDs were added since no data was available
            mock_add_sub_id.assert_not_called()
            mock_set_phy_class.assert_not_called()
