"""
For non-port entity, the rule to generate entPhysicalIndex describes below:
The entPhysicalIndex is divided into 3 layers:
    1. Module layer which includes modules located on system (e.g. fan drawer, PSU)
    2. Device layer which includes system devices (e.g. fan )
    3. Sensor layer which includes system sensors (e.g. temperature sensor, fan sensor)
The entPhysicalIndex is a 9 digits number, and each digit describes below:
Digit 1: Module Type
Digit 2~3: Module Index
Digit 4~5: Device Type
Digit 6~7: Device Index
Digit 8: Sensor Type
Digit 9: Sensor Index

Module Type describes below:
2 - Management
5 - Fan Drawer
6 - PSU
Device Type describes below:
01 - PS
02 - Fan
24 - Power Monitor (temperature, power, current, voltage...)
99 - Chassis Thermals
Sensor Type describes below:
1 - Temperature
2 - Fan Tachometers
3 - Power
4 - Current
5 - Voltage

e.g. 501000000 means the first fan drawer, 502020100 means the first fan of the second fan drawer

As we are using ifindex to generate port entPhysicalIndex and ifindex might be a valur larger 
than 99, we uses a different way to generate port entPhysicalIndex.

For port entity, the entPhysicalIndex is a 10 digits number, and each digit describes below:
Digit 1: 1
Digit 2~8: ifindex
Digit 9: Sensor Type
Digit 10: Sensor Index

Port Sensor Type describes below:
1 - Temperature
2 - TX Power
3 - RX Power
4 - TX BIAS
5 - Voltage
"""

# Moduel Type Definition
MODULE_TYPE_MULTIPLE = 100000000
MODULE_INDEX_MULTIPLE = 1000000
MODULE_TYPE_MGMT = 2 * MODULE_TYPE_MULTIPLE
MODULE_TYPE_FAN_DRAWER = 5 * MODULE_TYPE_MULTIPLE
MODULE_TYPE_PSU = 6 * MODULE_TYPE_MULTIPLE
MODULE_TYPE_PORT = 1000000000

# Device Type Definition
DEVICE_TYPE_MULTIPLE = 10000
DEVICE_INDEX_MULTIPLE = 100
DEVICE_TYPE_PS = 1 * DEVICE_TYPE_MULTIPLE
DEVICE_TYPE_FAN = 2 * DEVICE_TYPE_MULTIPLE
DEVICE_TYPE_CHASSIS_THERMAL = 99 * DEVICE_TYPE_MULTIPLE
DEVICE_TYPE_POWER_MONITOR = 24 * DEVICE_TYPE_MULTIPLE

# Sensor Type Definition
SENSOR_TYPE_MULTIPLE = 10
SENSOR_TYPE_TEMP = 1 * SENSOR_TYPE_MULTIPLE
SENSOR_TYPE_FAN = 2 * SENSOR_TYPE_MULTIPLE
SENSOR_TYPE_POWER = 3 * SENSOR_TYPE_MULTIPLE
SENSOR_TYPE_CURRENT = 4 * SENSOR_TYPE_MULTIPLE
SENSOR_TYPE_VOLTAGE = 5 * SENSOR_TYPE_MULTIPLE

# Port entPhysicalIndex Definition
PORT_IFINDEX_MULTIPLE = 100
SENSOR_TYPE_PORT_TX_POWER = 2 * SENSOR_TYPE_MULTIPLE
SENSOR_TYPE_PORT_RX_POWER = 3 * SENSOR_TYPE_MULTIPLE
SENSOR_TYPE_PORT_TX_BIAS = 4 * SENSOR_TYPE_MULTIPLE

CHASSIS_SUB_ID = 1
CHASSIS_MGMT_SUB_ID = MODULE_TYPE_MGMT

PSU_SENSOR_PART_ID_MAP = {
    'temperature': SENSOR_TYPE_TEMP,
    'power': SENSOR_TYPE_POWER,
    'current': SENSOR_TYPE_CURRENT,
    'voltage': SENSOR_TYPE_VOLTAGE
}

def get_chassis_thermal_sub_id(position):
    """
    Returns sub OID for thermals that belong to chassis. Sub OID is calculated as follows:
    sub OID = CHASSIS_MGMT_SUB_ID + DEVICE_TYPE_CHASSIS_THERMAL + position * DEVICE_INDEX_MULTIPLE + SENSOR_TYPE_TEMP, 
    :param position: thermal position
    :return: sub OID of the thermal
    """
    return (CHASSIS_MGMT_SUB_ID + DEVICE_TYPE_CHASSIS_THERMAL + position * DEVICE_INDEX_MULTIPLE + SENSOR_TYPE_TEMP, )

