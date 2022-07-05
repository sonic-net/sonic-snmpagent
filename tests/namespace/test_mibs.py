import os
import sys
from unittest import TestCase

import tests.mock_tables.dbconnector
from sonic_ax_impl.mibs import Namespace
from sonic_ax_impl import mibs

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from sonic_ax_impl import mibs
from sonic_py_common.port_util import BaseIdx

class TestGetNextPDU(TestCase):
    @classmethod
    def setUpClass(cls):
        tests.mock_tables.dbconnector.load_namespace_config()

    def test_init_namespace_sync_d_lag_tables(self):
        dbs = Namespace.init_namespace_dbs()

        lag_name_if_name_map, \
        if_name_lag_name_map, \
        oid_lag_name_map, \
        lag_sai_map, \
        sai_lag_map = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_lag_tables, dbs)
        #PortChannel in asic0 Namespace
        self.assertTrue("PortChannel01" in lag_name_if_name_map)
        self.assertTrue("Ethernet-BP0" in lag_name_if_name_map["PortChannel01"])
        self.assertTrue("Ethernet-BP4" in lag_name_if_name_map["PortChannel01"])
        #PortChannel in asic2 Namespace
        self.assertTrue("PortChannel03" in lag_name_if_name_map)
        self.assertTrue("Ethernet-BP16" in lag_name_if_name_map["PortChannel03"])
        self.assertTrue("Ethernet-BP20" in lag_name_if_name_map["PortChannel03"])

        self.assertTrue("PortChannel_Temp" in lag_name_if_name_map)
        self.assertTrue(lag_name_if_name_map["PortChannel_Temp"] == [])

    def test_init_sync_d_interface_tables_for_recirc_ports(self):
        db_conn = Namespace.init_namespace_dbs()

        if_name_map, \
        if_alias_map, \
        if_id_map, \
        oid_name_map = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_interface_tables, db_conn)
        for recirc_port_name, sai_id, intf_alias, intf_id_key, intf_index in [
              ('Ethernet-IB0',  '1000000000080', 'rec0', 'asic0:1000000000080', BaseIdx.ethernet_ib_base_idx),
              ('Ethernet-Rec0', '1000000000081', 'rec1', 'asic0:1000000000081', BaseIdx.ethernet_rec_base_idx)]:
            self.assertTrue(if_name_map[recirc_port_name] == sai_id)
            self.assertTrue(if_alias_map[recirc_port_name] == intf_alias)
            self.assertTrue(oid_name_map[intf_index] == recirc_port_name)
            self.assertTrue(if_id_map[intf_id_key] == recirc_port_name)

    @classmethod
    def tearDownClass(cls):
        tests.mock_tables.dbconnector.clean_up_config()
