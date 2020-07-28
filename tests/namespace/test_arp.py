import os
import sys
import importlib

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from unittest import TestCase
from unittest.mock import patch, mock_open

# noinspection PyUnresolvedReferences
import tests.mock_tables.dbconnector
import tests.mock_tables.python_arptable
from ax_interface.mib import MIBTable
from ax_interface.pdu import PDUHeader
from ax_interface.pdu_implementations import GetPDU, GetNextPDU
from ax_interface import ValueType
from ax_interface.encodings import ObjectIdentifier
from ax_interface.constants import PduTypes
from sonic_ax_impl.main import SonicMIB
from sonic_ax_impl.mibs.ietf import rfc1213
class TestSonicMIB(TestCase):
    @classmethod
    def setUpClass(cls):
        tests.mock_tables.python_arptable.arp_filename = '/host_arp.txt'
        tests.mock_tables.dbconnector.load_namespace_config()
        importlib.reload(rfc1213)
        cls.lut = MIBTable(rfc1213.IpMib)
        for updater in cls.lut.updater_instances:
            updater.update_data()
            updater.reinit_data()
            updater.update_data()

    def test_getpdu(self):
        oid = ObjectIdentifier(20, 0, 0, 0, (1, 3, 6, 1, 2, 1, 4, 22, 1, 2, 10000, 10, 3, 146, 1))
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
        self.assertEqual(value0.data.string, b'\x00\x00\x5e\x00\x01\x54')

    def test_getnextpdu(self):
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=(
                ObjectIdentifier(20, 0, 0, 0, (1, 3, 6, 1, 2, 1, 4, 22, 1, 2, 10000, 10, 3, 146, 1)),
            )
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        n = len(response.values)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(value0.data.string, b'\xf4\xb5\x2f\x79\xb3\xf0')

    def test_getnextpdu_exactmatch(self):
        # oid.include = 1
        oid = ObjectIdentifier(20, 0, 1, 0, (1, 3, 6, 1, 2, 1, 4, 22, 1, 2, 10000, 10, 3, 146, 1))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        n = len(response.values)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        print("test_getnextpdu_exactmatch: ", str(oid))
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data.string, b'\x00\x00\x5e\x00\x01\x54')

    def test_getnextpdu_exactmatch_asic0(self):
        # oid.include = 1
        oid = ObjectIdentifier(20, 0, 1, 0, (1, 3, 6, 1, 2, 1, 4, 22, 1, 2, 1, 10, 0, 0, 0))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        n = len(response.values)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        print("test_getnextpdu_exactmatch: ", str(oid))
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data.string, b'\x52\x54\x00\xa5\x70\x47')

    def test_getnextpdu_exactmatch_asic1(self):
        # oid.include = 1
        oid = ObjectIdentifier(20, 0, 1, 0, (1, 3, 6, 1, 2, 1, 4, 22, 1, 2, 9, 10, 0, 0, 6))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        n = len(response.values)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        print("test_getnextpdu_exactmatch: ", str(oid))
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data.string, b'\x52\x54\x00\xb4\x59\x59')


    def test_getpdu_noinstance(self):
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=(
                ObjectIdentifier(20, 0, 0, 0, (1, 3, 6, 1, 2, 1, 4, 22, 1, 2, 39)),
            )
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        n = len(response.values)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.NO_SUCH_INSTANCE)

    def test_getpdu_noinstance_eth0_docker0(self):
        oid = ObjectIdentifier(20, 0, 1, 0, (1, 3, 6, 1, 2, 1, 4, 22, 1, 2, 9, 240, 127, 1, 1))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        n = len(response.values)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.NO_SUCH_INSTANCE)

    def test_getnextpdu_empty(self):
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=(
                ObjectIdentifier(20, 0, 0, 0, (1, 3, 6, 1, 2, 1, 4, 22, 1, 3)),
            )
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        n = len(response.values)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.END_OF_MIB_VIEW)

    @classmethod
    def tearDownClass(cls):
        tests.mock_tables.dbconnector.clean_up_config()
