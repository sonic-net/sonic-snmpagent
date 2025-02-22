import os
import sys
import importlib
import pytest

if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

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
from sonic_ax_impl.mibs.vendor.cisco import ciscoPfcExtMIB

class TestPfcPortCounters(TestCase):
    @classmethod
    def setUpClass(cls):
        tests.mock_tables.dbconnector.load_database_config()
        importlib.reload(ciscoPfcExtMIB)
        cls.lut_port = MIBTable(ciscoPfcExtMIB.cpfcIfTable)
        cls.lut_prio = MIBTable(ciscoPfcExtMIB.cpfcIfPriorityTable)
		
		# Update MIBs
        for updater in cls.lut_port.updater_instances:
            updater.reinit_data()
            updater.update_data()
        for updater in cls.lut_prio.updater_instances:
            updater.reinit_data()
            updater.update_data()

    def test_getPduRequestForPort(self):
        oid = ObjectIdentifier(32, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 1, 1, 1, 1))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut_port)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.COUNTER_64)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 4)

    def test_getNextPduRequestForPort(self):
        oid = ObjectIdentifier(32, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 1, 1, 1, 1))
        expected_oid = ObjectIdentifier(32, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 1, 1, 1, 5))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut_port)
        print(response)

        n = len(response.values)
        print('values = ' + str(n))
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.COUNTER_64)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 4)

    def test_getPduIndicationForPort(self):
        oid = ObjectIdentifier(32, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 1, 1, 2, 1))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut_port)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.COUNTER_64)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 4)

    def test_getNextPduindicationForPort(self):
        oid = ObjectIdentifier(32, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 1, 1, 2, 1))
        expected_oid = ObjectIdentifier(32, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 1, 1, 2, 5))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut_port)
        print(response)

        n = len(response.values)
        print('values = ' + str(n))
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.COUNTER_64)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 4)

    def test_getPduRequestForPriority(self):
        oid = ObjectIdentifier(8, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 2, 1, 2, 1, 0))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut_prio)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.COUNTER_64)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 209347219842134092490 % pow(2, 64)) # Test integer truncation

    def test_getNextPduRequestForPriority(self):
        oid = ObjectIdentifier(8, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 2, 1, 2, 1, 1))
        expected_oid = ObjectIdentifier(8, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 2, 1, 2, 1, 2))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut_prio)
        print(response)

        n = len(response.values)
        print('values = ' + str(n))
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.COUNTER_64)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 3)

    def test_getPduIndicationForPriority(self):
        oid = ObjectIdentifier(8, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 2, 1, 3, 5, 0))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut_prio)
        print(response)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.COUNTER_64)
        self.assertEqual(str(value0.name), str(oid))
        self.assertEqual(value0.data, 1)

    def test_getPduIndicationLagMemberCounterNotAvailable(self):
        oid = ObjectIdentifier(8, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 2, 1, 3, 1004, 0))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        with mock.patch('ax_interface.logger.exception') as mock_logger:
            encoded = get_pdu.encode()
            response = get_pdu.make_response(self.lut_prio)
            mock_logger.assert_not_called()
        print(response)
        value0 = response.values[0]
        self.assertEqual(value0.data, None)


    def test_getPduRequestsLagMemberCounterNotAvailable(self):
        oid = ObjectIdentifier(8, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 2, 1, 2, 1004, 0))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        with mock.patch('ax_interface.logger.exception') as mock_logger:
            encoded = get_pdu.encode()
            response = get_pdu.make_response(self.lut_prio)
            mock_logger.assert_not_called()
        print(response)
        value0 = response.values[0]
        self.assertEqual(value0.data, None)

    def test_getPduifIndicationLagMemberCounterNotAvailable(self):
        oid = ObjectIdentifier(8, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 1, 1, 1, 1004))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        with mock.patch('ax_interface.logger.exception') as mock_logger:
            encoded = get_pdu.encode()
            response = get_pdu.make_response(self.lut_prio)
            mock_logger.assert_not_called()
        print(response)
        value0 = response.values[0]
        self.assertEqual(value0.data, None)

    def test_getPduifRequestLagMemberCounterNotAvailable(self):
        oid = ObjectIdentifier(8, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 1, 1, 1, 1004))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        with mock.patch('ax_interface.logger.exception') as mock_logger:
            encoded = get_pdu.encode()
            response = get_pdu.make_response(self.lut_prio)
            mock_logger.assert_not_called()
        print(response)
        value0 = response.values[0]
        self.assertEqual(value0.data, None)

    def test_getNextPduindicationForPriority(self):
        oid = ObjectIdentifier(8, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 2, 1, 3, 1, 0))
        expected_oid = ObjectIdentifier(8, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 2, 1, 3, 1, 1))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut_prio)
        print(response)

        n = len(response.values)
        print('values = ' + str(n))
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.COUNTER_64)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 2)

    def test_getPfcSubtree(self):
        # Subtree for port
        oid = ObjectIdentifier(32, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 1))
        expected_oid = ObjectIdentifier(32, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 1, 1, 1, 1))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut_port)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.COUNTER_64)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 4)

        # Subtree for Priority
        oid = ObjectIdentifier(33, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 2))
        expected_oid = ObjectIdentifier(33, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 813, 1, 2, 1, 2, 1, 0))
        get_pdu = GetNextPDU(
            header=PDUHeader(1, PduTypes.GET_NEXT, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut_prio)

        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.COUNTER_64)
        self.assertEqual(str(value0.name), str(expected_oid))
        self.assertEqual(value0.data, 209347219842134092490 % pow(2, 64)) # Test integer truncation
