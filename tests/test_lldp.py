import os
import sys

# noinspection PyUnresolvedReferences
import tests.mock_tables.dbconnector
from tests.mock_tables.dbconnector import SonicV2Connector

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from unittest import TestCase

from ax_interface import ValueType
from ax_interface.pdu_implementations import GetPDU, GetNextPDU
from ax_interface.encodings import ObjectIdentifier
from ax_interface.constants import PduTypes
from ax_interface.pdu import PDU, PDUHeader
from ax_interface.mib import MIBTable
from sonic_ax_impl.mibs import ieee802_1ab
from mock import patch

def mock_poll_lldp_notif(mock_lldp_polled_entries):
    if not mock_lldp_polled_entries:
        return None, None, None
    return mock_lldp_polled_entries.pop(0)

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
        for entry in range(4, 13):
            mib_entry = self.lut[(1, 0, 8802, 1, 1, 2, 1, 4, 1, 1, entry)]
            ret = mib_entry(sub_id=(1, 1))
            self.assertIsNotNone(ret)
            print(ret)

    def test_subtype_lldp_loc_port_table(self):
        for entry in range(2, 5):
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
        oid = ObjectIdentifier(13, 0, 1, 0, (1, 0, 8802, 1, 1, 2, 1, 3, 8, 1, 3, 1, 4))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        response = get_pdu.make_response(self.lut)
        value0 = response.values[0]
        self.assertEqual(str(value0.name), str(ObjectIdentifier(13, 0, 1, 0, (1, 0, 8802, 1, 1, 2, 1, 3, 8, 1, 3, 1, 4, 10, 224, 25, 26))))
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(value0.data, 5)


    def test_subtype_lldp_rem_man_addr_table(self):
        # Get the first entry of walk. We will get IPv4 Address associated with Ethernet92 Port
        # Verfiy both valid ipv4 and ipv6 address exist
        for entry in range(3, 6):
            oid = ObjectIdentifier(11, 0, 0, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, entry))
            get_pdu = GetNextPDU(
                header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
                oids=[oid]
            )
            response = get_pdu.make_response(self.lut)
            value0 = response.values[0]
            self.assertEqual(str(value0.name), str(ObjectIdentifier(20, 0, 0, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, entry, 32, 93, 1, 1, 4, 10, 224, 25, 123))))
            if entry == 3:
                self.assertEqual(value0.type_, ValueType.INTEGER)
                self.assertEqual(value0.data, 2)
            elif entry == 4:
                self.assertEqual(value0.type_, ValueType.INTEGER)
                self.assertEqual(value0.data, 0)
            else:
                self.assertEqual(value0.type_, ValueType.OBJECT_IDENTIFIER)
                self.assertEqual(str(value0.data), str(ObjectIdentifier(5, 2, 0, 0, (1, 2, 2, 1, 1))))

            # Get next on above to get IPv6 Entry. We will get IPv6 Address associated with Ethernet92 Port
            oid = ObjectIdentifier(16, 0, 0, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, entry, 32, 93, 1, 1, 16))
            get_pdu = GetNextPDU(
                header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
                oids=[oid]
            )
            response = get_pdu.make_response(self.lut)
            value0 = response.values[0]
            self.assertEqual(str(value0.name), str(ObjectIdentifier(20, 0, 1, 0, 
                                                   (1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, entry, 32, 93, 1, 2, 16, 38, 3, 16, 226, 2, 144, 80, 22, 0, 0, 0, 0, 0, 0, 0, 0))))
            if entry == 3:
                self.assertEqual(value0.type_, ValueType.INTEGER)
                self.assertEqual(value0.data, 2)
            elif entry == 4:
                self.assertEqual(value0.type_, ValueType.INTEGER)
                self.assertEqual(value0.data, 0)
            else:
                self.assertEqual(value0.type_, ValueType.OBJECT_IDENTIFIER)
                self.assertEqual(str(value0.data), str(ObjectIdentifier(5, 2, 0, 0, (1, 2, 2, 1, 1))))

        # Verfiy both valid ipv4 and invalid ipv6 address exist. Ethernet5 has this config.
        oid = ObjectIdentifier(20, 0, 0, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, 3, 18543, 5, 1, 1, 4, 10, 224, 25, 101))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )
        response = get_pdu.make_response(self.lut)
        value0 = response.values[0]
        self.assertEqual(str(value0.name), str(ObjectIdentifier(20, 0, 0, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, 3, 18543, 5, 1, 1, 4, 10, 224, 25, 101))))
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(value0.data, 2)

        # Verfiy only valid ipv4 address exist. Ethernet8 has this config.
        oid = ObjectIdentifier(20, 0, 0, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, 3, 18543, 9, 1, 1, 4, 10, 224, 25, 102))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )
        response = get_pdu.make_response(self.lut)
        value0 = response.values[0]
        self.assertEqual(str(value0.name), str(ObjectIdentifier(20, 0, 0, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, 3, 18543, 9, 1, 1, 4, 10, 224, 25, 102))))
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(value0.data, 2)

        # Verfiy only valid ipv6 address exist. Ethernet12 has this config.
        oid = ObjectIdentifier(20, 0, 0, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, 3, 18545, 13, 1, 2, 16, 254, 128, 38, 138, 0, 0, 0, 0, 0, 0, 7, 255, 254, 63, 131, 76))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )
        response = get_pdu.make_response(self.lut)
        value0 = response.values[0]
        self.assertEqual(str(value0.name), str(ObjectIdentifier(20, 0, 0, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, 3, 18545,  
                                               13, 1, 2, 16, 254, 128, 38, 138, 0, 0, 0, 0, 0, 0, 7, 255, 254, 63, 131, 76))))
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(value0.data, 2)

        # Verfiy no mgmt address exist. Ethernet16 has this config.
        oid = ObjectIdentifier(11, 0, 0, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, 3, 18545, 17))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )
        response = get_pdu.make_response(self.lut)
        value0 = response.values[0]
        # Should move to other interface. Ethernet22
        self.assertEqual(str(value0.name), str(ObjectIdentifier(20, 0, 0, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 2, 1, 3, 18545, 21, 1, 1, 4, 10, 224, 25, 105))))
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(value0.data, 2)

    def test_local_port_identification(self):
        mib_entry = self.lut[(1, 0, 8802, 1, 1, 2, 1, 3, 7, 1, 3)]
        ret = mib_entry(sub_id=(1,))
        self.assertEquals(ret, 'etp1')
        print(ret)

    def test_mgmt_local_port_identification(self):
        mib_entry = self.lut[(1, 0, 8802, 1, 1, 2, 1, 3, 7, 1, 3)]
        ret = mib_entry(sub_id=(10001,))
        self.assertEquals(ret, 'mgmt1')
        print(ret)

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
        self.assertEqual(str(value0.data), "etp1")

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

    def test_getnextpdu_lldpLocSysCapSupported(self):
        oid = ObjectIdentifier(9, 0, 1, 0, (1, 0, 8802, 1, 1, 2, 1, 3, 5))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(9, 0, 1, 0, (1, 0, 8802, 1, 1, 2, 1, 3, 5))))
        self.assertEqual(str(value0.data), "\x28\x00")

    def test_getnextpdu_lldpLocSysCapEnabled(self):
        oid = ObjectIdentifier(9, 0, 1, 0, (1, 0, 8802, 1, 1, 2, 1, 3, 6))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(9, 0, 1, 0, (1, 0, 8802, 1, 1, 2, 1, 3, 6))))
        self.assertEqual(str(value0.data), "\x28\x00")

    def test_getnextpdu_lldpRemSysCapSupported(self):
        oid = ObjectIdentifier(12, 0, 1, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 1, 1, 11, 1, 1))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(12, 0, 1, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 1, 1, 11, 1, 1))))
        self.assertEqual(str(value0.data), "\x28\x00")

    def test_getnextpdu_lldpRemSysCapEnabled(self):
        oid = ObjectIdentifier(12, 0, 1, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 1, 1, 12, 1, 1))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(12, 0, 1, 0, (1, 0, 8802, 1, 1, 2, 1, 4, 1, 1, 12, 1, 1))))
        self.assertEqual(str(value0.data), "\x28\x00")
    
    @patch("sonic_ax_impl.mibs.ieee802_1ab.poll_lldp_entry_updates", mock_poll_lldp_notif)
    def test_get_latest_notification(self):
        mock_lldp_polled_entries = []
        mock_lldp_polled_entries.extend([("hset", "Ethernet0", "123"),
                                        ("hset", "Ethernet4", "124"),
                                        ("del", "Ethernet4", "124"),
                                        ("del", "Ethernet8", "125"),
                                        ("hset", "Ethernet8", "125"),
                                        ("hset", "Ethernet4", "124"),
                                        ("del", "Ethernet0", "123"),
                                        ("hset", "Ethernet12", "126"),
                                        ("del", "Ethernet12", "126"),
                                        ("hset", "Ethernet0", "123"),
                                        ("del", "Ethernet16", "127")])
        event_cache = ieee802_1ab.get_latest_notification(mock_lldp_polled_entries)
        expect = {"Ethernet0" : ("hset", "123"),
                  "Ethernet4" : ("hset", "124"),
                  "Ethernet8" : ("hset", "125"),
                  "Ethernet12" : ("del", "126"),
                  "Ethernet16" : ("del", "127")}
        for key in expect.keys():
            assert key in event_cache
            self.assertEqual(expect[key], event_cache[key])     
