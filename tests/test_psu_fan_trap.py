import os
import sys
from unittest import TestCase
from unittest import mock

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from sonic_ax_impl.mibs.ietf.psu_fan_trap import psuFanTrap
from sonic_ax_impl.mibs import Namespace


def make_trap():
    """Construct a psuFanTrap with the real DB layer stubbed out."""
    with mock.patch.object(Namespace, 'init_namespace_dbs', return_value=["db"]), \
         mock.patch.object(Namespace, 'connect_all_dbs'):
        return psuFanTrap()


class TestParseFanIndex(TestCase):
    def setUp(self):
        self.trap = make_trap()

    def test_psu_internal_fan_index(self):
        self.assertEqual(self.trap._parse_fan_index("PSU1_FAN1"), 101)
        self.assertEqual(self.trap._parse_fan_index("PSU2_FAN1"), 201)

    def test_fantray_index(self):
        self.assertEqual(self.trap._parse_fan_index("FANTRAY2_1"), 21)
        self.assertEqual(self.trap._parse_fan_index("FANTRAY1_2"), 12)

    def test_is_case_insensitive(self):
        self.assertEqual(self.trap._parse_fan_index("psu1_fan1"), 101)

    def test_unknown_format_returns_zero(self):
        self.assertEqual(self.trap._parse_fan_index("weirdname"), 0)


class TestCalcFanStatus(TestCase):
    def setUp(self):
        self.trap = make_trap()

    def test_absent_is_down(self):
        entry = {"presence": "false", "status": "true"}
        self.assertEqual(self.trap._calc_fan_status(entry), self.trap.FAN_STATUS_MAP["down"])

    def test_bad_status_is_down(self):
        entry = {"presence": "true", "status": "false"}
        self.assertEqual(self.trap._calc_fan_status(entry), self.trap.FAN_STATUS_MAP["down"])

    def test_under_speed_is_warning(self):
        entry = {"presence": "true", "status": "true", "is_under_speed": "true"}
        self.assertEqual(self.trap._calc_fan_status(entry), self.trap.FAN_STATUS_MAP["warning"])

    def test_over_speed_is_warning(self):
        entry = {"presence": "true", "status": "true", "is_over_speed": "true"}
        self.assertEqual(self.trap._calc_fan_status(entry), self.trap.FAN_STATUS_MAP["warning"])

    def test_normal_is_up(self):
        entry = {
            "presence": "true", "status": "true",
            "is_under_speed": "false", "is_over_speed": "false",
        }
        self.assertEqual(self.trap._calc_fan_status(entry), self.trap.FAN_STATUS_MAP["up"])

    def test_missing_fields_default_to_down_not_up(self):
        # An empty/missing entry (e.g. key just deleted) must resolve to
        # "down" via the field defaults, never silently read as "up".
        self.assertEqual(self.trap._calc_fan_status({}), self.trap.FAN_STATUS_MAP["down"])


class TestCalcPsuStatus(TestCase):
    def setUp(self):
        self.trap = make_trap()

    def test_absent_is_offEnvOther(self):
        entry = {"presence": "false"}
        self.assertEqual(self.trap._calc_psu_status(entry), self.trap.PSU_STATUS_MAP["offEnvOther"])

    def test_present_but_status_false_is_failed(self):
        # Hardware-confirmed removal signature on this platform: `presence`
        # stays "true" on physical removal, only `status` flips to false.
        entry = {"presence": "true", "status": "false"}
        self.assertEqual(self.trap._calc_psu_status(entry), self.trap.PSU_STATUS_MAP["failed"])

    def test_power_overload_takes_priority_over_voltage_and_temp(self):
        entry = {
            "presence": "true", "status": "true", "power_overload": "true",
            "voltage": "20", "voltage_min_threshold": "11", "voltage_max_threshold": "14",
        }
        self.assertEqual(self.trap._calc_psu_status(entry), self.trap.PSU_STATUS_MAP["offEnvPower"])

    def test_voltage_below_min_threshold_is_onButInLinePowerFail(self):
        entry = {
            "presence": "true", "status": "true", "power_overload": "false",
            "voltage": "9", "voltage_min_threshold": "11", "voltage_max_threshold": "14",
        }
        self.assertEqual(self.trap._calc_psu_status(entry), self.trap.PSU_STATUS_MAP["onButInLinePowerFail"])

    def test_voltage_above_max_threshold_is_onButInLinePowerFail(self):
        entry = {
            "presence": "true", "status": "true", "power_overload": "false",
            "voltage": "20", "voltage_min_threshold": "11", "voltage_max_threshold": "14",
        }
        self.assertEqual(self.trap._calc_psu_status(entry), self.trap.PSU_STATUS_MAP["onButInLinePowerFail"])

    def test_temp_at_or_above_threshold_is_offEnvTemp(self):
        entry = {
            "presence": "true", "status": "true", "power_overload": "false",
            "voltage": "12", "voltage_min_threshold": "11", "voltage_max_threshold": "14",
            "temp": "60", "temp_threshold": "60",
        }
        self.assertEqual(self.trap._calc_psu_status(entry), self.trap.PSU_STATUS_MAP["offEnvTemp"])

    def test_normal_is_on(self):
        entry = {
            "presence": "true", "status": "true", "power_overload": "false",
            "voltage": "12.2", "voltage_min_threshold": "11", "voltage_max_threshold": "14",
            "temp": "25", "temp_threshold": "60",
        }
        self.assertEqual(self.trap._calc_psu_status(entry), self.trap.PSU_STATUS_MAP["on"])

    def test_non_numeric_voltage_is_tolerated_not_raised(self):
        entry = {
            "presence": "true", "status": "true", "power_overload": "false",
            "voltage": "not-a-number",
            "temp": "25", "temp_threshold": "60",
        }
        self.assertEqual(self.trap._calc_psu_status(entry), self.trap.PSU_STATUS_MAP["on"])

    def test_non_numeric_temp_is_tolerated_not_raised(self):
        entry = {
            "presence": "true", "status": "true", "power_overload": "false",
            "voltage": "12", "voltage_min_threshold": "11", "voltage_max_threshold": "14",
            "temp": "not-a-number", "temp_threshold": "60",
        }
        self.assertEqual(self.trap._calc_psu_status(entry), self.trap.PSU_STATUS_MAP["on"])


