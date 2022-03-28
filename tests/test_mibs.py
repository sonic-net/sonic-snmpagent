import os
import sys
from unittest import TestCase

import tests.mock_tables.dbconnector
from sonic_ax_impl import mibs

if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from sonic_ax_impl.mibs import Namespace
from sonic_ax_impl import mibs

class TestGetNextPDU(TestCase):
    @classmethod
    def setUpClass(cls):
        #For single namespace scenario, load database_config.json
        tests.mock_tables.dbconnector.load_database_config()

    def test_init_sync_d_lag_tables(self):
        db_conn = Namespace.init_namespace_dbs()

        lag_name_if_name_map, \
        if_name_lag_name_map, \
        oid_lag_name_map, \
        lag_sai_map, _ = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_lag_tables, db_conn)

        self.assertTrue("PortChannel04" in lag_name_if_name_map)
        self.assertTrue(lag_name_if_name_map["PortChannel04"] == ["Ethernet124"])
        self.assertTrue("Ethernet124" in if_name_lag_name_map)
        self.assertTrue(if_name_lag_name_map["Ethernet124"] == "PortChannel04")

        self.assertTrue("PortChannel_Temp" in lag_name_if_name_map)
        self.assertTrue(lag_name_if_name_map["PortChannel_Temp"] == [])
        self.assertTrue(lag_sai_map["PortChannel01"] == "2000000000006")

    @mock.patch('swsssdk.dbconnector.SonicV2Connector.get_all', mock.MagicMock(return_value=({})))
    def test_init_sync_d_interface_tables(self):
        db_conn = Namespace.init_namespace_dbs()

        if_name_map, \
        if_alias_map, \
        if_id_map, \
        oid_name_map = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_interface_tables, db_conn)
        self.assertTrue(if_name_map == {})
        self.assertTrue(if_alias_map == {})
        self.assertTrue(if_id_map == {})
        self.assertTrue(oid_name_map == {})

    @mock.patch('swsssdk.dbconnector.SonicV2Connector.get_all', mock.MagicMock(return_value=({})))
    def test_init_sync_d_queue_tables(self):
        mock_queue_stat_map = {}
        db_conn = Namespace.init_namespace_dbs()

        port_queues_map, queue_stat_map, port_queue_list_map = \
            Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_queue_tables, db_conn)
        self.assertTrue(port_queues_map == {})
        self.assertTrue(queue_stat_map == {})
        self.assertTrue(port_queue_list_map == {})

    @mock.patch('swsssdk.dbconnector.SonicV2Connector.get_all', mock.MagicMock(return_value=({})))
    def test_init_sync_d_vlan_tables(self):
        db_conn = Namespace.init_namespace_dbs()

        vlan_name_map, \
        vlan_oid_sai_map, \
        vlan_oid_name_map = Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_vlan_tables, db_conn)

        self.assertTrue(vlan_name_map == {})
        self.assertTrue(vlan_oid_sai_map == {})
        self.assertTrue(vlan_oid_name_map == {})
