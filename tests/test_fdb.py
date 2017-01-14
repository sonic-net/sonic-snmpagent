import os
import sys

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from unittest import TestCase

# noinspection PyUnresolvedReferences
import tests.mock_tables.dbconnector

from ax_interface.mib import MIBTable
from ax_interface.pdu import PDU, PDUHeader, PDUHeaderTags, supported_pdus, ContextOptionalPDU, _ignored_pdus, PDUStream
from ax_interface.pdu_implementations import OpenPDU, ResponsePDU, RegisterPDU, GetPDU
from ax_interface import exceptions, ValueType
from ax_interface.encodings import ObjectIdentifier
from ax_interface.constants import PduTypes
from sonic_ax_impl.mibs import ieee802_1ab
from sonic_ax_impl.mibs.ietf import rfc4363


class TestFdbMIB(TestCase):
    @classmethod
    def setUpClass(cls):
        class FdbMIB(rfc4363.FdbMIB):
            pass

        cls.lut = MIBTable(FdbMIB)

    def test_print_oids(self):
        for k in self.lut.keys():
            print(k)
        #mib_entry = self.lut[(1, 3, 6, 1, 2, 1, 17, 7, 1, 2, 2, 1, 2, 1000, 124, 254, 144, 128, 159, 92)]

    def test_getpdu(self):
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=(
                ObjectIdentifier(20, 0, 0, 0, (1, 3, 6, 1, 2, 1, 17, 7, 1, 2, 2, 1, 2, 1000, 124, 254, 144, 128, 159, 92)),
            )
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.INTEGER)
        self.assertEqual(value0.data, 49)


