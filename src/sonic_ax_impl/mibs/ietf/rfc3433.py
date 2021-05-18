"""
RFC 3433 MIB implementation
"""

from enum import Enum, unique
from bisect import bisect_right

from swsssdk import port_util
from ax_interface import MIBMeta, MIBUpdater, ValueType, SubtreeMIBEntry
from sonic_ax_impl import mibs
from sonic_ax_impl.mibs import HOST_NAMESPACE_DB_IDX
from sonic_ax_impl.mibs import Namespace
from .physical_entity_sub_oid_generator import CHASSIS_SUB_ID
from .physical_entity_sub_oid_generator import get_transceiver_sensor_sub_id
from .physical_entity_sub_oid_generator import get_fan_drawer_sub_id
from .physical_entity_sub_oid_generator import get_fan_sub_id
from .physical_entity_sub_oid_generator import get_fan_tachometers_sub_id
from .physical_entity_sub_oid_generator import get_psu_sub_id
from .physical_entity_sub_oid_generator import get_psu_sensor_sub_id
from .physical_entity_sub_oid_generator import get_chassis_thermal_sub_id
from .sensor_data import ThermalSensorData, FANSensorData, PSUSensorData, TransceiverSensorData

NOT_AVAILABLE = 'N/A'
CHASSIS_NAME_SUB_STRING = 'chassis'
PSU_NAME_SUB_STRING = 'PSU'


def is_null_empty_str(value):
    """
    Indicate if a string value is null
    :param value: input string value
    :return: True is string value is empty or equal to 'N/A' or 'None'
    """
    if not isinstance(value, str) or value == NOT_AVAILABLE or value == 'None' or value == '':
        return True
    return False


def get_db_data(info_dict, enum_type):
    """
    :param info_dict: db info dict
    :param enum_type: db field enum
    :return: tuple of fields values defined in enum_type;
    Empty string if field not in info_dict
    """
    return (info_dict.get(field.value, "")
            for field in enum_type)


@unique
class PhysicalRelationInfoDB(str, Enum):
    """
    Physical relation info keys
    """
    POSITION_IN_PARENT    = 'position_in_parent'
    PARENT_NAME           = 'parent_name'


@unique
class EntitySensorDataType(int, Enum):
    """
    Enumeration of sensor data types according to RFC3433
    (https://tools.ietf.org/html/rfc3433)
    """

    OTHER      = 1
    UNKNOWN    = 2
    VOLTS_AC   = 3
    VOLTS_DC   = 4
    AMPERES    = 5
    WATTS      = 6
    HERTZ      = 7
    CELSIUS    = 8
    PERCENT_RH = 9
    RPM        = 10
    CMM        = 11
    TRUTHVALUE = 12


@unique
class EntitySensorDataScale(int, Enum):
    """
    Enumeration of sensor data scale types according to RFC3433
    (https://tools.ietf.org/html/rfc3433)
    """

    YOCTO = 1
    ZEPTO = 2
    ATTO  = 3
    FEMTO = 4
    PICO  = 5
    NANO  = 6
    MICRO = 7
    MILLI = 8
    UNITS = 9
    KILO  = 10
    MEGA  = 11
    GIGA  = 12
    TERA  = 13
    EXA   = 14
    PETA  = 15
    ZETTA = 16
    YOTTA = 17


@unique
class EntitySensorStatus(int, Enum):
    """
    Enumeration of sensor operational status according to RFC3433
    (https://tools.ietf.org/html/rfc3433)
    """

    OK             = 1
    UNAVAILABLE    = 2
    NONOPERATIONAL = 3


@unique
class EntitySensorValueRange(int, Enum):
    """
    Range of EntitySensorValue field defined by RFC 3433
    """

    MIN = -1E9
    MAX = 1E9


class Converters:
    """ """

    # dBm to milli watts converter function
    CONV_dBm_mW = lambda x: 10 ** (x/10)


