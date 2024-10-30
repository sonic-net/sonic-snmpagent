import os
import sys

# noinspection PyUnresolvedReferences
import tests.mock_tables.dbconnector

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from unittest import TestCase

from ax_interface import ValueType
from ax_interface.pdu_implementations import GetPDU, GetNextPDU
from ax_interface.encodings import ObjectIdentifier
from ax_interface.constants import PduTypes
from ax_interface.pdu import PDU, PDUHeader
from ax_interface.mib import MIBTable
from sonic_ax_impl.mibs.vendor.cisco import ciscoEntityFruControlFanTrayMIB

class TestFanTrayStatus(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lut = MIBTable(ciscoEntityFruControlFanTrayMIB.cefcFruFanTrayStatusTable)

    def test_getNextFanTray0(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1, 1))
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

    def test_getFanTray0Status(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1, 1))
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

    def test_getNextFanTray1(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1, 1))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1, 2))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 3)

    def test_getFanTray1Status(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1, 2))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 3)

    def test_getNextFanTray2(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1, 2))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1, 3))
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

    def test_getFanTray2Status(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1, 3))
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

    def test_getNextFanTray3(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1, 3))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1, 4))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 3)

    def test_getFanTray3Status(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1, 4))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 3)

    def test_getNextFanTray4(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1, 4))
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

    def test_getMissedFanTray(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1, 8))
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
