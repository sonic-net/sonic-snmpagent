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

    def test_getHrStorageAlloc1(self):
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

