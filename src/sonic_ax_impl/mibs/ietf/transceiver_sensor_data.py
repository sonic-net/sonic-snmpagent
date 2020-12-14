import re

from .physical_entity_sub_oid_generator import SENSOR_TYPE_TEMP
from .physical_entity_sub_oid_generator import SENSOR_TYPE_PORT_TX_POWER
from .physical_entity_sub_oid_generator import SENSOR_TYPE_PORT_RX_POWER
from .physical_entity_sub_oid_generator import SENSOR_TYPE_PORT_TX_BIAS
from .physical_entity_sub_oid_generator import SENSOR_TYPE_VOLTAGE


def transceiver_sensor_data():
    """
    Decorator for auto registering transceiver sensor data type
    """
    def wrapper(object_type):
        TransceiverSensorData.register(object_type)
        return object_type

    return wrapper


class TransceiverSensorData:
    """
    Base transceiver sensor data class. Responsible for:
        1. Manage concrete sensor data class
        2. Create concrete sensor data instances
        3. Provide common logic for concrete sensor data class
    """
    concrete_type_list = []
    sensor_interface = None

    def __init__(self, key, value, match_result):
        self._key = key
        self._value = value
        self._match_result = match_result

    @classmethod
    def create_sensor_data(cls, sensor_data_dict):
        """
        Create sensor data instances according to the sensor data got from redis
        :param sensor_data_dict: sensor data got from redis
        :return: A sorted sensor data instance list
        """
        sensor_data_list = []
        for name, value in sensor_data_dict.items():
            for concrete_type in cls.concrete_type_list:
                match_result = re.match(concrete_type.get_pattern(), name)
                if match_result:
                    sensor_data = concrete_type(name, value, match_result)
                    sensor_data_list.append(sensor_data)
                    break
        return sensor_data_list

    @classmethod
    def sort_sensor_data(cls, sensor_data_list):
        return sorted(sensor_data_list, key=lambda x: x.get_sort_factor())

    @classmethod
    def register(cls, concrete_type):
        """
        Register concrete sensor data type
        :param concrete_type: concrete sensor data class
        :return:
        """
        cls.concrete_type_list.append(concrete_type)

    @classmethod
    def bind_sensor_interface(cls, sensor_interface_dict):
        for concrete_type in cls.concrete_type_list:
            if concrete_type in sensor_interface_dict:
                concrete_type.sensor_interface = sensor_interface_dict[concrete_type]

    def get_key(self):
        """
        Get the redis key of this sensor
        """
        return self._key

    def get_raw_value(self):
        """
        Get raw redis value of this sensor
        """
        return self._value

    def get_name(self):
        """
        Get the name of this sensor. Concrete sensor data class must override
        this.
        """
        raise NotImplementedError

    def get_sort_factor(self):
        """
        Get sort factor for this sensor. Concrete sensor data class must override
        this.
        """
        raise NotImplementedError

    def get_lane_number(self):
        """
        Get lane number of this sensor. For example, some transceivers have more than one rx power sensor, the sub index
        of rx1power is 1, the sub index of rx2power is 2.
        """
        return int(self._match_result.group(1))

    def get_oid_offset(self):
        """
        Get OID offset of this sensor.
        """
        raise NotImplementedError

    @classmethod
    def get_pattern(cls):
        """
        Return regular expression pattern for matching the sensor name. Concrete sensor data class must override
        this.
        """
        raise NotImplementedError


@transceiver_sensor_data()
class TransceiverTempSensorData(TransceiverSensorData):
    SORT_FACTOR = 0

    @classmethod
    def get_pattern(cls):
        return 'temperature'

    def get_name(self):
        return 'Temperature'

    def get_sort_factor(self):
        return TransceiverTempSensorData.SORT_FACTOR

    def get_lane_number(self):
        return 0

    def get_oid_offset(self):
        return SENSOR_TYPE_TEMP


@transceiver_sensor_data()
class TransceiverVoltageSensorData(TransceiverSensorData):
    SORT_FACTOR = 9000

    @classmethod
    def get_pattern(cls):
        return 'voltage'

    def get_name(self):
        return 'Voltage'

    def get_sort_factor(self):
        return TransceiverVoltageSensorData.SORT_FACTOR

    def get_lane_number(self):
        return 0

    def get_oid_offset(self):
        return SENSOR_TYPE_VOLTAGE


@transceiver_sensor_data()
class TransceiverRxPowerSensorData(TransceiverSensorData):
    SORT_FACTOR = 2000

    @classmethod
    def get_pattern(cls):
        return 'rx(\d+)power'

    def get_name(self):
        return 'RX Power'

    def get_sort_factor(self):
        return TransceiverRxPowerSensorData.SORT_FACTOR + self.get_lane_number()

    def get_oid_offset(self):
        return SENSOR_TYPE_PORT_RX_POWER + self.get_lane_number()


@transceiver_sensor_data()
class TransceiverTxPowerSensorData(TransceiverSensorData):
    SORT_FACTOR = 1000

    @classmethod
    def get_pattern(cls):
        return 'tx(\d+)power'

    def get_name(self):
        return 'TX Power'

    def get_sort_factor(self):
        return TransceiverTxPowerSensorData.SORT_FACTOR + self.get_lane_number()

    def get_oid_offset(self):
        return SENSOR_TYPE_PORT_TX_POWER + self.get_lane_number()


@transceiver_sensor_data()
class TransceiverTxBiasSensorData(TransceiverSensorData):
    SORT_FACTOR = 3000

    @classmethod
    def get_pattern(cls):
        return 'tx(\d+)bias'

    def get_name(self):
        return 'TX Bias'

    def get_sort_factor(self):
        return TransceiverTxBiasSensorData.SORT_FACTOR + self.get_lane_number()

    def get_oid_offset(self):
        return SENSOR_TYPE_PORT_TX_BIAS + self.get_lane_number()
