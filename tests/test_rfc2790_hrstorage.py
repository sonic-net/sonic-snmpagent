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
from sonic_ax_impl.mibs.ietf import rfc2790 

class TestMountpoints(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lut = MIBTable(rfc2790.hrStorageTable)

    # ====== Testing Used ======
    def test_getNextHrStorageUsed0(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 1))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 0)

    def test_getHrStorageUsed0(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 1))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 0)

    def test_getNextHrStorageUsed1(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 1))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 2))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 10)

    def test_getHrStorageUsed1(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 2))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 10)

    def test_getNextHrStorageUsed2(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 2))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 3))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 100)

    def test_getHrStorageUsed2(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 3))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 100)

    def test_getNextHrStorageUsed3(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 3))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 4))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 1000)

    def test_getHrStorageUsed3(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 4))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 1000)

    def test_getNextHrStorageUsed4(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 4))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 5))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 0)

    def test_getHrStorageUsed4(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 5))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 0)

    def test_getNextHrStorageUsed5(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 5))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 6))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 0)

    def test_getHrStorageUsed5(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 6))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 0)

    def test_getNextHrStorageUsed6(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 6))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 7))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 0)

    def test_getHrStorageUsed6(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 7))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 0)

    def test_getNextHrStorageUsed7(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 7))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 8))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 200)

    def test_getHrStorageUsed7(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 8))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 200)

    def test_getNextHrStorageUsed8(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 8))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 9))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 300)

    def test_getHrStorageUsed8(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 6, 9))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 300)

    # ====== Testing Size ======
    def test_getNextHrStorageSize0(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 1))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 52829740)

    def test_getHrStorageSize0(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 1))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 52829740)
    
    def test_getNextHrStorageSize1(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 1))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 2))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 12345)

    def test_getHrStorageSize1(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 2))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 12345)
 
    def test_getNextHrStorageSize2(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 2))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 3))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 1000)

    def test_getHrStorageSize2(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 3))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 1000)

    def test_getNextHrStorageSize3(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 3))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 4))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 100000)

    def test_getHrStorageSize3(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 4))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 100000)

    def test_getNextHrStorageSize4(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 4))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 5))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 100000)

    def test_getHrStorageSize4(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 5))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 100000)

    def test_getNextHrStorageSize5(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 5))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 6))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 0)

    def test_getHrStorageSize5(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 6))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 0)

    def test_getNextHrStorageSize6(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 6))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 7))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 0)

    def test_getHrStorageSize6(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 7))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 0)

    def test_getNextHrStorageSize7(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 7))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 8))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 200)

    def test_getHrStorageSize7(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 8))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 200)

    def test_getNextHrStorageSize8(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 8))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 9))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 678)

    def test_getHrStorageSize8(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 5, 9))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 678)

    # ====== Testing Description ======
    def test_getNextHrStorageDescr0(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 1))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(expected_oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "/host")

    def test_getHrStorageDescr0(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 1))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "/host")

    def test_getNextHrStorageDescr1(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 1))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 2))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(expected_oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "/host2")

    def test_getHrStorageDescr1(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 2))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "/host2")

    def test_getNextHrStorageDescr2(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 2))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 3))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(expected_oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "/host3")

    def test_getHrStorageDescr2(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 3))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "/host3")

    def test_getNextHrStorageDescr3(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 3))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 4))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(expected_oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "Physical Memory")

    def test_getHrStorageDescr3(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 4))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "Physical Memory")

    def test_getNextHrStorageDescr4(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 4))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 5))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(expected_oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "Virtual Memory")

    def test_getHrStorageDescr4(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 5))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "Virtual Memory")

    def test_getNextHrStorageDescr5(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 5))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 6))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(expected_oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "Swap Memory")

    def test_getHrStorageDescr5(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 6))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "Swap Memory")

    def test_getNextHrStorageDescr6(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 6))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 7))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(expected_oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "Cached Memory")

    def test_getHrStorageDescr6(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 7))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "Cached Memory")

    def test_getNextHrStorageDescr7(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 7))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 8))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(expected_oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "Shared Memory")

    def test_getHrStorageDescr7(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 8))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "Shared Memory")

    def test_getNextHrStorageDescr8(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 8))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 9))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(expected_oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "Buffer Memory")

    def test_getHrStorageDescr8(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 3, 9))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(oid))
        decoded_str = value0.data.string.decode('utf-8')
        self.assertEqual(decoded_str, "Buffer Memory")

    # ====== Testing Allocation ======
    def test_getNextHrStorageAlloc0(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 4))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 4, 1))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 1024)

    def test_getHrStorageAlloc0(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 4, 1))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 1024)   

    def test_getNextHrStorageAlloc1(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 4, 1))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 4, 2))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 1024)

    def test_getHrStorageAlloc1(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 4, 2))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 1024)

    def test_getNextHrStorageAlloc2(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 4, 2))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 4, 3))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 1024)

    def test_getHrStorageAlloc2(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 4, 3))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 1024)

    def test_getNextHrStorageAlloc3(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 4, 3))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 4, 4))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 1024)

    def test_getHrStorageAlloc3(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 4, 4))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 1024)

    def test_getNextHrStorageAlloc4(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 4, 8))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 4, 9))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 1024)

    def test_getHrStorageAlloc4(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 2, 3, 1, 4, 9))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 1024)
