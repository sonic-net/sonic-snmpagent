import os
import sys
import importlib
from unittest import TestCase

from ax_interface import ValueType
from ax_interface.pdu_implementations import GetPDU, GetNextPDU
from ax_interface.encodings import ObjectIdentifier
from ax_interface.constants import PduTypes
from ax_interface.pdu import PDU, PDUHeader
from ax_interface.mib import MIBTable
from sonic_ax_impl.mibs.ietf import rfc1213
import tests.mock_tables.dbconnector

class TestGetNextPDU(TestCase):
    @classmethod
    def setUpClass(cls):
        tests.mock_tables.dbconnector.load_namespace_config()
        importlib.reload(rfc1213)
        cls.lut = MIBTable(rfc1213.SysNameMIB)
        for updater in cls.lut.updater_instances:
            updater.reinit_data()
            updater.update_data()

    def test_getpdu_sysname(self):
        oid = ObjectIdentifier(9, 0, 0, 0, (1, 3, 6, 1, 2, 1, 1, 5, 0))
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
        self.assertEqual(str(value0.name), str(ObjectIdentifier(9, 0, 0, 0, (1, 3, 6, 1, 2, 1, 1, 5, 0))))
        hostname_value = str(value0.data).split(".")[0]
        self.assertEqual(str(hostname_value), 'namespace_hostname')

    @classmethod
    def tearDownClass(cls):
        tests.mock_tables.dbconnector.clean_up_config()
