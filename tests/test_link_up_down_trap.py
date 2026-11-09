import os
import sys
from unittest import TestCase
from unittest import mock

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from sonic_ax_impl import mibs
from sonic_ax_impl.mibs import Namespace
from sonic_ax_impl.mibs.ietf.link_up_down_trap import linkUpDownTrap


def make_trap():
    """Construct a linkUpDownTrap with the real DB layer stubbed out."""
    with mock.patch.object(Namespace, 'init_namespace_dbs', return_value=["db"]), \
         mock.patch.object(Namespace, 'connect_all_dbs'):
        return linkUpDownTrap()


class TestParseChangedKey(TestCase):
    def setUp(self):
        self.trap = make_trap()

    def test_extracts_db_number_and_key(self):
        db_num, key = self.trap._parse_changed_key("__keyspace@0__:PORT_TABLE:Ethernet1")
        self.assertEqual(db_num, "0")
        self.assertEqual(key, "PORT_TABLE:Ethernet1")

    def test_malformed_key_returns_none_none(self):
        db_num, key = self.trap._parse_changed_key("not-a-keyspace-notification")
        self.assertIsNone(db_num)
        self.assertIsNone(key)


class TestMatchInterface(TestCase):
    def setUp(self):
        self.trap = make_trap()

    def test_ethernet_port(self):
        if_name, cache = self.trap._match_interface("PORT_TABLE:Ethernet1")
        self.assertEqual(if_name, "Ethernet1")
        self.assertIs(cache, self.trap.etherTable)

    def test_port_channel(self):
        if_name, cache = self.trap._match_interface("LAG_TABLE:PortChannel1")
        self.assertEqual(if_name, "PortChannel1")
        self.assertIs(cache, self.trap.portChannelTable)

    def test_mgmt_port_config(self):
        if_name, cache = self.trap._match_interface("MGMT_PORT|eth0")
        self.assertEqual(if_name, "eth0")
        self.assertIs(cache, self.trap.mgmtDict)

    def test_mgmt_port_state(self):
        if_name, cache = self.trap._match_interface("MGMT_PORT_TABLE|eth0")
        self.assertEqual(if_name, "eth0")
        self.assertIs(cache, self.trap.mgmtDict)

    def test_unrecognized_key_returns_none_none(self):
        if_name, cache = self.trap._match_interface("SOME_OTHER_TABLE:foo")
        self.assertIsNone(if_name)
        self.assertIsNone(cache)


class TestGetStatusFromDb(TestCase):
    def setUp(self):
        self.trap = make_trap()

    def test_appl_db_reads_both_statuses_directly(self):
        entry = {"admin_status": "up", "oper_status": "down"}
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=entry):
            admin, oper = self.trap._get_status_from_db("0", "PORT_TABLE:Ethernet1")
        self.assertEqual((admin, oper), ("up", "down"))

    def test_appl_db_missing_entry_returns_none_none(self):
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=None):
            admin, oper = self.trap._get_status_from_db("0", "PORT_TABLE:Ethernet1")
        self.assertEqual((admin, oper), (None, None))

    def test_state_db_mgmt_oper_merges_with_cached_admin(self):
        # db_num '6' == STATE_DB: only oper_status comes from the DB entry;
        # admin_status is whatever is already cached for that interface.
        self.trap.mgmtDict["eth0"] = {"admin_status": "up", "oper_status": "down"}
        entry = {"oper_status": "up"}
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=entry):
            admin, oper = self.trap._get_status_from_db("6", "MGMT_PORT_TABLE|eth0")
        self.assertEqual((admin, oper), ("up", "up"))

    def test_config_db_mgmt_admin_merges_with_cached_oper(self):
        # db_num '4' == CONFIG_DB: only admin_status comes from the DB entry;
        # oper_status is whatever is already cached for that interface.
        self.trap.mgmtDict["eth0"] = {"admin_status": "down", "oper_status": "up"}
        entry = {"admin_status": "up"}
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=entry):
            admin, oper = self.trap._get_status_from_db("4", "MGMT_PORT|eth0")
        self.assertEqual((admin, oper), ("up", "up"))

    def test_state_db_mgmt_oper_defaults_when_uncached(self):
        entry = {"oper_status": "down"}
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=entry):
            admin, oper = self.trap._get_status_from_db("6", "MGMT_PORT_TABLE|eth0")
        self.assertEqual((admin, oper), ("down", "down"))

    def test_exception_from_db_layer_is_swallowed(self):
        with mock.patch.object(Namespace, 'dbs_get_all', side_effect=RuntimeError("boom")):
            admin, oper = self.trap._get_status_from_db("0", "PORT_TABLE:Ethernet1")
        self.assertEqual((admin, oper), (None, None))

    def test_state_db_missing_entry_returns_none_none(self):
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=None):
            admin, oper = self.trap._get_status_from_db("6", "MGMT_PORT_TABLE|eth0")
        self.assertEqual((admin, oper), (None, None))

    def test_config_db_missing_entry_returns_none_none(self):
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=None):
            admin, oper = self.trap._get_status_from_db("4", "MGMT_PORT|eth0")
        self.assertEqual((admin, oper), (None, None))


