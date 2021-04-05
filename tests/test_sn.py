import os
import sys

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
from sonic_ax_impl.mibs.ietf.rfc2737 import PhysicalClass, PSU_SENSOR_NAME_MAP, PSU_SENSOR_POSITION_MAP
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import CHASSIS_SUB_ID, CHASSIS_MGMT_SUB_ID, PSU_SENSOR_PART_ID_MAP
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import get_psu_sensor_sub_id, get_psu_sub_id, get_fan_drawer_sub_id
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import get_fan_sub_id, get_fan_tachometers_sub_id
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import get_chassis_thermal_sub_id, get_transceiver_sub_id
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import get_transceiver_sensor_sub_id
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import SENSOR_TYPE_TEMP
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import SENSOR_TYPE_VOLTAGE
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import SENSOR_TYPE_PORT_RX_POWER
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import SENSOR_TYPE_PORT_TX_POWER
from sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator import SENSOR_TYPE_PORT_TX_BIAS
from sonic_ax_impl.main import SonicMIB

class TestSonicMIB(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lut = MIBTable(SonicMIB)

        # Update MIBs
        for updater in cls.lut.updater_instances:
            updater.reinit_data()

    def test_getnextpdu_chassis_class(self):
        """
        Test chassis physical class
        """
        oid = ObjectIdentifier(12, 0, 0, 0, (1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 5))
        expected_oid = ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 5, 1))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(value0.data, PhysicalClass.CHASSIS)

    def test_getnextpdu_chassis_serial_number(self):
        oid = ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 11))
        expected_oid = ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, 11, 1))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.data), "SAMPLETESTSN")

    def test_getpdu_chassis_mgmt_info(self):
        sub_id = CHASSIS_MGMT_SUB_ID
        expected_mib = {
            2: (ValueType.OCTET_STRING, "MGMT"),
            4: (ValueType.INTEGER, 1),
            5: (ValueType.INTEGER, PhysicalClass.CPU),
            6: (ValueType.INTEGER, 1),
            16: (ValueType.INTEGER, 2)
        }

        self._check_getpdu(sub_id, expected_mib)

    def test_getpdu_psu_info(self):
        sub_id = get_psu_sub_id(2)[0]
        expected_mib = {
            2: (ValueType.OCTET_STRING, "PSU 2"),
            4: (ValueType.INTEGER, 1),
            5: (ValueType.INTEGER, PhysicalClass.POWERSUPPLY),
            6: (ValueType.INTEGER, 2),
            7: (ValueType.OCTET_STRING, "PSU 2"), 
            8: (ValueType.OCTET_STRING, ""),
            9: (ValueType.OCTET_STRING, ""), 
            10: (ValueType.OCTET_STRING, ""), 
            11: (ValueType.OCTET_STRING, "PSU_SERIAL"),
            12: (ValueType.OCTET_STRING, ""),
            13: (ValueType.OCTET_STRING, "PSU_MODEL"),
            16: (ValueType.INTEGER, 1)
        }

        self._check_getpdu(sub_id, expected_mib)

    def test_getpdu_psu_sensor_info(self):
        for sensor_name, oid_offset in PSU_SENSOR_PART_ID_MAP.items():
            self._check_psu_sensor_info(sensor_name, oid_offset)

    def _check_psu_sensor_info(self, sensor_name, oid_offset):
        psu_sub_id = get_psu_sub_id(2)[0]
        sub_id = get_psu_sensor_sub_id((psu_sub_id, ), sensor_name)[0]
        expected_mib = {
            2: (ValueType.OCTET_STRING, "{} for PSU 2".format(PSU_SENSOR_NAME_MAP[sensor_name])),
            4: (ValueType.INTEGER, psu_sub_id),
            5: (ValueType.INTEGER, PhysicalClass.SENSOR),
            6: (ValueType.INTEGER, PSU_SENSOR_POSITION_MAP[sensor_name]),
            7: (ValueType.OCTET_STRING, "{} for PSU 2".format(PSU_SENSOR_NAME_MAP[sensor_name])), 
            16: (ValueType.INTEGER, 2)
        }

        self._check_getpdu(sub_id, expected_mib)

    def test_getpdu_fan_drawer_info(self):
        sub_id = get_fan_drawer_sub_id(1)[0]
        expected_mib = {
            2: (ValueType.OCTET_STRING, "drawer1"),
            4: (ValueType.INTEGER, 1),
            5: (ValueType.INTEGER, PhysicalClass.CONTAINER),
            6: (ValueType.INTEGER, 1),
            7: (ValueType.OCTET_STRING, "drawer1"), 
            8: (ValueType.OCTET_STRING, ""),
            9: (ValueType.OCTET_STRING, ""), 
            10: (ValueType.OCTET_STRING, ""), 
            11: (ValueType.OCTET_STRING, "DRAWERSERIAL"),
            12: (ValueType.OCTET_STRING, ""),
            13: (ValueType.OCTET_STRING, "DRAWERMODEL"),
            16: (ValueType.INTEGER, 1)
        }
        self._check_getpdu(sub_id, expected_mib)

    def test_getpdu_fan_info(self):
        drawer_sub_id = get_fan_drawer_sub_id(1)
        sub_id = get_fan_sub_id(drawer_sub_id, 1)[0]
        expected_mib = {
            2: (ValueType.OCTET_STRING, "fan1"),
            4: (ValueType.INTEGER, drawer_sub_id[0]),
            5: (ValueType.INTEGER, PhysicalClass.FAN),
            6: (ValueType.INTEGER, 1),
            7: (ValueType.OCTET_STRING, "fan1"), 
            8: (ValueType.OCTET_STRING, ""),
            9: (ValueType.OCTET_STRING, ""), 
            10: (ValueType.OCTET_STRING, ""), 
            11: (ValueType.OCTET_STRING, "FANSERIAL"),
            12: (ValueType.OCTET_STRING, ""),
            13: (ValueType.OCTET_STRING, "FANMODEL"),
            16: (ValueType.INTEGER, 1)
        }
        self._check_getpdu(sub_id, expected_mib)

    def test_getpdu_fan_tachometers_info(self):
        drawer_sub_id = get_fan_drawer_sub_id(1)
        fan_sub_id = get_fan_sub_id(drawer_sub_id, 1)
        sub_id = get_fan_tachometers_sub_id(fan_sub_id)[0]
        expected_mib = {
            2: (ValueType.OCTET_STRING, "Tachometers for fan1"),
            4: (ValueType.INTEGER, fan_sub_id[0]),
            5: (ValueType.INTEGER, PhysicalClass.SENSOR),
            6: (ValueType.INTEGER, 1),
            7: (ValueType.OCTET_STRING, "Tachometers for fan1"), 
            16: (ValueType.INTEGER, 2)
        }
        self._check_getpdu(sub_id, expected_mib)

    def test_getpdu_thermal_info(self):
        sub_id = get_chassis_thermal_sub_id(1)[0]
        expected_mib = {
            2: (ValueType.OCTET_STRING, "thermal1"),
            4: (ValueType.INTEGER, CHASSIS_MGMT_SUB_ID),
            5: (ValueType.INTEGER, PhysicalClass.SENSOR),
            6: (ValueType.INTEGER, 1),
            7: (ValueType.OCTET_STRING, "thermal1"), 
            16: (ValueType.INTEGER, 2)
        }
        self._check_getpdu(sub_id, expected_mib)

    def test_getpdu_xcvr_info(self):
        sub_id = get_transceiver_sub_id(1)[0]

        expected_mib = {
            2: (ValueType.OCTET_STRING, "QSFP+ for etp1"),
            4: (ValueType.INTEGER, CHASSIS_SUB_ID),
            5: (ValueType.INTEGER, PhysicalClass.PORT),
            6: (ValueType.INTEGER, -1),
            7: (ValueType.OCTET_STRING, "Ethernet0"), 
            8: (ValueType.OCTET_STRING, "A1"),
            9: (ValueType.OCTET_STRING, ""), # skip
            10: (ValueType.OCTET_STRING, ""), # skip
            11: (ValueType.OCTET_STRING, "SERIAL_NUM"),
            12: (ValueType.OCTET_STRING, "VENDOR_NAME"),
            13: (ValueType.OCTET_STRING, "MODEL_NAME"),
            16: (ValueType.INTEGER, 1)
        }

        self._check_getpdu(sub_id, expected_mib)

    def test_getpdu_xcvr_info_port_disable(self):
        sub_id = get_transceiver_sub_id(2)[0]

        expected_mib = {
            2: (ValueType.OCTET_STRING, "QSFP-DD"),
            4: (ValueType.INTEGER, CHASSIS_SUB_ID),
            5: (ValueType.INTEGER, PhysicalClass.PORT),
            6: (ValueType.INTEGER, -1),
            7: (ValueType.OCTET_STRING, "Ethernet1"),
            8: (ValueType.OCTET_STRING, "A1"),
            9: (ValueType.OCTET_STRING, ""), # skip
            10: (ValueType.OCTET_STRING, ""), # skip
            11: (ValueType.OCTET_STRING, "SERIAL_NUM"),
            12: (ValueType.OCTET_STRING, "VENDOR_NAME"),
            13: (ValueType.OCTET_STRING, "MODEL_NAME"),
            16: (ValueType.INTEGER, 1)
        }

        self._check_getpdu(sub_id, expected_mib)

    def test_getpdu_xcvr_dom(self):
        expected_mib = {
            get_transceiver_sensor_sub_id(1, SENSOR_TYPE_TEMP)[0]: "DOM Temperature Sensor for etp1",
            get_transceiver_sensor_sub_id(1, SENSOR_TYPE_VOLTAGE)[0]: "DOM Voltage Sensor for etp1",
            get_transceiver_sensor_sub_id(1, 1 + SENSOR_TYPE_PORT_RX_POWER)[0]: "DOM RX Power Sensor for etp1/1",
            get_transceiver_sensor_sub_id(1, 2 + SENSOR_TYPE_PORT_RX_POWER)[0]: "DOM RX Power Sensor for etp1/2",
            get_transceiver_sensor_sub_id(1, 3 + SENSOR_TYPE_PORT_RX_POWER)[0]: "DOM RX Power Sensor for etp1/3",
            get_transceiver_sensor_sub_id(1, 4 + SENSOR_TYPE_PORT_RX_POWER)[0]: "DOM RX Power Sensor for etp1/4",
            get_transceiver_sensor_sub_id(1, 1 + SENSOR_TYPE_PORT_TX_BIAS)[0]: "DOM TX Bias Sensor for etp1/1",
            get_transceiver_sensor_sub_id(1, 2 + SENSOR_TYPE_PORT_TX_BIAS)[0]: "DOM TX Bias Sensor for etp1/2",
            get_transceiver_sensor_sub_id(1, 3 + SENSOR_TYPE_PORT_TX_BIAS)[0]: "DOM TX Bias Sensor for etp1/3",
            get_transceiver_sensor_sub_id(1, 4 + SENSOR_TYPE_PORT_TX_BIAS)[0]: "DOM TX Bias Sensor for etp1/4",
            get_transceiver_sensor_sub_id(1, 1 + SENSOR_TYPE_PORT_TX_POWER)[0]: "DOM TX Power Sensor for etp1/1",
            get_transceiver_sensor_sub_id(1, 2 + SENSOR_TYPE_PORT_TX_POWER)[0]: "DOM TX Power Sensor for etp1/2",
            get_transceiver_sensor_sub_id(1, 3 + SENSOR_TYPE_PORT_TX_POWER)[0]: "DOM TX Power Sensor for etp1/3",
            get_transceiver_sensor_sub_id(1, 4 + SENSOR_TYPE_PORT_TX_POWER)[0]: "DOM TX Power Sensor for etp1/4",
        }

        phyDescr, phyClass = 2, 5

        # check physical class value
        oids = [ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, field_id, sub_id))
                for field_id in (phyDescr, phyClass)
                for sub_id in expected_mib]

        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=oids
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        for mib_key, value in zip(expected_mib, response.values):
            if phyClass == value.name.subids[-2]:
                sub_id = (phyClass, mib_key)
                expected_type, expected_value = ValueType.INTEGER, PhysicalClass.SENSOR
            elif phyDescr == value.name.subids[-2]:
                sub_id = (phyDescr, mib_key)
                expected_type, expected_value = ValueType.OCTET_STRING, expected_mib[mib_key]
            else:
                # received unexpected
                self.assertTrue(False)

            expected_oid = ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, *sub_id))
            self.assertEqual(str(value.name), str(expected_oid))
            self.assertEqual(value.type_, expected_type)
            self.assertEqual(str(value.data), str(expected_value))

    def _check_getpdu(self, sub_id, expected_mib):
        oids = [ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, field_sub_id, sub_id))
                for field_sub_id in expected_mib]
        
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=oids
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        for mib_key, value in zip(expected_mib, response.values):
            expected_oid = ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 47, 1, 1, 1, 1, mib_key, sub_id))
            expected_type, expected_value = expected_mib[mib_key]
            self.assertEqual(str(value.name), str(expected_oid))
            self.assertEqual(value.type_, expected_type)
            self.assertEqual(str(value.data), str(expected_value))

