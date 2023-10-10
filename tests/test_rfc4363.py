import os
import sys
import sonic_ax_impl
from unittest import TestCase

if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from sonic_ax_impl.mibs.ietf.rfc4363 import FdbUpdater

class TestFdbUpdater(TestCase):

    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_keys', mock.MagicMock(return_value=(['ASIC_STATE:SAI_OBJECT_TYPE_FDB_ENTRY:{"bvid":"oid:0x26000000000b6c","mac":"60:45:BD:98:6F:48","switch_id":"oid:0x21000000000000"}'])))
    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_get_all', mock.MagicMock(return_value=({"nexthop": "10.0.0.1,10.0.0.3", "ifname": "Ethernet0,Ethernet4"})))
    def test_FdbUpdater_ent_bridge_port_id_attr_missing(self):
        updater = FdbUpdater()

        with mock.patch('sonic_ax_impl.mibs.logger.warn') as mocked_warn:
            updater.update_data()
            
            # check warning
            mocked_warn.assert_called()

        self.assertTrue(len(updater.vlanmac_ifindex_list) == 0)


    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_keys', mock.MagicMock(return_value=(None)))
    @mock.patch('sonic_ax_impl.mibs.Namespace.dbs_get_bridge_port_map', mock.MagicMock(return_value=(None)))
    def test_RouteUpdater_re_init_redis_exception(self):
        updater = FdbUpdater()

        def mock_get_sync_d_from_all_namespace(per_namespace_func, db_conn):
            if per_namespace_func == sonic_ax_impl.mibs.init_sync_d_interface_tables:
                return [{}, {}, {}, {}]

            return [{}, {}, {}, {}, {}]

        with mock.patch('sonic_ax_impl.mibs.Namespace.get_sync_d_from_all_namespace', mock_get_sync_d_from_all_namespace):
            with mock.patch('sonic_ax_impl.mibs.Namespace.connect_namespace_dbs') as connect_namespace_dbs:
                updater.reinit_connection()

                # check re-init
                connect_namespace_dbs.assert_called()