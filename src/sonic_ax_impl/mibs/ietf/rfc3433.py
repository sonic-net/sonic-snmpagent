"""
RFC 3433 MIB implementation
"""

from enum import Enum, unique
from bisect import bisect_right

from swsssdk import port_util
from ax_interface import MIBMeta, MIBUpdater, ValueType, SubtreeMIBEntry
from sonic_ax_impl import mibs
from sonic_ax_impl.mibs import Namespace

from .physical_entity_sub_oid_generator import get_transceiver_sensor_sub_id
from .transceiver_sensor_data import TransceiverSensorData


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


class PhysicalSensorTableMIBUpdater(MIBUpdater):
    """
    Updater for sensors.
    """

    TRANSCEIVER_DOM_KEY_PATTERN = mibs.transceiver_dom_table("*")

    def __init__(self):
        """
        ctor
        """

        super().__init__()

        self.statedb = Namespace.init_namespace_dbs()
        Namespace.connect_all_dbs(self.statedb, mibs.STATE_DB)

        # list of available sub OIDs
        self.sub_ids = []

        # sensor MIB requiered values
        self.ent_phy_sensor_type_map = {}
        self.ent_phy_sensor_scale_map = {}
        self.ent_phy_sensor_precision_map = {}
        self.ent_phy_sensor_value_map = {}
        self.ent_phy_sensor_oper_state_map = {}

        self.transceiver_dom = []

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

        transceiver_dom_encoded = Namespace.dbs_keys(self.statedb, mibs.STATE_DB,
                                                    self.TRANSCEIVER_DOM_KEY_PATTERN)
        if transceiver_dom_encoded:
            self.transceiver_dom = [entry for entry in transceiver_dom_encoded]

    def update_data(self):
        """
        Update sensors cache.
        """

        self.sub_ids = []

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
            transceiver_dom_entry_data = Namespace.dbs_get_all(self.statedb, mibs.STATE_DB,
                                                              transceiver_dom_entry)

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
                    mibs.logger.error("Exception occured when converting"
                                      "value for sensor {} interface {}".format(sensor, interface))
                    # skip
                    continue
                else:
                    self.ent_phy_sensor_type_map[sub_id], \
                    self.ent_phy_sensor_scale_map[sub_id], \
                    self.ent_phy_sensor_precision_map[sub_id], \
                    self.ent_phy_sensor_value_map[sub_id], \
                    self.ent_phy_sensor_oper_state_map[sub_id] = mib_values

                    self.sub_ids.append(sub_id)

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

