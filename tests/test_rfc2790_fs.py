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

class TestMountpoints_fs(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lut = MIBTable(rfc2790.hrFSTable)

    # ======= Filesystem Type ======= 
    def test_getNextFSType0(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 4))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 4, 1))
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
        self.assertEqual(decoded_str, "ext4")

    def test_getFSType0(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 4, 1))
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
        self.assertEqual(decoded_str, "ext4")

    def test_getNextFSType1(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 4, 1))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 4, 2))
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
        self.assertEqual(decoded_str, "ext3")

    def test_getFSType1(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 4, 2))
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
        self.assertEqual(decoded_str, "ext3")

    def test_getNextFSType2(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 4, 2))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 4, 3))
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
        self.assertEqual(decoded_str, "nfs")

    def test_getFSType2(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 4, 3))
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
        self.assertEqual(decoded_str, "nfs")

    # ======= Filesystem Mount ======= 
    def test_getNextMountFS0(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 2))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 2, 1))
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
        self.assertEqual(decoded_str, "/dev")

    def test_getMountFS0(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 2, 1))
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
        self.assertEqual(decoded_str, "/dev")

    def test_getNextMountFS1(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 2, 1))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 2, 2))
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
        self.assertEqual(decoded_str, "/dev2")

    def test_getMountFS1(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 2, 2))
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
        self.assertEqual(decoded_str, "/dev2")

    def test_getNextMountFS2(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 2, 2))
        expected_oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 2, 3))
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
        self.assertEqual(decoded_str, "/dev3")

    def test_getMountFS2(self):
        oid = ObjectIdentifier(2, 0, 0, 0, (1, 3, 6, 1, 2, 1, 25, 3, 8, 1, 2, 3))
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
        self.assertEqual(decoded_str, "/dev3")
