import os
import sys
import importlib

# noinspection PyUnresolvedReferences
import tests.mock_tables.dbconnector

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from unittest import TestCase
from unittest.mock import patch, mock_open

from ax_interface import ValueType
from ax_interface.pdu import PDU
from ax_interface.mib import MIBTable
from ax_interface.pdu_implementations import GetPDU, GetNextPDU
from ax_interface.encodings import ObjectIdentifier
from ax_interface.constants import PduTypes
from ax_interface.pdu import PDU, PDUHeader
from sonic_ax_impl.mibs.ietf import rfc2863


class TestGetNextPDU(TestCase):
    @classmethod
    def setUpClass(cls):
        tests.mock_tables.dbconnector.load_database_config()
        importlib.reload(rfc2863)
        cls.lut = MIBTable(rfc2863.InterfaceMIBObjects)
        for updater in cls.lut.updater_instances:
            updater.update_data()
            updater.reinit_data()
            updater.update_data()

    def test_getnextpdu_firstifalias(self):
        oid = ObjectIdentifier(10, 0, 1, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 18))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(11, 0, 1, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 18, 1))))
        self.assertEqual(str(value0.data), 'snowflake')

    def test_get_next_alias(self):
        if_alias = b'\x01\x06\x10\x00\x00\x00\x00o\x00\x01\xcc4\x00\x01\xcc5\x00\x00\x000\x07\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x11\x00\x00\x00}\x03\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x02'
        pdu = PDU.decode(if_alias)
        resp = pdu.make_response(self.lut)
        print(resp)

    def test_get_next1(self):
        payload = b'\x01\x06\x10\x00\x00\x00\x00\x17\x00\x00\x01R\x00\x00\x01S\x00\x00\x00,\x06\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x03\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x02'
        pdu = PDU.decode(payload)
        resp = pdu.make_response(self.lut)
        print(resp)

    def test_get_next2(self):
        payload = b'\x01\x06\x10\x00\x00\x00\x00\x17\x00\x00\x01V\x00\x00\x01W\x00\x00\x00,\x06\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x03\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x02\x01\x06\x10\x00\x00\x00\x00\x17\x00\x00\x01\\\x00\x00\x01]\x00\x00\x00,\x06\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x03\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x02\x01\x06\x10\x00\x00\x00\x00\x17\x00\x00\x01b\x00\x00\x01c\x00\x00\x00,\x06\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x03\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x02\x01\x06\x10\x00\x00\x00\x00\x17\x00\x00\x01h\x00\x00\x01i\x00\x00\x00,\x06\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x03\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x02'
        pdu = PDU.decode(payload)
        resp = pdu.make_response(self.lut)
        print(resp)

    def test_get_next3(self):
        payload = b'\x01\x06\x10\x00\x00\x00\x00\x17\x00\x00\x01V\x00\x00\x01W\x00\x00\x00,\x06\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x03\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x02\x01\x06\x10\x00\x00\x00\x00\x17\x00\x00\x01\\\x00\x00\x01]\x00\x00\x00,\x06\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x03\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x02\x01\x06\x10\x00\x00\x00\x00\x17\x00\x00\x01b\x00\x00\x01c\x00\x00\x00,\x06\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x03\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x02\x01\x06\x10\x00\x00\x00\x00\x17\x00\x00\x01h\x00\x00\x01i\x00\x00\x00,\x06\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x03\x02\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1f\x00\x00\x00\x02'
        pdu = PDU.decode(payload)
        resp = pdu.make_response(self.lut)
        print(resp)

    def test_no_description(self):
        """
        For a port with no description in the db the result should be ian empty string
        """
        oid = ObjectIdentifier(12, 0, 0, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 18, 113))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 18, 117))))
        self.assertEqual(str(value0.data), '')

    def test_low_speed(self):
        """
        For an interface with a speed inside the 32 bit counter returns the speed of the interface in Mbps
        """
        oid = ObjectIdentifier(12, 0, 0, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 15, 113))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.GAUGE_32)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 15, 117))))
        self.assertEqual(value0.data, 1000)

    def test_high_speed(self):
        """
        should return the speed of the interface
        """
        oid = ObjectIdentifier(12, 0, 0, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 15, 1))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.GAUGE_32)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 15, 5))))
        self.assertEqual(value0.data, 100000)

    def test_no_speed(self):
        """
        For a port with no speed in the db the result should be 40000
        """
        oid = ObjectIdentifier(12, 0, 0, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 15, 117))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.GAUGE_32)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 15, 121))))
        self.assertEqual(value0.data, 40000)

    def test_portchannel_speed(self):
        """
        For a portchannel, the speed should be the sum of all members' speeds
        """
        oid = ObjectIdentifier(12, 0, 0, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 15, 1000))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.GAUGE_32)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 15, 1001))))
        self.assertEqual(value0.data, 200000)

    def test_no_description(self):
        """
        For a port with no speed in the db the result should be 40000
        """
        oid = ObjectIdentifier(12, 0, 0, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 18, 113))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        n = len(response.values)
        # self.assertEqual(n, 7)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 18, 117))))
        self.assertEqual(str(value0.data), '')

    def test_mgmt_iface_name(self):
        """
        Test that mgmt port is present in the MIB
        """
        oid = ObjectIdentifier(11, 0, 0, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 1, 10000))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(11, 0, 1, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 1, 10000))))
        self.assertEqual(str(value0.data), 'eth0')

    def test_mgmt_iface_alias(self):
        """
        Test that mgmt port alias
        """
        oid = ObjectIdentifier(11, 0, 0, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 1, 10001))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(11, 0, 1, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 1, 10001))))
        self.assertEqual(str(value0.data), 'mgmt1')

    @patch("builtins.open", new_callable=mock_open, read_data="1000\n")
    def test_mgmt_iface_speed(self, mock_file):
        """
        Test that mgmt port speed is 1000
        """
        oid = ObjectIdentifier(11, 0, 0, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 15, 10000))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.GAUGE_32)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(11, 0, 1, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 15, 10000))))
        self.assertEqual(value0.data, 1000)

    def test_in_octets(self):
        """
        For a port with no speed in the db the result should be 0
        """
        oid = ObjectIdentifier(12, 0, 0, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 6, 1))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.COUNTER_64)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 6, 1))))
        self.assertEqual(value0.data, 4321)

    def test_in_octets_override(self):
        """
        For a port with no speed in the db the result should be 0
        """
        oid = ObjectIdentifier(12, 0, 0, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 6, 5))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.COUNTER_64)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(12, 0, 1, 0, (1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 6, 5))))
        self.assertEqual(value0.data, 654321)