class TestBuildTrap(TestCase):
    def setUp(self):
        self.trap = make_trap()

    def test_unknown_oper_status_produces_no_trap(self):
        result = self.trap._build_trap("Ethernet1", "up", "flapping")
        self.assertIsNone(result)

    def test_valid_status_produces_trap_with_correct_ifindex_and_oid(self):
        result = self.trap._build_trap("Ethernet1", "up", "down")

        self.assertEqual(result["TrapOid"].subids, (1, 3, 6, 1, 6, 3, 1, 1, 5, 3))
        if_index_vb, admin_vb, oper_vb = result["varBinds"]
        self.assertEqual(if_index_vb.name.subids, (1, 3, 6, 1, 2, 1, 2, 2, 1, 1, 2))
        self.assertEqual(if_index_vb.data, 2)
        self.assertEqual(admin_vb.name.subids, (1, 3, 6, 1, 2, 1, 2, 2, 1, 7, 2))
        self.assertEqual(admin_vb.data, self.trap.STATUS_MAP["up"])
        self.assertEqual(oper_vb.name.subids, (1, 3, 6, 1, 2, 1, 2, 2, 1, 8, 2))
        self.assertEqual(oper_vb.data, self.trap.STATUS_MAP["down"])

    def test_linkup_uses_linkup_trap_oid(self):
        result = self.trap._build_trap("Ethernet1", "up", "up")
        self.assertEqual(result["TrapOid"].subids, (1, 3, 6, 1, 6, 3, 1, 1, 5, 4))


class TestTrapProcess(TestCase):
    def setUp(self):
        self.trap = make_trap()

    def test_first_observed_state_generates_trap(self):
        entry = {"admin_status": "up", "oper_status": "down"}
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=entry):
            result = self.trap.trap_process([], "__keyspace@0__:PORT_TABLE:Ethernet1")

        self.assertIsNotNone(result)
        self.assertEqual(self.trap.etherTable["Ethernet1"], {"admin_status": "up", "oper_status": "down"})

    def test_unchanged_state_produces_no_trap(self):
        self.trap.etherTable["Ethernet1"] = {"admin_status": "up", "oper_status": "down"}
        entry = {"admin_status": "up", "oper_status": "down"}
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=entry):
            result = self.trap.trap_process([], "__keyspace@0__:PORT_TABLE:Ethernet1")
        self.assertIsNone(result)

    def test_oper_status_change_generates_trap_and_updates_cache(self):
        self.trap.etherTable["Ethernet1"] = {"admin_status": "up", "oper_status": "down"}
        entry = {"admin_status": "up", "oper_status": "up"}
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=entry):
            result = self.trap.trap_process([], "__keyspace@0__:PORT_TABLE:Ethernet1")

        self.assertIsNotNone(result)
        self.assertEqual(result["TrapOid"].subids, (1, 3, 6, 1, 6, 3, 1, 1, 5, 4))  # linkUp
        self.assertEqual(self.trap.etherTable["Ethernet1"]["oper_status"], "up")

    def test_malformed_key_produces_no_trap(self):
        result = self.trap.trap_process([], "not-a-keyspace-notification")
        self.assertIsNone(result)

    def test_missing_db_entry_produces_no_trap(self):
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=None):
            result = self.trap.trap_process([], "__keyspace@0__:PORT_TABLE:Ethernet1")
        self.assertIsNone(result)

    def test_portchannel_state_change_generates_trap(self):
        entry = {"admin_status": "up", "oper_status": "up"}
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=entry):
            result = self.trap.trap_process([], "__keyspace@0__:LAG_TABLE:PortChannel1")

        self.assertIsNotNone(result)
        self.assertEqual(self.trap.portChannelTable["PortChannel1"]["oper_status"], "up")

    def test_mgmt_port_admin_then_oper_change_both_trigger_and_merge(self):
        # CONFIG_DB (admin) notification arrives first.
        with mock.patch.object(Namespace, 'dbs_get_all', return_value={"admin_status": "up"}):
            result1 = self.trap.trap_process([], "__keyspace@4__:MGMT_PORT|eth0")
        self.assertIsNotNone(result1)
        self.assertEqual(self.trap.mgmtDict["eth0"], {"admin_status": "up", "oper_status": "down"})

        # STATE_DB (oper) notification arrives next; admin_status must be preserved.
        with mock.patch.object(Namespace, 'dbs_get_all', return_value={"oper_status": "up"}):
            result2 = self.trap.trap_process([], "__keyspace@6__:MGMT_PORT_TABLE|eth0")
        self.assertIsNotNone(result2)
        self.assertEqual(self.trap.mgmtDict["eth0"], {"admin_status": "up", "oper_status": "up"})
        # The second trap must reflect the merged state, not just "up"/None.
        oper_vb = result2["varBinds"][2]
        self.assertEqual(oper_vb.data, self.trap.STATUS_MAP["up"])


