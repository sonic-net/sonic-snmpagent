import os
import sys
import importlib

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from unittest import TestCase

# noinspection PyUnresolvedReferences
import tests.mock_tables.dbconnector

from ax_interface.mib import MIBTable
from ax_interface.pdu import PDUHeader
from ax_interface.pdu_implementations import GetPDU, GetNextPDU
from ax_interface import ValueType
from ax_interface.encodings import ObjectIdentifier
from ax_interface.constants import PduTypes
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import get_transceiver_sub_id, get_transceiver_sensor_sub_id
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import get_psu_sub_id
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import get_psu_sensor_sub_id
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import get_fan_drawer_sub_id
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import get_fan_sub_id
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import get_fan_tachometers_sub_id
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import get_chassis_thermal_sub_id
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import SENSOR_TYPE_TEMP
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import SENSOR_TYPE_VOLTAGE
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import SENSOR_TYPE_PORT_RX_POWER
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import SENSOR_TYPE_PORT_TX_POWER
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import SENSOR_TYPE_PORT_TX_BIAS
from sonic_ax_impl.mibs.ietf import rfc3433
from sonic_ax_impl.main import SonicMIB

class TestSonicMIB(TestCase):
    @classmethod
    def setUpClass(cls):
        tests.mock_tables.dbconnector.load_namespace_config()
        importlib.reload(rfc3433)
        cls.lut = MIBTable(rfc3433.PhysicalSensorTableMIB)
        cls.IFINDEX = 1
        cls.IFINDEX_ASIC1 = 9
        cls.XCVR_SUB_ID = get_transceiver_sub_id(cls.IFINDEX)
        cls.XCVR_SUB_ID_ASIC1 = get_transceiver_sub_id(cls.IFINDEX_ASIC1)
        cls.XCVR_CHANNELS = (1, 2, 3, 4)
        cls.PSU_POSITION = 2
        cls.FAN_DRAWER_POSITION = 1
        cls.FAN_POSITION = 1
        cls.PSU_FAN_POSITION = 1
        cls.THERMAL_POSITION = 1

        # Update MIBs
        for updater in cls.lut.updater_instances:
            updater.reinit_data()
            updater.update_data()

    @staticmethod
    def generate_oids_for_physical_sensor_mib(sub_id):

        return [ObjectIdentifier(12, 0, 0, 0, (1, 3, 6, 1, 2, 1, 99, 1, 1, 1, i, sub_id))
                for i in range(1, 5)]

    def _test_getpdu_sensor(self, sub_id, expected_values):
        """
        Test case for correctness of transceiver sensor MIB values
        :param sub_id: sub OID of the sensor
        :expected values: iterable of expected values TYPE, SCALE, PRECISION, VALUE
        """

        # generate OIDs for TYPE(.1), SCALE(.2), PRECISION(.3), VALUE(.4)
        # for given sub OID
        oids = self.generate_oids_for_physical_sensor_mib(sub_id)

        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=oids
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        for index, value in enumerate(response.values):
            self.assertEqual(str(value.name), str(oids[index]))
            self.assertEqual(value.type_, ValueType.INTEGER)
            self.assertEqual(value.data, expected_values[index])


    def test_getpdu_xcvr_temperature_sensor(self):
        """
        Test case for correctness of transceiver temperature sensor MIB values
        """
        expected_values = [
            rfc3433.EntitySensorDataType.CELSIUS,
            rfc3433.EntitySensorDataScale.UNITS,
            6, # precision
            25390000, # expected sensor value
            rfc3433.EntitySensorStatus.OK
        ]

        self._test_getpdu_sensor(get_transceiver_sensor_sub_id(self.IFINDEX, SENSOR_TYPE_TEMP)[0], expected_values)


    def test_getpdu_xcvr_temperature_sensor_asic1(self):
        """
        Test case for correctness of transceiver temperature sensor MIB values
        """
        print(rfc3433.PhysicalSensorTableMIB.updater.sub_ids)
        expected_values = [
            rfc3433.EntitySensorDataType.CELSIUS,
            rfc3433.EntitySensorDataScale.UNITS,
            6, # precision
            30390000, # expected sensor value
            rfc3433.EntitySensorStatus.OK
        ]

        self._test_getpdu_sensor(get_transceiver_sensor_sub_id(self.IFINDEX_ASIC1, SENSOR_TYPE_TEMP)[0], expected_values)

    def test_getpdu_xcvr_voltage_sensor(self):
        """
        Test case for correctness of transceiver voltage sensor MIB values
        """

        expected_values = [
            rfc3433.EntitySensorDataType.VOLTS_DC,
            rfc3433.EntitySensorDataScale.UNITS,
            4, # precision
            33700, # expected sensor value
            rfc3433.EntitySensorStatus.OK
        ]

        self._test_getpdu_sensor(get_transceiver_sensor_sub_id(self.IFINDEX, SENSOR_TYPE_VOLTAGE)[0], expected_values)


    def test_getpdu_xcvr_voltage_sensor_asic1(self):
        """
        Test case for correctness of transceiver voltage sensor MIB values
        """

        expected_values = [
            rfc3433.EntitySensorDataType.VOLTS_DC,
            rfc3433.EntitySensorDataScale.UNITS,
            4, # precision
            23700, # expected sensor value
            rfc3433.EntitySensorStatus.OK
        ]

        self._test_getpdu_sensor(get_transceiver_sensor_sub_id(self.IFINDEX_ASIC1, SENSOR_TYPE_VOLTAGE)[0], expected_values)

    def test_getpdu_xcvr_rx_power_sensor_minus_infinity(self):
        """
        Test case for correctness of transceiver rx power sensor MIB values
        in case when rx power == -inf
        """

        expected_values = [
            rfc3433.EntitySensorDataType.WATTS,
            rfc3433.EntitySensorDataScale.MILLI,
            4, # precision
            0, # expected sensor value
            rfc3433.EntitySensorStatus.OK
        ]

        self._test_getpdu_sensor(get_transceiver_sensor_sub_id(self.IFINDEX, 1 + SENSOR_TYPE_PORT_RX_POWER)[0], expected_values)

    def test_getpdu_xcvr_rx_power_sensor(self):
        """
        Test case for correctness of transceiver rx power sensor MIB values
        """

        expected_values = [
            rfc3433.EntitySensorDataType.WATTS,
            rfc3433.EntitySensorDataScale.MILLI,
            4, # precision
            7998, # expected sensor value
            rfc3433.EntitySensorStatus.OK
        ]

        # test for each channel except first, we already test above
        for channel in (2, 3, 4):
            self._test_getpdu_sensor(get_transceiver_sensor_sub_id(self.IFINDEX, SENSOR_TYPE_PORT_RX_POWER + channel)[0], expected_values)

    def test_getpdu_xcvr_tx_power_sensor(self):
        """
        Test case for correctness of transceiver rx power sensor MIB values
        """

        expected_values = [
            rfc3433.EntitySensorDataType.WATTS,
            rfc3433.EntitySensorDataScale.MILLI,
            4, # precision
            2884, # expected sensor value
            rfc3433.EntitySensorStatus.OK
        ]

        # test for each channel except first, we already test above
        for channel in (1, 2, 3, 4):
            self._test_getpdu_sensor(get_transceiver_sensor_sub_id(self.IFINDEX, SENSOR_TYPE_PORT_TX_POWER + channel)[0], expected_values)

    def test_getpdu_xcvr_tx_bias_sensor_unknown(self):
        """
        Test case for correctness of transceiver tx bias sensor MIB values, when
        tx bias sensor is set to "UNKNOWN" in state DB
        """

        expected_values = [
            rfc3433.EntitySensorDataType.AMPERES,
            rfc3433.EntitySensorDataScale.MILLI,
            3, # precision
            0, # expected sensor value
            rfc3433.EntitySensorStatus.UNAVAILABLE
        ]

        self._test_getpdu_sensor(get_transceiver_sensor_sub_id(self.IFINDEX, 1 + SENSOR_TYPE_PORT_TX_BIAS)[0], expected_values)

    def test_getpdu_xcvr_tx_bias_sensor_overflow(self):
        """
        Test case for correctness of transceiver tx bias sensor MIB values
        when tx bias is grater than 1E9
        """

        expected_values = [
            rfc3433.EntitySensorDataType.AMPERES,
            rfc3433.EntitySensorDataScale.MILLI,
            3, # precision
            1E9, # expected sensor value
            rfc3433.EntitySensorStatus.OK
        ]

        self._test_getpdu_sensor(get_transceiver_sensor_sub_id(self.IFINDEX, 3 + SENSOR_TYPE_PORT_TX_BIAS)[0], expected_values)

    def test_getpdu_xcvr_tx_bias_sensor(self):
        """
        Test case for correctness of transceiver tx bias sensor MIB values
        """

        expected_values = [
            rfc3433.EntitySensorDataType.AMPERES,
            rfc3433.EntitySensorDataScale.MILLI,
            3, # precision
            4440, # expected sensor value
            rfc3433.EntitySensorStatus.OK
        ]

        # test for each channel
        for channel in (2, 4):
            self._test_getpdu_sensor(get_transceiver_sensor_sub_id(self.IFINDEX, SENSOR_TYPE_PORT_TX_BIAS + channel)[0], expected_values)

    def test_getpdu_psu_temp_sensor(self):
        """
        Test case for correctness of psu temperature sensor MIB values
        """

        expected_values = [
            rfc3433.EntitySensorDataType.CELSIUS,
            rfc3433.EntitySensorDataScale.UNITS,
            3, # precision
            31100, # expected sensor value
            rfc3433.EntitySensorStatus.OK
        ]

        psu_sub_id = get_psu_sub_id(self.PSU_POSITION)
        self._test_getpdu_sensor(get_psu_sensor_sub_id(psu_sub_id, "temperature")[0], expected_values)

    def test_getpdu_psu_voltage_sensor(self):
        """
        Test case for correctness of psu voltage sensor MIB values
        """

        expected_values = [
            rfc3433.EntitySensorDataType.VOLTS_DC,
            rfc3433.EntitySensorDataScale.UNITS,
            3, # precision
            13100, # expected sensor value
            rfc3433.EntitySensorStatus.OK
        ]

        psu_sub_id = get_psu_sub_id(self.PSU_POSITION)
        self._test_getpdu_sensor(get_psu_sensor_sub_id(psu_sub_id, "voltage")[0], expected_values)

    def test_getpdu_psu_power_sensor(self):
        """
        Test case for correctness of psu voltage sensor MIB values
        """

        expected_values = [
            rfc3433.EntitySensorDataType.WATTS,
            rfc3433.EntitySensorDataScale.UNITS,
            3, # precision
            312600, # expected sensor value
            rfc3433.EntitySensorStatus.OK
        ]

        psu_sub_id = get_psu_sub_id(self.PSU_POSITION)
        self._test_getpdu_sensor(get_psu_sensor_sub_id(psu_sub_id, "power")[0], expected_values)

    def test_getpdu_psu_current_sensor(self):
        """
        Test case for correctness of psu current sensor MIB values
        """

        expected_values = [
            rfc3433.EntitySensorDataType.AMPERES,
            rfc3433.EntitySensorDataScale.UNITS,
            3, # precision
            13400, # expected sensor value
            rfc3433.EntitySensorStatus.OK
        ]

        psu_sub_id = get_psu_sub_id(self.PSU_POSITION)
        self._test_getpdu_sensor(get_psu_sensor_sub_id(psu_sub_id, "current")[0], expected_values)

    def test_getpdu_chassis_fan_speed_sensor(self):
        """
        Test case for correctness of fan speed sensor MIB values
        """

        expected_values = [
            rfc3433.EntitySensorDataType.UNKNOWN,
            rfc3433.EntitySensorDataScale.UNITS,
            0, # precision
            50, # expected sensor value
            rfc3433.EntitySensorStatus.OK
        ]

        fan_parent_sub_id = get_fan_drawer_sub_id(self.FAN_DRAWER_POSITION)
        fan_sub_id = get_fan_sub_id(fan_parent_sub_id, self.FAN_POSITION)

        self._test_getpdu_sensor(get_fan_tachometers_sub_id(fan_sub_id)[0], expected_values)

    def test_getpdu_psu_fan_speed_sensor(self):
        """
        Test case for correctness of psu fan speed sensor MIB values
        """

        expected_values = [
            rfc3433.EntitySensorDataType.UNKNOWN,
            rfc3433.EntitySensorDataScale.UNITS,
            0, # precision
            57, # expected sensor value
            rfc3433.EntitySensorStatus.OK
        ]

        psu_sub_id = get_psu_sub_id(self.PSU_POSITION)
        fan_sub_id = get_fan_sub_id(psu_sub_id, self.PSU_FAN_POSITION)

        self._test_getpdu_sensor(get_fan_tachometers_sub_id(fan_sub_id)[0], expected_values)

    def test_getpdu_chassis_temp_sensor(self):
        """
        Test case for correctness of chassis temp sensors MIB values
        """

        expected_values = [
            rfc3433.EntitySensorDataType.CELSIUS,
            rfc3433.EntitySensorDataScale.UNITS,
            3, # precision
            20500, # expected sensor value
            rfc3433.EntitySensorStatus.OK
        ]

        self._test_getpdu_sensor(get_chassis_thermal_sub_id(self.THERMAL_POSITION)[0], expected_values)