class SensorInterface:
    """
    Sensor interface.
    Sensor should define SCALE, TYPE, PRECISION
    """

    SCALE = None
    TYPE = None
    PRECISION = None
    CONVERTER = None

    @classmethod
    def mib_values(cls, raw_value):
        """
        :param: cls: class instance
        :param: value: sensor's value as is from DB
        :param: converter: optional converter for a value in case it
        is needed to convert value from one unit to another
        :return: value converted for MIB
        """

        type_ = cls.TYPE
        scale = cls.SCALE
        precision = cls.PRECISION

        try:
            value = float(raw_value)
        except ValueError:
            # if raw_value is not able to be parsed as a float
            # the operational status of sensor is
            # considered to be UNAVAILABLE

            # since sensor is unavailable
            # vlaue can be 0
            value = 0
            oper_status = EntitySensorStatus.UNAVAILABLE
        else:
            # else the status is considered to be OK
            oper_status = EntitySensorStatus.OK

            # convert if converter is defined
            if cls.CONVERTER:
                value = cls.CONVERTER(value)

            value = value * 10 ** precision
            if value > EntitySensorValueRange.MAX:
                value = EntitySensorValueRange.MAX
            elif value < EntitySensorValueRange.MIN:
                value = EntitySensorValueRange.MIN
            else:
                # round the value to integer
                value = round(value)

        return type_, scale, precision, value, oper_status


class XcvrTempSensor(SensorInterface):
    """
    Transceiver temperature sensor.
    (TYPE, SCALE, PRECISION) set according to SFF-8472
    Sensor measures in range (-128, 128) Celsium degrees
    with step equals 1/256 degree
    """

    TYPE = EntitySensorDataType.CELSIUS
    SCALE = EntitySensorDataScale.UNITS
    PRECISION = 6


class XcvrVoltageSensor(SensorInterface):
    """
    Transceiver voltage sensor.
    (TYPE, SCALE, PRECISION) set according to SFF-8472
    Sensor measures in range (0 V, +6.55 V) with step 1E-4 V
    """

    TYPE = EntitySensorDataType.VOLTS_DC
    SCALE = EntitySensorDataScale.UNITS
    PRECISION = 4


class XcvrRxPowerSensor(SensorInterface):
    """
    Transceiver rx power sensor.
    (TYPE, SCALE, PRECISION) set according to SFF-8472
    Sensor measures in range (0 W, +6.5535 mW) with step 1E-4 mW.
    """

    TYPE = EntitySensorDataType.WATTS
    SCALE = EntitySensorDataScale.MILLI
    PRECISION = 4
    CONVERTER = Converters.CONV_dBm_mW


class XcvrTxBiasSensor(SensorInterface):
    """
    Transceiver tx bias sensor.
    (TYPE, SCALE, PRECISION) set according to SFF-8472
    Sensor measures in range (0 mA, 131 mA) with step 2E-3 mA
    """

    TYPE = EntitySensorDataType.AMPERES
    SCALE = EntitySensorDataScale.MILLI
    PRECISION = 3


class XcvrTxPowerSensor(SensorInterface):
    """
    Transceiver tx power sensor.
    (TYPE, SCALE, PRECISION) set according to SFF-8472
    Sensor measures in range (0 W, +6.5535 mW) with step 1E-4 mW.
    """

    TYPE = EntitySensorDataType.WATTS
    SCALE = EntitySensorDataScale.MILLI
    PRECISION = 4
    CONVERTER = Converters.CONV_dBm_mW


TransceiverSensorData.bind_sensor_interface({
    'temperature': XcvrTempSensor,
    'voltage'    : XcvrVoltageSensor,
    'rxpower'    : XcvrRxPowerSensor,
    'txpower'    : XcvrTxPowerSensor,
    'txbias'     : XcvrTxBiasSensor
})


class PSUTempSensor(SensorInterface):
    """
    PSU temperature sensor.
    """

    TYPE = EntitySensorDataType.CELSIUS
    SCALE = EntitySensorDataScale.UNITS
    PRECISION = 3


class PSUVoltageSensor(SensorInterface):
    """
    PSU voltage sensor.
    """

    TYPE = EntitySensorDataType.VOLTS_DC
    SCALE = EntitySensorDataScale.UNITS
    PRECISION = 3


class PSUCurrentSensor(SensorInterface):
    """
    PSU current sensor.
    """

    TYPE = EntitySensorDataType.AMPERES
    SCALE = EntitySensorDataScale.UNITS
    PRECISION = 3