class TestTrapInit(TestCase):
    def test_preloads_fan_and_psu_tables(self):
        trap = make_trap()

        def fake_dbs_keys(dbs, db_name, pattern):
            return {
                "FAN_INFO|*": ["FAN_INFO|PSU1_FAN1"],
                "PSU_INFO|*": ["PSU_INFO|Psu1"],
            }.get(pattern, [])

        def fake_dbs_get_all(dbs, db_name, key, **kwargs):
            return {
                "FAN_INFO|PSU1_FAN1": {"presence": "true", "status": "true"},
                "PSU_INFO|Psu1": {"presence": "true", "status": "true"},
            }.get(key, {})

        with mock.patch.object(Namespace, 'dbs_keys', side_effect=fake_dbs_keys), \
             mock.patch.object(Namespace, 'dbs_get_all', side_effect=fake_dbs_get_all):
            trap.trap_init()

        self.assertEqual(trap.fanTable["FAN_INFO|PSU1_FAN1"], trap.FAN_STATUS_MAP["up"])
        self.assertEqual(trap.psuTable["PSU_INFO|Psu1"], trap.PSU_STATUS_MAP["on"])

    def test_empty_db_entry_is_skipped_not_cached(self):
        trap = make_trap()
        with mock.patch.object(Namespace, 'dbs_keys', return_value=["FAN_INFO|Ghost"]), \
             mock.patch.object(Namespace, 'dbs_get_all', return_value=None):
            trap.trap_init()
        self.assertNotIn("FAN_INFO|Ghost", trap.fanTable)


class TestTrapProcess(TestCase):
    def setUp(self):
        self.trap = make_trap()

    def test_missing_db_entry_produces_no_trap(self):
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=None):
            result = self.trap.trap_process(["hset"], "__keyspace@6__:PSU_INFO|Psu2")
        self.assertIsNone(result)

    def test_first_observed_fan_status_generates_a_trap(self):
        entry = {"presence": "true", "status": "true"}
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=entry):
            result = self.trap.trap_process(["hset"], "__keyspace@6__:FAN_INFO|PSU2_FAN1")

        self.assertIsNotNone(result)
        self.assertEqual(result["TrapOid"].subids, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1))
        varbind = result["varBinds"][0]
        self.assertEqual(varbind.name.subids, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1, 201))
        self.assertEqual(varbind.data, self.trap.FAN_STATUS_MAP["up"])
        self.assertEqual(self.trap.fanTable["FAN_INFO|PSU2_FAN1"], self.trap.FAN_STATUS_MAP["up"])

    def test_unchanged_fan_status_produces_no_trap(self):
        self.trap.fanTable["FAN_INFO|PSU2_FAN1"] = self.trap.FAN_STATUS_MAP["up"]
        entry = {"presence": "true", "status": "true"}
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=entry):
            result = self.trap.trap_process(["hset"], "__keyspace@6__:FAN_INFO|PSU2_FAN1")
        self.assertIsNone(result)

    def test_fan_status_change_reports_fantray_index(self):
        self.trap.fanTable["FAN_INFO|FANTRAY1_1"] = self.trap.FAN_STATUS_MAP["up"]
        entry = {"presence": "false"}
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=entry):
            result = self.trap.trap_process(["hset"], "__keyspace@6__:FAN_INFO|FANTRAY1_1")

        varbind = result["varBinds"][0]
        self.assertEqual(varbind.name.subids[-1], 11)
        self.assertEqual(varbind.data, self.trap.FAN_STATUS_MAP["down"])

    def test_psu_status_change_generates_trap_with_correct_index(self):
        entry = {"presence": "true", "status": "false"}
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=entry):
            result = self.trap.trap_process(["hset"], "__keyspace@6__:PSU_INFO|Psu2")

        self.assertIsNotNone(result)
        self.assertEqual(result["TrapOid"].subids, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2))
        varbind = result["varBinds"][0]
        self.assertEqual(varbind.name.subids, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2, 2))
        self.assertEqual(varbind.data, self.trap.PSU_STATUS_MAP["failed"])
        self.assertEqual(self.trap.psuTable["PSU_INFO|Psu2"], self.trap.PSU_STATUS_MAP["failed"])

    def test_unchanged_psu_status_produces_no_trap(self):
        self.trap.psuTable["PSU_INFO|Psu2"] = self.trap.PSU_STATUS_MAP["on"]
        entry = {"presence": "true", "status": "true", "power_overload": "false"}
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=entry):
            result = self.trap.trap_process(["hset"], "__keyspace@6__:PSU_INFO|Psu2")
        self.assertIsNone(result)

    def test_unrelated_key_produces_no_trap(self):
        entry = {"foo": "bar"}
        with mock.patch.object(Namespace, 'dbs_get_all', return_value=entry):
            result = self.trap.trap_process(["hset"], "__keyspace@6__:SOME_OTHER_TABLE|x")
        self.assertIsNone(result)
