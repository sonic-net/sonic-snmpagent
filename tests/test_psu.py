import os
import sys

# noinspection PyUnresolvedReferences
import tests.mock_tables.dbconnector

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from unittest import TestCase

if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

from ax_interface import ValueType
from ax_interface.pdu_implementations import GetPDU, GetNextPDU
from ax_interface.encodings import ObjectIdentifier
from ax_interface.constants import PduTypes
from ax_interface.pdu import PDU, PDUHeader
from ax_interface.mib import MIBTable
from sonic_ax_impl.mibs.vendor.cisco import ciscoEntityFruControlMIB

class TestPsuStatus(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lut = MIBTable(ciscoEntityFruControlMIB.cefcFruPowerStatusTable)

    def test_getNextPsu0(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2, 1))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 8)

    def test_getPsu1Status(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2, 1))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 8)

    def test_getNextPsu1(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2, 1))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2, 2))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 2)

    def test_getPsu2Status(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2, 2))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 2)

    def test_getNextPsu3(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2, 3))
        expected_oid = None
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.END_OF_MIB_VIEW)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, None)

    def test_getMissedPsu(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2, 5, 1))
        expected_oid = None
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.END_OF_MIB_VIEW)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, None)

    @mock.patch('sonic_ax_impl.mibs.vendor.cisco.ciscoEntityFruControlMIB.is_chassis', mock.MagicMock(return_value=True))
    @mock.patch('sonic_ax_impl.mibs.vendor.cisco.ciscoEntityFruControlMIB.is_supervisor', mock.MagicMock(return_value=False))
    @mock.patch('sonic_ax_impl.mibs.vendor.cisco.ciscoEntityFruControlMIB.get_chassis_data', mock.MagicMock(return_value=(('',))))
    def test_getNoPsuChassisLineCard(self):
        # is_chassis is True and is_supervisor is False
        # Expect no PSU in Linecard of Chassis
        # Fail if Exception is caught, no exception should be caught for Linecard with no PSU
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2, 1))
        expected_oid = None
        try:
            ciscoEntityFruControlMIB.cefcFruPowerStatusTable.power_status_handler._get_num_psus()
        except Exception as e:
            self.fail(f"Caught unexpected exception: {type(e).__name__}: {str(e)}")


    @mock.patch('sonic_ax_impl.mibs.vendor.cisco.ciscoEntityFruControlMIB.is_chassis', mock.MagicMock(return_value=True))
    @mock.patch('sonic_ax_impl.mibs.vendor.cisco.ciscoEntityFruControlMIB.is_supervisor', mock.MagicMock(return_value=True))
    @mock.patch('sonic_ax_impl.mibs.vendor.cisco.ciscoEntityFruControlMIB.get_chassis_data', mock.MagicMock(return_value=(('',))))
    def test_getNoPsuChassisSupervisor(self):
        # is_chassis is True and is_supervisor is True
        # get_chassis_data() should return num_psu
        # Exception will be caught on supervisory if num_psu is empty
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2, 1))
        expected_oid = None

        with self.assertRaises(Exception):
            ciscoEntityFruControlMIB.cefcFruPowerStatusTable.power_status_handler._get_num_psus()

    @mock.patch('sonic_ax_impl.mibs.vendor.cisco.ciscoEntityFruControlMIB.is_chassis', mock.MagicMock(return_value=True))
    @mock.patch('sonic_ax_impl.mibs.vendor.cisco.ciscoEntityFruControlMIB.is_supervisor', mock.MagicMock(return_value=True))
    @mock.patch('sonic_ax_impl.mibs.vendor.cisco.ciscoEntityFruControlMIB.get_chassis_data', mock.MagicMock(return_value=(('8',))))
    def test_getPsuPresentChassisSupervisor(self):
        # is_chassis is True and is_supervisor is True
        # get_chassis_data() should return num_psu
        # no exception should be caught and number of psus should be returned
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2, 1))
        expected_oid = None
        try:
            num_psus = ciscoEntityFruControlMIB.cefcFruPowerStatusTable.power_status_handler._get_num_psus()
            self.assertEqual(num_psus, 8)
        except Exception as e:
            self.fail(f"Caught unexpected exception: {type(e).__name__}: {str(e)}")
