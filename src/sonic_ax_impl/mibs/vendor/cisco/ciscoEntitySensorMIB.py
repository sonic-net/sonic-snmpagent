from .cisco_sensor_threshold import CiscoPhysicalSensorThretholdTableMIBUpdater
from .cisco_sensor_value import CiscoValuePhysicalSensorTableMIBUpdater
from ax_interface import MIBMeta, MIBUpdater, ValueType, SubtreeMIBEntry



class CiscoPhysicalSensorThresholdMIB(metaclass=MIBMeta, prefix='.1.3.6.1.4.1.9.9.91.1.2.1'): 
    """
    Sensor thresholds table.
    """
    
    updater = CiscoPhysicalSensorThretholdTableMIBUpdater()

    entSensorHighThresholdSeverity = \
        SubtreeMIBEntry('1.2.1', updater, ValueType.INTEGER, updater.get_high_sensors_severity)
    
    entSensorLowThresholdSeverity = \
        SubtreeMIBEntry('1.2.2', updater, ValueType.INTEGER, updater.get_low_sensors_severity)

    
    entSensorHighThresholdRelation = \
        SubtreeMIBEntry('1.3.1', updater, ValueType.INTEGER, updater.get_high_sensors_relation)
        
    entSensorLowThresholdRelation = \
        SubtreeMIBEntry('1.3.2', updater, ValueType.INTEGER, updater.get_low_sensors_relation)
    
    entSensorHighThresholdValue = \
        SubtreeMIBEntry('1.4.1', updater, ValueType.OCTET_STRING, updater.get_high_sensors_threshold)
        
    entSensorLowThresholdValue = \
        SubtreeMIBEntry('1.4.2', updater, ValueType.OCTET_STRING, updater.get_low_sensors_threshold)
    
    entSensorHighThresholdEvaluation = \
        SubtreeMIBEntry('1.5.1', updater, ValueType.INTEGER, updater.get_high_sensors_evaluation)
        
    entSensorLowThresholdEvaluation = \
        SubtreeMIBEntry('1.5.2', updater, ValueType.INTEGER, updater.get_low_sensors_evaluation)
    
    entSensorHighThresholdNotificationEnable = \
        SubtreeMIBEntry('1.6.1', updater, ValueType.INTEGER, updater.get_high_sensors_notification)
        
    entSensorLowThresholdNotificationEnable = \
        SubtreeMIBEntry('1.6.2', updater, ValueType.INTEGER, updater.get_low_sensors_notification)


class CiscoPhysicalSensorValueTableMIB(metaclass=MIBMeta, prefix='.1.3.6.1.4.1.9.9.91.1.1.1'):
    """
    Sensor Value table.
    """

    updater = CiscoValuePhysicalSensorTableMIBUpdater()

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
