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
from sonic_ax_impl.mibs.ietf import rfc4363
from sonic_ax_impl.main import SonicMIB

class Dot1qMIB(
    rfc4363.QBridgeMIBObjects,
    rfc4363.Dot1qFdbMIBObjects,
    rfc4363.Dot1qVlanCurrentMIBObjects,
    rfc4363.Dot1qVlanStaticMIBObjects,
    rfc4363.Dot1qPortVlanMIBObjects,
):
    """
    Class for dot1q mib objects
    """

class TestSonicMIB(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lut = MIBTable(Dot1qMIB)
        for updater in cls.lut.updater_instances:
            updater.update_data()
            updater.reinit_data()
            updater.update_data()


    def getpdu(self, objid, value_type, expected_value):
        #oid = ObjectIdentifier(10, 0, 1, 0, (1, 3, 6, 1, 2, 1, 17, 1, 1,0))
        oid = ObjectIdentifier(len(objid), 0, 0, 0, objid)
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        #self.assertEqual(value0.value_type_, ValueType.OCTET_STRING)
        self.assertEqual(value0.type_, value_type)
        self.assertEqual(str(value0.name), str(oid))
        if expected_value is None:
            return
        if value0.type_ == ValueType.OCTET_STRING:
            self.assertEqual(str(value0.data), expected_value)
        else:
            self.assertEqual(value0.data, expected_value)

    def getnextpdu(self, objid, value_type, expected_value, expected_objid):
        oid = ObjectIdentifier(len(objid), 0, 0, 0, objid)
        expect_oid = ObjectIdentifier(10, 0, 0, 0, expected_objid)
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, value_type)
        self.assertEqual(str(value0.name), str(expect_oid))
        if value0.type_ == ValueType.OCTET_STRING:
            self.assertEqual(str(value0.data), expected_value)
        else:
            self.assertEqual(value0.data, expected_value)

    def test_get_vlan_version(self):
        self.getpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 1, 1, 0),ValueType.INTEGER, 2)

    def test_getnext_vlan_version(self):
        self.getnextpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 1, 1),ValueType.INTEGER, 2, (1, 3, 6, 1, 2, 1, 17, 7, 1, 1,1,0))

    def test_get_max_vlanid(self):
        self.getpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 1, 2, 0),ValueType.INTEGER, 4094)

    def test_getnext_max_vlanid(self):
        self.getnextpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 1, 2),ValueType.INTEGER, 4094, (1, 3, 6, 1, 2, 1, 17, 7, 1, 1,2,0))

    def test_get_max_vlans(self):
        self.getpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 1, 3, 0),ValueType.GAUGE_32, 4094)

    def test_getnext_max_vlans(self):
        self.getnextpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 1, 3),ValueType.GAUGE_32, 4094, (1, 3, 6, 1, 2, 1, 17, 7, 1, 1,3,0))

    def test_get_num_vlans(self):
        self.getpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 1, 4, 0),ValueType.GAUGE_32, 2)

    def test_getnext_num_vlans(self):
        self.getnextpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 1, 4),ValueType.GAUGE_32, 2, (1, 3, 6, 1, 2, 1, 17, 7, 1, 1,4,0))

    def test_get_fdb_status(self):
        self.getpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 2, 2, 1, 3, 1000, 124, 254, 144, 128, 159, 4),ValueType.INTEGER, 3)

    def test_getnext_fdb_status(self):
        self.getnextpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 2, 2, 1,3),ValueType.INTEGER, 3, (1, 3, 6, 1, 2, 1, 17, 7, 1, 2,2,1,3,102, 124, 254, 144, 128, 159, 6))

    def test_get_fdb_dynamic_count(self):
        self.getpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 2, 1, 1, 2, 1000), ValueType.COUNTER_32, 2)

    def test_getnext_fdb_dynamic_count(self):
        self.getnextpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 2, 1, 1,2),ValueType.COUNTER_32, 1, (1, 3, 6, 1, 2, 1, 17, 7, 1, 2,1,1,2,102 ))

    def test_get_vlan_deletes(self):
        self.getpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 1, 0),ValueType.COUNTER_32, 0)

    def test_getnext_vlan_deletes(self):
        self.getnextpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 1),ValueType.COUNTER_32, 0, (1, 3, 6, 1, 2, 1, 17, 7, 1, 4,1,0))

    def test_get_current_egress_ports(self):
        self.getpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 2, 1, 4, 0, 20),ValueType.OCTET_STRING, '00 20 08 00')

    def test_getnext_current_egress_ports(self):
        self.getnextpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 2, 1,4),ValueType.OCTET_STRING, '00 80 00', (1, 3, 6, 1, 2, 1, 17, 7, 1, 4,2,1,4,0,10))

    def test_get_current_untagged_ports(self):
        self.getpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 2, 1, 5, 0, 20),ValueType.OCTET_STRING, '00 00 08 00')

    def test_getnext_current_untagged_ports(self):
        self.getnextpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 2, 1,5),ValueType.OCTET_STRING, '00 80 00' , (1, 3, 6, 1, 2, 1, 17, 7, 1, 4,2,1,5,0,10))

    def test_get_valn_status(self):
        self.getpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 2, 1, 6, 0, 20),ValueType.INTEGER, 2)

    def test_getnext_valn_status(self):
        self.getnextpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 2, 1,6),ValueType.INTEGER, 2, (1, 3, 6, 1, 2, 1, 17, 7, 1, 4,2,1,6,0,10))

    def test_get_valn_name(self):
        self.getpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 3, 1, 1, 20),ValueType.OCTET_STRING, 'Vlan20')

    def test_getnext_valn_name(self):
        self.getnextpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 3, 1,1),ValueType.OCTET_STRING, 'Vlan10', (1, 3, 6, 1, 2, 1, 17, 7, 1, 4,3,1,1,10))

    def test_get_static_egress_ports(self):
        self.getpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 3, 1, 2, 20),ValueType.OCTET_STRING, '00 20 08 00')

    def test_getnext_static_egress_ports(self):
        self.getnextpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 3, 1,2),ValueType.OCTET_STRING, '00 80 00', (1, 3, 6, 1, 2, 1, 17, 7, 1, 4,3,1,2,10))

    def test_get_static_untagged_ports(self):
        self.getpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 3, 1, 4, 20),ValueType.OCTET_STRING, '00 00 08 00')

    def test_getnext_static_untagged_ports(self):
        self.getnextpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 3, 1,4),ValueType.OCTET_STRING, '00 80 00', (1, 3, 6, 1, 2, 1, 17, 7, 1, 4,3,1,4,10))

    def test_get_static_row_status(self):
        self.getpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 3, 1, 5, 20),ValueType.INTEGER, 1)

    def test_getnext_static_row_status(self):
        self.getnextpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 3, 1,5),ValueType.INTEGER, 1, (1, 3, 6, 1, 2, 1, 17, 7, 1, 4,3,1,5,10))

    def test_get_dot1qPvid(self):
        self.getpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 5, 1, 1, 20),ValueType.INTEGER, 20)

    def test_getnext_dot1qPvid(self):
        self.getnextpdu((1, 3, 6, 1, 2, 1, 17, 7, 1, 4, 5, 1,1),ValueType.INTEGER, 10, (1, 3, 6, 1, 2, 1, 17, 7, 1, 4,5,1,1,8))