class PSUPowerSensor(SensorInterface):
    """
    PSU power sensor.
    """

    TYPE = EntitySensorDataType.WATTS
    SCALE = EntitySensorDataScale.UNITS
    PRECISION = 3


PSUSensorData.bind_sensor_interface({
    'temperature': PSUTempSensor,
    'voltage'    : PSUVoltageSensor,
    'power'      : PSUPowerSensor,
    'current'    : PSUCurrentSensor
})


class FANSpeedSensor(SensorInterface):
    """
    FAN speed sensor.
    """

    TYPE = EntitySensorDataType.UNKNOWN
    SCALE = EntitySensorDataScale.UNITS
    PRECISION = 0


FANSensorData.bind_sensor_interface({
    'speed': FANSpeedSensor
})


class ThermalSensor(SensorInterface):
    """
    Temperature sensor.
    """

    TYPE = EntitySensorDataType.CELSIUS
    SCALE = EntitySensorDataScale.UNITS
    PRECISION = 3


ThermalSensorData.bind_sensor_interface({
    'temperature': ThermalSensor
})


class PhysicalSensorTableMIBUpdater(MIBUpdater):
    """
    Updater for sensors.
    """

    TRANSCEIVER_DOM_KEY_PATTERN = mibs.transceiver_dom_table("*")
    PSU_SENSOR_KEY_PATTERN = mibs.psu_info_table("*")
    FAN_SENSOR_KEY_PATTERN = mibs.fan_info_table("*")
    THERMAL_SENSOR_KEY_PATTERN = mibs.thermal_info_table("*")

    def __init__(self):
        """
        ctor
        """

        super().__init__()

        self.statedb = Namespace.init_namespace_dbs()
        Namespace.connect_all_dbs(self.statedb, mibs.STATE_DB)

        # list of available sub OIDs
        self.sub_ids = []

        # sensor MIB required values
        self.ent_phy_sensor_type_map = {}
        self.ent_phy_sensor_scale_map = {}
        self.ent_phy_sensor_precision_map = {}
        self.ent_phy_sensor_value_map = {}
        self.ent_phy_sensor_oper_state_map = {}

        self.transceiver_dom = []
        self.fan_sensor = []
        self.psu_sensor = []
        self.thermal_sensor = []

    def reinit_data(self):
        """
        Reinit data, clear cache
        """

        # clear cache
        self.ent_phy_sensor_type_map = {}
        self.ent_phy_sensor_scale_map = {}
        self.ent_phy_sensor_precision_map = {}
        self.ent_phy_sensor_value_map = {}
        self.ent_phy_sensor_oper_state_map = {}

        transceiver_dom_encoded = Namespace.dbs_keys(self.statedb, mibs.STATE_DB, self.TRANSCEIVER_DOM_KEY_PATTERN)
        if transceiver_dom_encoded:
            self.transceiver_dom = [entry for entry in transceiver_dom_encoded]

        # for FAN, PSU and thermal sensors, they are in host namespace DB, to avoid iterating all namespace DBs,
        # just get data from host namespace DB, which is self.statedb[0].
        fan_sensor_encoded = self.statedb[HOST_NAMESPACE_DB_IDX].keys(self.statedb[HOST_NAMESPACE_DB_IDX].STATE_DB,
                                                                      self.FAN_SENSOR_KEY_PATTERN)
        if fan_sensor_encoded:
            self.fan_sensor = [entry for entry in fan_sensor_encoded]

        psu_sensor_encoded = self.statedb[HOST_NAMESPACE_DB_IDX].keys(self.statedb[HOST_NAMESPACE_DB_IDX].STATE_DB,
                                                                      self.PSU_SENSOR_KEY_PATTERN)
        if psu_sensor_encoded:
            self.psu_sensor = [entry for entry in psu_sensor_encoded]

        thermal_sensor_encoded = self.statedb[HOST_NAMESPACE_DB_IDX].keys(self.statedb[HOST_NAMESPACE_DB_IDX].STATE_DB,
                                                                          self.THERMAL_SENSOR_KEY_PATTERN)
        if thermal_sensor_encoded:
            self.thermal_sensor = [entry for entry in thermal_sensor_encoded]

    def update_xcvr_dom_data(self):
        if not self.transceiver_dom:
            return

        # update transceiver sensors cache
        for transceiver_dom_entry in self.transceiver_dom:
            # extract interface name
            interface = transceiver_dom_entry.split(mibs.TABLE_NAME_SEPARATOR_VBAR)[-1]
            ifindex = port_util.get_index_from_str(interface)

            if ifindex is None:
                mibs.logger.warning(
                    "Invalid interface name in {} \
                     in STATE_DB, skipping".format(transceiver_dom_entry))
                continue

            # get transceiver sensors from transceiver dom entry in STATE DB
            transceiver_dom_entry_data = Namespace.dbs_get_all(self.statedb, mibs.STATE_DB, transceiver_dom_entry)

            if not transceiver_dom_entry_data:
                continue

            sensor_data_list = TransceiverSensorData.create_sensor_data(transceiver_dom_entry_data)
            for sensor_data in sensor_data_list:
                raw_sensor_value = sensor_data.get_raw_value()
                sensor = sensor_data.get_sensor_interface()
                sub_id = get_transceiver_sensor_sub_id(ifindex, sensor_data.get_oid_offset())

                try:
                    mib_values = sensor.mib_values(raw_sensor_value)
                except (ValueError, ArithmeticError):
                    mibs.logger.error("Exception occurred when converting"
                                      "value for sensor {} interface {}".format(sensor, interface))
                    continue
                else:
                    self.ent_phy_sensor_type_map[sub_id], \
                        self.ent_phy_sensor_scale_map[sub_id], \
                        self.ent_phy_sensor_precision_map[sub_id], \
                        self.ent_phy_sensor_value_map[sub_id], \
                        self.ent_phy_sensor_oper_state_map[sub_id] = mib_values

                    self.sub_ids.append(sub_id)

    def update_psu_sensor_data(self):
        if not self.psu_sensor:
            return

        for psu_sensor_entry in self.psu_sensor:
            psu_name = psu_sensor_entry.split(mibs.TABLE_NAME_SEPARATOR_VBAR)[-1]
            psu_relation_info = self.statedb[HOST_NAMESPACE_DB_IDX].get_all(
                self.statedb[HOST_NAMESPACE_DB_IDX].STATE_DB, mibs.physical_entity_info_table(psu_name))
            psu_position, psu_parent_name = get_db_data(psu_relation_info, PhysicalRelationInfoDB)
            if is_null_empty_str(psu_position):
                continue
            psu_position = int(psu_position)
            psu_sub_id = get_psu_sub_id(psu_position)

            psu_sensor_entry_data = self.statedb[HOST_NAMESPACE_DB_IDX].get_all(
                self.statedb[HOST_NAMESPACE_DB_IDX].STATE_DB, psu_sensor_entry)

            if not psu_sensor_entry_data:
                continue

            sensor_data_list = PSUSensorData.create_sensor_data(psu_sensor_entry_data)
            for sensor_data in sensor_data_list:
                raw_sensor_value = sensor_data.get_raw_value()
                if is_null_empty_str(raw_sensor_value):
                    continue
                sensor = sensor_data.get_sensor_interface()
                sub_id = get_psu_sensor_sub_id(psu_sub_id, sensor_data.get_name().lower())

                try:
                    mib_values = sensor.mib_values(raw_sensor_value)
                except (ValueError, ArithmeticError):
                    mibs.logger.error("Exception occurred when converting"
                                      "value for sensor {} PSU {}".format(sensor, psu_name))
                    continue
                else:
                    self.ent_phy_sensor_type_map[sub_id], \
                        self.ent_phy_sensor_scale_map[sub_id], \
                        self.ent_phy_sensor_precision_map[sub_id], \
                        self.ent_phy_sensor_value_map[sub_id], \
                        self.ent_phy_sensor_oper_state_map[sub_id] = mib_values

                    self.sub_ids.append(sub_id)

    def update_fan_sensor_data(self):
        if not self.fan_sensor:
            return

        fan_parent_sub_id = 0
        for fan_sensor_entry in self.fan_sensor:
            fan_name = fan_sensor_entry.split(mibs.TABLE_NAME_SEPARATOR_VBAR)[-1]
            fan_relation_info = self.statedb[HOST_NAMESPACE_DB_IDX].get_all(
                self.statedb[HOST_NAMESPACE_DB_IDX].STATE_DB, mibs.physical_entity_info_table(fan_name))
            fan_position, fan_parent_name = get_db_data(fan_relation_info, PhysicalRelationInfoDB)
            if is_null_empty_str(fan_position):
                continue

            fan_position = int(fan_position)

            if CHASSIS_NAME_SUB_STRING in fan_parent_name:
                fan_parent_sub_id = (CHASSIS_SUB_ID,)
            else:
                fan_parent_relation_info = self.statedb[HOST_NAMESPACE_DB_IDX].get_all(
                    self.statedb[HOST_NAMESPACE_DB_IDX].STATE_DB, mibs.physical_entity_info_table(fan_parent_name))
                if fan_parent_relation_info:
                    fan_parent_position, fan_grad_parent_name = get_db_data(fan_parent_relation_info,
                                                                            PhysicalRelationInfoDB)

                    fan_parent_position = int(fan_parent_position)

                    if PSU_NAME_SUB_STRING in fan_parent_name:
                        fan_parent_sub_id = get_psu_sub_id(fan_parent_position)
                    else:
                        fan_parent_sub_id = get_fan_drawer_sub_id(fan_parent_position)
                else:
                    mibs.logger.error("fan_name = {} get fan parent failed".format(fan_name))
                    continue

            fan_sub_id = get_fan_sub_id(fan_parent_sub_id, fan_position)

            fan_sensor_entry_data = self.statedb[HOST_NAMESPACE_DB_IDX].get_all(
                self.statedb[HOST_NAMESPACE_DB_IDX].STATE_DB, fan_sensor_entry)

            if not fan_sensor_entry_data:
                mibs.logger.error("fan_name = {} get fan_sensor_entry_data failed".format(fan_name))
                continue

            sensor_data_list = FANSensorData.create_sensor_data(fan_sensor_entry_data)
            for sensor_data in sensor_data_list:
                raw_sensor_value = sensor_data.get_raw_value()
                if is_null_empty_str(raw_sensor_value):
                    continue
                sensor = sensor_data.get_sensor_interface()
                sub_id = get_fan_tachometers_sub_id(fan_sub_id)

                try:
                    mib_values = sensor.mib_values(raw_sensor_value)
                except (ValueError, ArithmeticError):
                    mibs.logger.error("Exception occurred when converting"
                                      "value for sensor {} PSU {}".format(sensor, fan_name))
                    continue
                else:
                    self.ent_phy_sensor_type_map[sub_id], \
                        self.ent_phy_sensor_scale_map[sub_id], \
                        self.ent_phy_sensor_precision_map[sub_id], \
                        self.ent_phy_sensor_value_map[sub_id], \
                        self.ent_phy_sensor_oper_state_map[sub_id] = mib_values

                    self.sub_ids.append(sub_id)

    def update_thermal_sensor_data(self):
        if not self.thermal_sensor:
            return

        for thermal_sensor_entry in self.thermal_sensor:
            thermal_name = thermal_sensor_entry.split(mibs.TABLE_NAME_SEPARATOR_VBAR)[-1]
            thermal_relation_info = self.statedb[HOST_NAMESPACE_DB_IDX].get_all(
                self.statedb[HOST_NAMESPACE_DB_IDX].STATE_DB, mibs.physical_entity_info_table(thermal_name))
            thermal_position, thermal_parent_name = get_db_data(thermal_relation_info, PhysicalRelationInfoDB)

            if is_null_empty_str(thermal_parent_name) or is_null_empty_str(thermal_parent_name) or \
                    CHASSIS_NAME_SUB_STRING not in thermal_parent_name.lower():
                continue

            thermal_position = int(thermal_position)

            thermal_sensor_entry_data = self.statedb[HOST_NAMESPACE_DB_IDX].get_all(
                self.statedb[HOST_NAMESPACE_DB_IDX].STATE_DB, thermal_sensor_entry)

            if not thermal_sensor_entry_data:
                continue

            sensor_data_list = ThermalSensorData.create_sensor_data(thermal_sensor_entry_data)
            for sensor_data in sensor_data_list:
                raw_sensor_value = sensor_data.get_raw_value()
                if is_null_empty_str(raw_sensor_value):
                    continue
                sensor = sensor_data.get_sensor_interface()
                sub_id = get_chassis_thermal_sub_id(thermal_position)

                try:
                    mib_values = sensor.mib_values(raw_sensor_value)
                except (ValueError, ArithmeticError):
                    mibs.logger.error("Exception occurred when converting"
                                      "value for sensor {} PSU {}".format(sensor, thermal_name))
                    continue
                else:
                    self.ent_phy_sensor_type_map[sub_id], \
                        self.ent_phy_sensor_scale_map[sub_id], \
                        self.ent_phy_sensor_precision_map[sub_id], \
                        self.ent_phy_sensor_value_map[sub_id], \
                        self.ent_phy_sensor_oper_state_map[sub_id] = mib_values

                    self.sub_ids.append(sub_id)

    def update_data(self):
        """
        Update sensors cache.
        """

        self.sub_ids = []

        self.update_xcvr_dom_data()
        
        self.update_psu_sensor_data()

        self.update_fan_sensor_data()

        self.update_thermal_sensor_data()

        self.sub_ids.sort()

    def get_next(self, sub_id):
        """
        :param sub_id: Input sub_id.
        :return: The next sub id.
        """

        right = bisect_right(self.sub_ids, sub_id)
        if right == len(self.sub_ids):
            return None
        return self.sub_ids[right]

    def get_ent_physical_sensor_type(self, sub_id):
        """
        Get sensor type based on sub OID
        :param sub_id: sub ID of the sensor
        :return: sensor type from EntitySensorDataType enum
                 or None if sub_id not in the cache.
        """

        if sub_id in self.sub_ids:
            return self.ent_phy_sensor_type_map.get(sub_id, EntitySensorDataType.UNKNOWN)
        return None

    def get_ent_physical_sensor_scale(self, sub_id):

        """
        Get sensor scale value based on sub OID
        :param sub_id: sub ID of the sensor
        :return: sensor scale from EntitySensorDataScale enum
                 or None if sub_id not in the cache.
        """

        if sub_id in self.sub_ids:
            return self.ent_phy_sensor_scale_map.get(sub_id, 0)
        return None

    def get_ent_physical_sensor_precision(self, sub_id):
        """
        Get sensor precision value based on sub OID
        :param sub_id: sub ID of the sensor
        :return: sensor precision in range (-8, 9)
                 or None if sub_id not in the cache.
        """

        if sub_id in self.sub_ids:
            return self.ent_phy_sensor_precision_map.get(sub_id, 0)
        return None

    def get_ent_physical_sensor_value(self, sub_id):
        """
        Get sensor value based on sub OID
        :param sub_id: sub ID of the sensor
        :return: sensor value converted according to tuple (type, scale, precision)
        """

        if sub_id in self.sub_ids:
            return self.ent_phy_sensor_value_map.get(sub_id, 0)
        return None

    def get_ent_physical_sensor_oper_status(self, sub_id):
        """
        Get sensor operational state based on sub OID
        :param sub_id: sub ID of the sensor
        :return: sensor's operational state
        """

        if sub_id in self.sub_ids:
            return self.ent_phy_sensor_oper_state_map.get(sub_id, EntitySensorStatus.UNAVAILABLE)
        return None


class PhysicalSensorTableMIB(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.99.1.1'):
    """
    Sensor table.
    """

    updater = PhysicalSensorTableMIBUpdater()

    entPhySensorType = \
        SubtreeMIBEntry('1.1', updater, ValueType.INTEGER, updater.get_ent_physical_sensor_type)

    entPhySensorScale = \
        SubtreeMIBEntry('1.2', updater, ValueType.INTEGER, updater.get_ent_physical_sensor_scale)

    entPhySensorPrecision = \
        SubtreeMIBEntry('1.3', updater, ValueType.INTEGER, updater.get_ent_physical_sensor_precision)

    entPhySensorValue = \
        SubtreeMIBEntry('1.4', updater, ValueType.INTEGER, updater.get_ent_physical_sensor_value)

    entPhySensorStatus = \
        SubtreeMIBEntry('1.5', updater, ValueType.INTEGER, updater.get_ent_physical_sensor_oper_status)

