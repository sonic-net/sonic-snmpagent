import re
from ax_interface.mib import ValueType
from sonic_ax_impl import mibs
from sonic_ax_impl.mibs import Namespace
from ax_interface.trap import Trap
from ax_interface.encodings import ObjectIdentifier, ValueRepresentation


class psuFanTrap(Trap):
    # Cisco EnvMon fan status values
    FAN_STATUS_MAP = {
        "unknown": 1,
        "up": 2,
        "down": 3,
        "warning": 4
    }

    # Cisco EnvMon PSU status values
    PSU_STATUS_MAP = {
        "offEnvOther": 1,
        "on": 2,
        "offAdmin": 3,
        "offDenied": 4,
        "offEnvPower": 5,
        "offEnvTemp": 6,
        "offEnvFan": 7,
        "failed": 8,
        "onButFanFail": 9,
        "offCooling": 10,
        "offConnectorRating": 11,
        "onButInLinePowerFail": 12
    }

    def __init__(self):
        # Subscribe to Redis keyspace notifications for FAN and PSU info
        super().__init__(dbKeys=[
            "__keyspace@6__:FAN_INFO|*",
            "__keyspace@6__:PSU_INFO|*"
        ])

        self.db_conn = Namespace.init_namespace_dbs()
        Namespace.connect_all_dbs(self.db_conn, mibs.STATE_DB)

        # Cache ONLY the final mapped status value
        # Key   -> Redis key (e.g. FAN_INFO|PSU1_FAN1)
        # Value -> INTEGER value actually sent in SNMP trap
        self.fanTable = {}
        self.psuTable = {}

    def trap_init(self):
        """
        Preload current device state at startup.

        This prevents sending SNMP traps immediately after
        snmp-subagent restart for already-existing conditions.
        """
        self._init_fan_table()
        self._init_psu_table()

    def _init_fan_table(self):
        keys = Namespace.dbs_keys(self.db_conn, mibs.STATE_DB, "FAN_INFO|*") or []

        for key in keys:
            entry = Namespace.dbs_get_all(self.db_conn, mibs.STATE_DB, key, blocking=True)
            if not entry:
                continue

            # Store the computed fan status, not raw DB fields
            self.fanTable[key] = self._calc_fan_status(entry)

    def _init_psu_table(self):
        keys = Namespace.dbs_keys(self.db_conn, mibs.STATE_DB, "PSU_INFO|*") or []

        for key in keys:
            entry = Namespace.dbs_get_all(self.db_conn, mibs.STATE_DB, key, blocking=True)
            if not entry:
                continue

            # Store the computed PSU status, not raw DB fields
            self.psuTable[key] = self._calc_psu_status(entry)

    def _parse_fan_index(self, key_suffix):
        """
        Convert Redis key suffix into Cisco EnvMon fan index.

        Examples:
          PSU1_FAN1   -> 101
          PSU2_FAN1   -> 201
          FANTRAY2_1  -> 21
        """
        key_upper = key_suffix.upper()

        # PSU fan
        match = re.fullmatch(r"PSU(\d+)_FAN(\d+)", key_upper)
        if match:
            return int(match.group(1)) * 100 + int(match.group(2))

        # Fantray fan
        match = re.fullmatch(r"FANTRAY(\d+)_(\d+)", key_upper)
        if match:
            return int(match.group(1)) * 10 + int(match.group(2))

        # Unknown format
        return 0

    def _calc_fan_status(self, entry):
        """
        Calculate final fan status according to Cisco EnvMon rules.

        IMPORTANT:
        This function defines the *semantic state* of a fan.
        SNMP traps must be triggered ONLY when this value changes.
        """
        presence = entry.get("presence", "false").lower()
        status = entry.get("status", "false").lower()
        is_under_speed = entry.get("is_under_speed", "false").lower()
        is_over_speed = entry.get("is_over_speed", "false").lower()

        if presence != "true":
            return self.FAN_STATUS_MAP["down"]

        if status != "true":
            return self.FAN_STATUS_MAP["down"]

        if is_under_speed == "true" or is_over_speed == "true":
            return self.FAN_STATUS_MAP["warning"]

        return self.FAN_STATUS_MAP["up"]

    def _calc_psu_status(self, entry):
        """
        Calculate final PSU status according to Cisco EnvMon rules.

        IMPORTANT:
        Many DB fields may change (voltage, temp, etc),
        but SNMP trap should only be sent if the *mapped status*
        actually changes.
        """
        if entry.get("presence", "false").lower() != "true":
            return self.PSU_STATUS_MAP["offEnvOther"]

        if entry.get("status", "false").lower() != "true":
            return self.PSU_STATUS_MAP["failed"]

        if entry.get("power_overload", "false").lower() == "true":
            return self.PSU_STATUS_MAP["offEnvPower"]

        try:
            voltage = float(entry.get("voltage", 0))
            vmin = float(entry.get("voltage_min_threshold", 0))
            vmax = float(entry.get("voltage_max_threshold", 0))
            if (vmin and voltage < vmin) or (vmax and voltage > vmax):
                return self.PSU_STATUS_MAP["onButInLinePowerFail"]
        except ValueError:
            pass

        try:
            temp = float(entry.get("temp", 0))
            temp_th = float(entry.get("temp_threshold", 0))
            if temp_th and temp >= temp_th:
                return self.PSU_STATUS_MAP["offEnvTemp"]
        except ValueError:
            pass

        return self.PSU_STATUS_MAP["on"]

    def trap_process(self, dbMessage, changedKey):
        """
        Process Redis keyspace notification and decide
        whether an SNMP trap should be sent.
        """
        returnDict = {}
        varBindsList = []

        # Extract real Redis key from keyspace notification
        actualKey = changedKey.split(":", 1)[1] if ":" in changedKey else changedKey

        dbEntry = Namespace.dbs_get_all(self.db_conn, mibs.STATE_DB, actualKey, blocking=False)
        if not dbEntry:
            return None

        # ---------------- FAN ----------------
        if actualKey.startswith("FAN_INFO|"):
            fan_status_value = self._calc_fan_status(dbEntry)

            # CRITICAL:
            # Do NOT send trap if final fan status has not changed.
            # This avoids trap storms caused by harmless DB updates.
            if self.fanTable.get(actualKey) == fan_status_value:
                return None

            # Update cached status AFTER change is confirmed
            self.fanTable[actualKey] = fan_status_value

            key_suffix = actualKey.split("|", 1)[1]
            fan_index = self._parse_fan_index(key_suffix)

            returnDict["TrapOid"] = ObjectIdentifier(14, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1))

            fan_status_oid = ObjectIdentifier(15, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 4, 1, 1, 1, fan_index))

            varBindsList.append(ValueRepresentation(ValueType.INTEGER, 0, fan_status_oid, fan_status_value))

        # ---------------- PSU ----------------
        elif actualKey.startswith("PSU_INFO|"):
            psu_status_value = self._calc_psu_status(dbEntry)

            # CRITICAL:
            # Only trigger trap on *mapped PSU status* change,
            # not on raw field updates (voltage/temp polling).
            if self.psuTable.get(actualKey) == psu_status_value:
                return None

            self.psuTable[actualKey] = psu_status_value

            returnDict["TrapOid"] = ObjectIdentifier(14, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2))

            key_suffix = actualKey.split("|", 1)[1]
            psu_match = re.search(r"PSU\s*(\d+)", key_suffix, re.IGNORECASE)
            psu_index = int(psu_match.group(1)) if psu_match else 0

            psu_status_oid = ObjectIdentifier(15, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2, psu_index))

            varBindsList.append(ValueRepresentation(ValueType.INTEGER, 0, psu_status_oid, psu_status_value))

        if varBindsList:
            returnDict["varBinds"] = varBindsList
            return returnDict

        return None
