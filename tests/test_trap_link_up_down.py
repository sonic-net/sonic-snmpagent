import os
import sys
from unittest import TestCase
from ax_interface.encodings import ObjectIdentifier, ValueRepresentation
from sonic_ax_impl.mibs.ietf import link_up_down_trap as linkUpDownTrap
from swsssdk.port_util import get_index, get_index_from_str
from ax_interface.mib import ValueType
from ax_interface.pdu_implementations import NotifyPDU
from ax_interface.constants import PduTypes
from ax_interface.pdu import PDUHeader

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

class TestLinkUpDownTrap(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trap_module = linkUpDownTrap.linkUpDownTrap()   
        cls.trap_module.trap_init()

    def validate_result(self, if_name, admin_status, oper_status, varBinds):
        status_map = {
            "up": 1,
            "down": 2
        }        
        varBindsList = []
        if_index_value = get_index_from_str(if_name)
        if_index_oid = ObjectIdentifier(11, 0, 0, 0, (1, 3, 6, 1, 2, 1, 2, 2, 1, 1, if_index_value))
        if_index_vb = ValueRepresentation(ValueType.INTEGER, 0, if_index_oid, if_index_value)
        varBindsList.append(if_index_vb)

        # For admin status 
        admin_status_oid = ObjectIdentifier(11, 0, 0, 0, (1, 3, 6, 1, 2, 1, 2, 2, 1, 7, if_index_value))
        admin_status_value = status_map[admin_status]
        admin_status_vb = ValueRepresentation(ValueType.INTEGER, 0, admin_status_oid, admin_status_value)
        varBindsList.append(admin_status_vb)

        # For oper status 
        oper_status_oid = ObjectIdentifier(11, 0, 0, 0, (1, 3, 6, 1, 2, 1, 2, 2, 1, 8, if_index_value))
        oper_status_value = status_map[oper_status]
        oper_status_vb = ValueRepresentation(ValueType.INTEGER, 0, oper_status_oid, oper_status_value)
        varBindsList.append(oper_status_vb)    

        self.assertEqual(varBinds, varBindsList)
        expected_notify_pdu = NotifyPDU(header=PDUHeader(1, PduTypes.NOTIFY, \
            PDUHeader.MASK_NEWORK_BYTE_ORDER, 0, 16, \
                0, 0, 0), varBinds=varBindsList)        
        test_notify_pdu = NotifyPDU(header=PDUHeader(1, PduTypes.NOTIFY, \
            PDUHeader.MASK_NEWORK_BYTE_ORDER, 0, 16, \
                0, 0, 0), varBinds=varBindsList) 
        self.assertEqual(test_notify_pdu, expected_notify_pdu)

    def test_no_trap(self):
        """
        This testcase verifies that No trap is generated.
        This case is possible when data in cache and in DB are same
        """     
        response = self.trap_module.trap_process(None,'__keyspace@0__:LAG_TABLE:PortChannel05')
        self.assertEqual(response, None)

    def test_link_down(self):
        """
        This testcase verifies that trap is generated when portChannel goes down
        """
        if self.trap_module.portChannelTable['LAG_TABLE:PortChannel05']['oper_status'] == 'down':
            self.trap_module.portChannelTable['LAG_TABLE:PortChannel05']['oper_status'] = 'up'
        response = self.trap_module.trap_process(None,'__keyspace@0__:LAG_TABLE:PortChannel05')            
        self.assertIsInstance(response, dict)
        TrapOid = ObjectIdentifier(10, 0, 0, 0, (1, 3, 6, 1, 6, 3, 1, 1, 5, 3))
        self.assertEqual(response['TrapOid'], TrapOid)
        self.validate_result('PortChannel05', \
            self.trap_module.portChannelTable['LAG_TABLE:PortChannel05']['admin_status'], \
                self.trap_module.portChannelTable['LAG_TABLE:PortChannel05']['oper_status'], \
                    response['varBinds'])

    def test_link_up(self):
        """
        This testcase verifies that trap is generated when portChannel goes up        
        """
        if self.trap_module.portChannelTable['LAG_TABLE:PortChannel06']['oper_status'] == 'up':
            self.trap_module.portChannelTable['LAG_TABLE:PortChannel06']['oper_status'] = 'down'
        response = self.trap_module.trap_process(None,'__keyspace@0__:LAG_TABLE:PortChannel06')            
        self.assertIsInstance(response, dict)
        TrapOid = ObjectIdentifier(10, 0, 0, 0, (1, 3, 6, 1, 6, 3, 1, 1, 5, 4))
        self.assertEqual(response['TrapOid'], TrapOid)
        self.validate_result('PortChannel06', \
            self.trap_module.portChannelTable['LAG_TABLE:PortChannel06']['admin_status'], \
                self.trap_module.portChannelTable['LAG_TABLE:PortChannel06']['oper_status'], \
                    response['varBinds'])

    def test_no_trap_ethernet(self):
        """
        This testcase verifies that No trap is generated.
        This case is possible when data in cache and in DB are same
        """     
        response = self.trap_module.trap_process(None,'__keyspace@0__:PORT_TABLE:Ethernet128')
        self.assertEqual(response, None)

    def test_link_down_ethernet(self):
        """
        This testcase verifies that trap is generated when portChannel goes down
        """
        if self.trap_module.etherTable['PORT_TABLE:Ethernet128']['oper_status'] == 'down':
            self.trap_module.etherTable['PORT_TABLE:Ethernet128']['oper_status'] = 'up'
        response = self.trap_module.trap_process(None,'__keyspace@0__:PORT_TABLE:Ethernet128')            
        self.assertIsInstance(response, dict)
        TrapOid = ObjectIdentifier(10, 0, 0, 0, (1, 3, 6, 1, 6, 3, 1, 1, 5, 3))
        self.assertEqual(response['TrapOid'], TrapOid)
        self.validate_result('Ethernet128', \
            self.trap_module.etherTable['PORT_TABLE:Ethernet128']['admin_status'], \
                self.trap_module.etherTable['PORT_TABLE:Ethernet128']['oper_status'], \
                    response['varBinds'])

    def test_link_up_ethernet(self):
        """
        This testcase verifies that trap is generated when portChannel goes up        
        """
        if self.trap_module.etherTable['PORT_TABLE:Ethernet132']['oper_status'] == 'up':
            self.trap_module.etherTable['PORT_TABLE:Ethernet132']['oper_status'] = 'down'
        response = self.trap_module.trap_process(None,'__keyspace@0__:PORT_TABLE:Ethernet132')            
        self.assertIsInstance(response, dict)
        TrapOid = ObjectIdentifier(10, 0, 0, 0, (1, 3, 6, 1, 6, 3, 1, 1, 5, 4))
        self.assertEqual(response['TrapOid'], TrapOid)
        self.validate_result('Ethernet132', \
            self.trap_module.etherTable['PORT_TABLE:Ethernet132']['admin_status'], \
                self.trap_module.etherTable['PORT_TABLE:Ethernet132']['oper_status'], \
                    response['varBinds'])                    

    def test_no_trap_mgmt(self):
        """
        This testcase verifies that No trap is generated.
        This case is possible when data in cache and in DB are same
        """     
        response = self.trap_module.trap_process(None,'__keyspace@6__:MGMT_PORT_TABLE|eth0')
        self.assertEqual(response, None)

    def test_link_down_mgmt(self):
        """
        This testcase verifies that trap is generated when portChannel goes down
        """
        if self.trap_module.mgmtDict['eth0']['oper_status'] == 'down':
            self.trap_module.mgmtDict['eth0']['oper_status'] = 'up'
        response = self.trap_module.trap_process(None,'__keyspace@6__:MGMT_PORT_TABLE|eth0')            
        self.assertIsInstance(response, dict)
        TrapOid = ObjectIdentifier(10, 0, 0, 0, (1, 3, 6, 1, 6, 3, 1, 1, 5, 3))
        self.assertEqual(response['TrapOid'], TrapOid)
        self.validate_result('eth0', \
            self.trap_module.mgmtDict['eth0']['admin_status'], \
                self.trap_module.mgmtDict['eth0']['oper_status'], \
                    response['varBinds'])

    def test_link_up_mgmt(self):
        """
        This testcase verifies that trap is generated when portChannel goes up        
        """
        if self.trap_module.mgmtDict['eth1']['oper_status'] == 'up':
            self.trap_module.mgmtDict['eth1']['oper_status'] = 'down'
        response = self.trap_module.trap_process(None,'__keyspace@6__:MGMT_PORT_TABLE|eth1')            
        self.assertIsInstance(response, dict)
        TrapOid = ObjectIdentifier(10, 0, 0, 0, (1, 3, 6, 1, 6, 3, 1, 1, 5, 4))
        self.assertEqual(response['TrapOid'], TrapOid)
        self.validate_result('eth1', \
            self.trap_module.mgmtDict['eth1']['admin_status'], \
                self.trap_module.mgmtDict['eth1']['oper_status'], \
                    response['varBinds'])                     
