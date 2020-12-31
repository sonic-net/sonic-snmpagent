import re

from .physical_entity_sub_oid_generator import SENSOR_TYPE_TEMP
from .physical_entity_sub_oid_generator import SENSOR_TYPE_PORT_TX_POWER
from .physical_entity_sub_oid_generator import SENSOR_TYPE_PORT_RX_POWER
from .physical_entity_sub_oid_generator import SENSOR_TYPE_PORT_TX_BIAS
from .physical_entity_sub_oid_generator import SENSOR_TYPE_VOLTAGE


class TransceiverSensorData:
    """
    Base transceiver sensor data class. Responsible for:
        1. Manage concrete sensor data class
        2. Create concrete sensor data instances
        3. Provide common logic for concrete sensor data class
    """

    sensor_attr_dict = {
        'temperature': {
            'pattern': 'temperature',
            'name': 'Temperature',
            'oid_offset_base': SENSOR_TYPE_TEMP,
            'sort_factor': 0,
            'lane_based_sensor': False
        },
        'voltage': {
            'pattern': 'voltage',
            'name': 'Voltage',
            'oid_offset_base': SENSOR_TYPE_VOLTAGE,
            'sort_factor': 9000,
            'lane_based_sensor': False
        },
        'rxpower': {
            'pattern': r'rx(\d+)power',
            'name': 'RX Power',
            'oid_offset_base': SENSOR_TYPE_PORT_RX_POWER,
            'sort_factor': 2000,
            'lane_based_sensor': True
        },
        'txpower': {
            'pattern': r'tx(\d+)power',
            'name': 'TX Power',
            'oid_offset_base': SENSOR_TYPE_PORT_TX_POWER,
            'sort_factor': 1000,
            'lane_based_sensor': True
        },
        'txbias': {
            'pattern': r'tx(\d+)bias',
            'name': 'TX Bias',
            'oid_offset_base': SENSOR_TYPE_PORT_TX_BIAS,
            'sort_factor': 3000,
            'lane_based_sensor': True
        }
    }

    def __init__(self, key, value, sensor_attrs, match_result):
        self._key = key
        self._value = value
        self._sensor_attrs = sensor_attrs
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
            for sensor_attrs in cls.sensor_attr_dict.values():
                match_result = re.match(sensor_attrs['pattern'], name)
                if match_result:
                    sensor_data = TransceiverSensorData(name, value, sensor_attrs, match_result)
                    sensor_data_list.append(sensor_data)

        return sensor_data_list

    @classmethod
    def sort_sensor_data(cls, sensor_data_list):
        return sorted(sensor_data_list, key=lambda x: x.get_sort_factor())

    @classmethod
    def bind_sensor_interface(cls, sensor_interface_dict):
        for name, sensor_attrs in cls.sensor_attr_dict.items():
            if name in sensor_interface_dict:
                sensor_attrs['sensor_interface'] = sensor_interface_dict[name]

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
        return self._sensor_attrs['name']

    def get_sort_factor(self):
        """
        Get sort factor for this sensor. Concrete sensor data class must override
        this.
        """
        return self._sensor_attrs['sort_factor'] + self.get_lane_number()

    def get_lane_number(self):
        """
        Get lane number of this sensor. For example, some transceivers have more than one rx power sensor, the sub index
        of rx1power is 1, the sub index of rx2power is 2.
        """
        return int(self._match_result.group(1)) if self._sensor_attrs['lane_based_sensor'] else 0

    def get_oid_offset(self):
        """
        Get OID offset of this sensor.
        """
        return self._sensor_attrs['oid_offset_base'] + self.get_lane_number()

    def get_sensor_interface(self):
        """
        Get sensor interface of this sensor. Used by rfc3433.
        """
        return self._sensor_attrs['sensor_interface']