class TestInitTables(TestCase):
    def test_init_ethernet_ports_populates_ether_table(self):
        trap = make_trap()

        def fake_dbs_keys(dbs, db_name, pattern):
            return ["PORT_TABLE:Ethernet1"] if pattern == "PORT_TABLE:Ethernet*" else []

        def fake_dbs_get_all(dbs, db_name, key, **kwargs):
            return {"admin_status": "up", "oper_status": "down"}

        with mock.patch.object(Namespace, 'dbs_keys', side_effect=fake_dbs_keys), \
             mock.patch.object(Namespace, 'dbs_get_all', side_effect=fake_dbs_get_all):
            trap._init_ethernet_ports()

        self.assertEqual(
            trap.etherTable["Ethernet1"], {"admin_status": "up", "oper_status": "down"}
        )

    def test_init_port_channels_populates_portchannel_table(self):
        trap = make_trap()

        def fake_dbs_keys(dbs, db_name, pattern):
            return ["LAG_TABLE:PortChannel1"] if pattern == "LAG_TABLE:PortChannel*" else []

        def fake_dbs_get_all(dbs, db_name, key, **kwargs):
            return {"admin_status": "down", "oper_status": "down"}

        with mock.patch.object(Namespace, 'dbs_keys', side_effect=fake_dbs_keys), \
             mock.patch.object(Namespace, 'dbs_get_all', side_effect=fake_dbs_get_all):
            trap._init_port_channels()

        self.assertEqual(
            trap.portChannelTable["PortChannel1"], {"admin_status": "down", "oper_status": "down"}
        )

    def test_init_mgmt_ports_state_only_interface_defaults_admin_down(self):
        # An interface present in STATE_DB (oper) but absent from CONFIG_DB
        # (admin) must still be recorded, with admin_status defaulted.
        trap = make_trap()

        def fake_dbs_keys(dbs, db_name, pattern):
            return {
                "MGMT_PORT|eth*": [],
                "MGMT_PORT_TABLE|eth*": ["MGMT_PORT_TABLE|eth1"],
            }.get(pattern, [])

        def fake_dbs_get_all(dbs, db_name, key, **kwargs):
            return {"MGMT_PORT_TABLE|eth1": {"oper_status": "up"}}.get(key, {})

        with mock.patch.object(Namespace, 'dbs_keys', side_effect=fake_dbs_keys), \
             mock.patch.object(Namespace, 'dbs_get_all', side_effect=fake_dbs_get_all):
            trap._init_mgmt_ports()

        self.assertEqual(trap.mgmtDict["eth1"], {"admin_status": "down", "oper_status": "up"})

    def test_trap_init_calls_all_three_initializers(self):
        trap = make_trap()
        with mock.patch.object(trap, '_init_ethernet_ports') as mock_eth, \
             mock.patch.object(trap, '_init_port_channels') as mock_lag, \
             mock.patch.object(trap, '_init_mgmt_ports') as mock_mgmt:
            trap.trap_init()

        mock_eth.assert_called_once()
        mock_lag.assert_called_once()
        mock_mgmt.assert_called_once()

    def test_init_mgmt_ports_merges_config_and_state(self):
        trap = make_trap()

        def fake_dbs_keys(dbs, db_name, pattern):
            return {
                "MGMT_PORT|eth*": ["MGMT_PORT|eth0"],
                "MGMT_PORT_TABLE|eth*": ["MGMT_PORT_TABLE|eth0"],
            }.get(pattern, [])

        def fake_dbs_get_all(dbs, db_name, key, **kwargs):
            return {
                "MGMT_PORT|eth0": {"admin_status": "up"},
                "MGMT_PORT_TABLE|eth0": {"oper_status": "up"},
            }.get(key, {})

        with mock.patch.object(Namespace, 'dbs_keys', side_effect=fake_dbs_keys), \
             mock.patch.object(Namespace, 'dbs_get_all', side_effect=fake_dbs_get_all):
            trap._init_mgmt_ports()

        self.assertEqual(trap.mgmtDict["eth0"], {"admin_status": "up", "oper_status": "up"})
