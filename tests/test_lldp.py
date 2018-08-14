import os
import sys

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from unittest import TestCase
import tests.mock_tables.dbconnector

from ax_interface import ValueType
from ax_interface.pdu_implementations import GetPDU, GetNextPDU
from ax_interface.encodings import ObjectIdentifier
from ax_interface.constants import PduTypes
from ax_interface.pdu import PDU, PDUHeader
from ax_interface.mib import MIBTable
from sonic_ax_impl.mibs import ieee802_1ab


class TestLLDPMIB(TestCase):
    @classmethod
    def setUpClass(cls):
        class LLDPMIB(ieee802_1ab.LLDPLocalSystemData,
                      ieee802_1ab.LLDPLocalSystemData.LLDPLocPortTable,
                      ieee802_1ab.LLDPLocalSystemData.LLDPLocManAddrTable,
                      ieee802_1ab.LLDPRemTable,
                      ieee802_1ab.LLDPRemManAddrTable):
            pass

        cls.lut = MIBTable(LLDPMIB)
        for updater in cls.lut.updater_instances:
            updater.update_data()
            updater.reinit_data()
            updater.update_data()

    def test_getnextpdu_eth1(self):
        oid = ObjectIdentifier(12, 0, 1, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 1, 1, 7, 1, 1))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        print("GetNextPDU sr=", get_pdu.sr)
        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        print("test_getnextpdu_exactmatch: ", str(oid))
        self.assertEqual(str(value0.name), str(ObjectIdentifier(11, 0, 1, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 1, 1, 7, 1, 1))))
        self.assertEqual(str(value0.data), "Ethernet1")

    def test_getnextpdu_eth2(self):
        # oid.include = 1
        oid = ObjectIdentifier(12, 0, 1, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 1, 1, 7, 1, 5))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        print("GetNextPDU sr=", get_pdu.sr)
        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        print("test_getnextpdu_exactmatch: ", str(oid))
        self.assertEqual(str(value0.name), str(ObjectIdentifier(11, 0, 1, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 1, 1, 7, 1, 5))))
        self.assertEqual(str(value0.data), "Ethernet2")

    def test_subtype_lldp_rem_table(self):
        for entry in range(2, 13):
            mib_entry = self.lut[(1, 0, 8802, 1, 1, 2, 1, 4, 1, 1, entry)]
            ret = mib_entry(sub_id=(1, 1))
            self.assertIsNotNone(ret)
            print(ret)

    def test_subtype_lldp_loc_port_table(self):
        for entry in range(1, 5):
            mib_entry = self.lut[(1, 0, 8802, 1, 1, 2, 1, 3, 7, 1, entry)]
            ret = mib_entry(sub_id=(1,))
            self.assertIsNotNone(ret)
            print(ret)

    def test_subtype_lldp_loc_sys_data(self):
        for entry in range(1, 5):
            mib_entry = self.lut[(1, 0, 8802, 1, 1, 2, 1, 3, entry)]
            ret = mib_entry(sub_id=(1,))
            self.assertIsNotNone(ret)
            print(ret)

    def test_subtype_lldp_loc_man_addr_table(self):
        for entry in range(1, 7):
            mib_entry = self.lut[(1, 0, 8802, 1, 1, 2, 1, 3, 8, 1, entry)]
            ret = mib_entry(sub_id=(1,))
            self.assertIsNotNone(ret)
            print(ret)

    def test_subtype_lldp_rem_man_addr_table(self):
        for entry in range(1, 6):
            mib_entry = self.lut[(1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, entry)]
            ret = mib_entry(sub_id=(1, 1))
            self.assertIsNotNone(ret)
            print(ret)

    def test_ipv4_rem_man_addr(self):
        # ethernet0 has IPv4 remote management address
        interface_number = 1
        mib_entry = self.lut[(1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, 2)]
        ret = mib_entry(sub_id=(1, interface_number,))
        self.assertEquals(ret, "0A E0 19 64")
        print(ret)
        # test remManAddrSubtype
        mib_entry = self.lut[(1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, 1)]
        ret = mib_entry(sub_id=(1, interface_number,))
        # subtype 1 means IPv4
        self.assertEquals(ret, 1)
        print(ret)

    def test_ipv6_rem_man_addr(self):
        # ethernet4 has IPv6 remote management address
        interface_number = 5
        mib_entry = self.lut[(1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, 2)]
        ret = mib_entry(sub_id=(1, interface_number,))
        self.assertEquals(ret, "fe80 0 268a 7ff fe3f 834c")
        print(ret)
        # test remManAddrSubtype
        mib_entry = self.lut[(1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, 1)]
        ret = mib_entry(sub_id=(1, interface_number,))
        # subtype 2 means IPv6
        self.assertEquals(ret, 2)
        print(ret)

    def test_local_port_identification(self):
        mib_entry = self.lut[(1, 0, 8802, 1, 1, 2, 1, 3, 7, 1, 3)]
        ret = mib_entry(sub_id=(1,))
        self.assertEquals(ret, b'Ethernet0')
        print(ret)

    def test_local_port_num(self):
        mib_entry = self.lut[(1, 0, 8802, 1, 1, 2, 1, 4, 1, 1, 2)]
        for num in range(1, 126, 4):
            ret = mib_entry(sub_id=(1, num,))
            self.assertEqual(ret, num)

    def test_getnextpdu_local_port_identification(self):
        # oid.include = 1
        oid = ObjectIdentifier(11, 0, 1, 0, (1, 0, 8802, 1, 1, 2, 1, 3, 7, 1, 3))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.data), "Ethernet0")

    def test_lab_breaks(self):
        break1 = b'\x01\x06\x10\x00\x00\x00\x00q\x00\x01\xd1\x02\x00\x01\xd1\x03\x00\x00\x00P\t\x00\x01\x00\x00' \
                 b'\x00\x00\x01\x00\x00\x00\x00\x00\x00"b\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x02\x00' \
                 b'\x00\x00\x01\x00\x00\x00\x03\x00\x00\x00\x07\t\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00' \
                 b'\x00"b\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x03\x00' \
                 b'\x00\x00\x08'

        pdu = PDU.decode(break1)
        resp = pdu.make_response(self.lut)
        print(resp)

        break2 = b'\x01\x06\x10\x00\x00\x00\x00\x15\x00\x00\x08\x98\x00\x00\x08\x9a\x00\x00\x00P\t\x00\x01\x00' \
                 b'\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00"b\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x02' \
                 b'\x00\x00\x00\x01\x00\x00\x00\x04\x00\x00\x00\x01\t\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00' \
                 b'\x00\x00\x00"b\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00' \
                 b'\x04\x00\x00\x00\x02'

        pdu = PDU.decode(break2)
        resp = pdu.make_response(self.lut)
        print(resp)

    def test_getnextpdu_noeth(self):
        # oid.include = 1
        oid = ObjectIdentifier(12, 0, 1, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 1, 1, 7, 18545, 126, 1))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        print("GetNextPDU sr=", get_pdu.sr)
        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.END_OF_MIB_VIEW)
