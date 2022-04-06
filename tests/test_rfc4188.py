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
from sonic_ax_impl.mibs.ietf import rfc4188
from sonic_ax_impl.main import SonicMIB

class TestSonicMIB(TestCase):
    @classmethod
    def setUpClass(cls):
        #cls.lut = MIBTable(SonicMIB)
        cls.lut = MIBTable(rfc4188.Dot1dBaseMIB)
        for updater in cls.lut.updater_instances:
            updater.update_data()
            updater.reinit_data()
            updater.update_data()


    def test_getbridge_addr(self):
        oid = ObjectIdentifier(10, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 1, 1,0))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(str(value0.data), '1a:2b:3c:4d:5e:6f')

    def test_getnextbridge_addr(self):
        oid = ObjectIdentifier(9, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 1, 1))
        expect_oid = ObjectIdentifier(10, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 1, 1,0))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(expect_oid))
        self.assertEqual(str(value0.data), '1a:2b:3c:4d:5e:6f')

    def test_getNumPorts(self):
        oid = ObjectIdentifier(10, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 1, 2,0))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 3)

    def test_getnextNumPorts(self):
        oid = ObjectIdentifier(9, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 1, 2))
        expect_oid = ObjectIdentifier(10, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 1, 2,0))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expect_oid))
        self.assertEqual(value0.data, 3)

    def test_getBaseType(self):
        oid = ObjectIdentifier(10, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 1, 3,0))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 2)

    def test_getnextBaseType(self):
        oid = ObjectIdentifier(9, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 1, 3))
        expect_oid = ObjectIdentifier(10, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 1, 3,0))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expect_oid))
        self.assertEqual(value0.data, 2)

    def test_getAgingTime(self):
        oid = ObjectIdentifier(10, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 4, 2,0))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 300)

    def test_getnextAgingTime(self):
        oid = ObjectIdentifier(9, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 4, 2))
        expect_oid = ObjectIdentifier(10, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 4, 2,0))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expect_oid))
        self.assertEqual(value0.data, 300)

    def test_getBasePort(self):
        oid = ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 1, 4, 1, 1, 8))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 8)

    def test_getnextBasePort(self):
        oid = ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 1, 4, 1, 1))
        expect_oid = ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 1, 4, 1, 1, 8))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expect_oid))
        self.assertEqual(value0.data, 8)

    def test_getBasePortIfIndex(self):
        oid = ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 1, 4, 1, 2, 8))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 9)

    def test_getnextBasePortIfIndex(self):
        oid = ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 1, 4, 1, 2))
        expect_oid = ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 1, 4, 1, 2, 8))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(str(value0.name), str(expect_oid))
        self.assertEqual(value0.data, 9)