def get_fan_sub_id(parent_id, position):
    """
    Returns sub OID for fan. Sub OID is calculated as follows:
    sub OID = parent_id[0] + DEVICE_TYPE_FAN + position * DEVICE_INDEX_MULTIPLE
    If parent_id is chassis OID, will use a "virtual" fan drawer OID as its parent_id
    :param parent_id: parent device sub OID
    :param position: fan position
    :return: sub OID of the fan
    """
    if parent_id[0] == CHASSIS_SUB_ID:
        parent_id = MODULE_TYPE_FAN_DRAWER + position * MODULE_INDEX_MULTIPLE
    else:
        parent_id = parent_id[0]
    return (parent_id + DEVICE_TYPE_FAN + position * DEVICE_INDEX_MULTIPLE, )

def get_fan_drawer_sub_id(position):
    """
    Returns sub OID for fan drawer. Sub OID is calculated as follows:
    sub OID = MODULE_TYPE_FAN_DRAWER + position * MODULE_INDEX_MULTIPLE
    :param position: fan drawer position
    :return: sub OID of the fan drawer
    """
    return (MODULE_TYPE_FAN_DRAWER + position * MODULE_INDEX_MULTIPLE, )

def get_fan_tachometers_sub_id(parent_id):
    """
    Returns sub OID for fan tachometers. Sub OID is calculated as follows:
    sub OID = parent_id[0] + SENSOR_TYPE_FAN
    :param parent_id: parent device sub OID
    :return: sub OID of the fan tachometers
    """
    return (parent_id[0] + SENSOR_TYPE_FAN, )

def get_psu_sub_id(position):
    """
    Returns sub OID for PSU. Sub OID is calculated as follows:
    sub OID = MODULE_TYPE_PSU + position * MODULE_INDEX_MULTIPLE
    :param position: PSU position
    :return: sub OID of PSU
    """
    return (MODULE_TYPE_PSU + position * MODULE_INDEX_MULTIPLE, )

def get_psu_sensor_sub_id(parent_id, sensor):
    """
    Returns sub OID for PSU sensor. Sub OID is calculated as follows:
    sub OID = parent_id[0] + DEVICE_TYPE_POWER_MONITOR + PSU_SENSOR_PART_ID_MAP[sensor]
    :param parent_id: PSU oid
    :param sensor: PSU sensor name
    :return: sub OID of PSU sensor
    """
    return (parent_id[0] + DEVICE_TYPE_POWER_MONITOR + PSU_SENSOR_PART_ID_MAP[sensor], )

def get_transceiver_sub_id(ifindex):
    """
    Returns sub OID for transceiver. Sub OID is calculated as folows:
    sub OID = MODULE_TYPE_PORT + ifindex * PORT_IFINDEX_MULTIPLE
    :param ifindex: interface index
    :return: sub OID of a port
    """
    return (MODULE_TYPE_PORT + ifindex * PORT_IFINDEX_MULTIPLE, )

def get_transceiver_sensor_sub_id(ifindex, offset):
    """
    Returns sub OID for transceiver sensor. Sub OID is calculated as folows:
    sub OID = transceiver_oid + offset
    :param ifindex: interface index
    :param offset: sensor OID offset
    :return: sub OID = {{index}} * 1000 + {{lane}} * 10 + sensor id
    """

    transceiver_oid, = get_transceiver_sub_id(ifindex)
    return (transceiver_oid + offset,)

def get_chassis_voltage_sensor_sub_id(position):
    """
    Returns sub OID for voltage sensors that belong to chassis. Sub OID is calculated as follows:
    sub OID = CHASSIS_MGMT_SUB_ID + DEVICE_TYPE_POWER_MONITOR + position * DEVICE_INDEX_MULTIPLE + SENSOR_TYPE_VOLTAGE, 
    :param position: voltage sensor position
    :return: sub OID of the voltage sensor
    """
    return (CHASSIS_MGMT_SUB_ID + DEVICE_TYPE_POWER_MONITOR + position * DEVICE_INDEX_MULTIPLE + SENSOR_TYPE_VOLTAGE, )

def get_chassis_current_sensor_sub_id(position):
    """
    Returns sub OID for current sensors that belong to chassis. Sub OID is calculated as follows:
    sub OID = CHASSIS_MGMT_SUB_ID + DEVICE_TYPE_POWER_MONITOR + position * DEVICE_INDEX_MULTIPLE + SENSOR_TYPE_CURRENT, 
    :param position: current sensor position
    :return: sub OID of the current sensor
    """
    return (CHASSIS_MGMT_SUB_ID + DEVICE_TYPE_POWER_MONITOR + position * DEVICE_INDEX_MULTIPLE + SENSOR_TYPE_CURRENT, )
