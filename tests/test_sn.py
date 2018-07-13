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
from sonic_ax_impl.mibs.ietf.rfc2737 import PhysicalClass
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

    def test_getpdu_xcvr_info(self):
        sub_id = 1000 * 1 # sub id for Ethernet100

        expected_mib = {
            2: (ValueType.OCTET_STRING, "QSFP+ for Ethernet0"),
            5: (ValueType.INTEGER, PhysicalClass.PORT),
            7: (ValueType.OCTET_STRING, ""), # skip
            8: (ValueType.OCTET_STRING, "A1"),
            9: (ValueType.OCTET_STRING, ""), # skip
            10: (ValueType.OCTET_STRING, ""), # skip
            11: (ValueType.OCTET_STRING, "SERIAL_NUM"),
            12: (ValueType.OCTET_STRING, "VENDOR_NAME"),
            13: (ValueType.OCTET_STRING, "MODEL_NAME")
        }

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

    def test_getpdu_xcvr_dom(self):
        expected_mib = {
            1000 * 1 + 1: "DOM Temperature Sensor for Ethernet0",
            1000 * 1 + 2: "DOM Voltage Sensor for Ethernet0",
            1000 * 1 + 11: "DOM RX Power Sensor for Ethernet0/1",
            1000 * 1 + 21: "DOM RX Power Sensor for Ethernet0/2",
            1000 * 1 + 31: "DOM RX Power Sensor for Ethernet0/3",
            1000 * 1 + 41: "DOM RX Power Sensor for Ethernet0/4",
            1000 * 1 + 12: "DOM TX Bias Sensor for Ethernet0/1",
            1000 * 1 + 22: "DOM TX Bias Sensor for Ethernet0/2",
            1000 * 1 + 32: "DOM TX Bias Sensor for Ethernet0/3",
            1000 * 1 + 42: "DOM TX Bias Sensor for Ethernet0/4",
            1000 * 1 + 13: "DOM TX Power Sensor for Ethernet0/1",
            1000 * 1 + 23: "DOM TX Power Sensor for Ethernet0/2",
            1000 * 1 + 33: "DOM TX Power Sensor for Ethernet0/3",
            1000 * 1 + 43: "DOM TX Power Sensor for Ethernet0/4",
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

