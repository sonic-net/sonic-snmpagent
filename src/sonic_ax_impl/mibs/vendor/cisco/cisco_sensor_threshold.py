"""
Cisco sensor threshold MIB implementation
"""

from enum import Enum, unique
from bisect import bisect_right

from swsssdk import port_util
from ax_interface import MIBMeta, MIBUpdater, ValueType, SubtreeMIBEntry
from sonic_ax_impl import mibs
from sonic_ax_impl.mibs import HOST_NAMESPACE_DB_IDX
from sonic_ax_impl.mibs import Namespace
from ...ietf.physical_entity_sub_oid_generator import get_transceiver_sensor_sub_id
from ...ietf.physical_entity_sub_oid_generator import get_psu_sub_id
from ...ietf.physical_entity_sub_oid_generator import get_psu_sensor_sub_id
from ...ietf.physical_entity_sub_oid_generator import get_chassis_thermal_sub_id
from ...ietf.physical_entity_sub_oid_generator import get_psu_thermal_sub_id
from ...ietf.sensor_data import ThermalSensorData, PSUSensorData, TransceiverSensorData

CHASSIS_NAME_SUB_STRING = 'chassis'
NOT_AVAILABLE = 'N/A'


def isfloat(number):
    try:
        float(number)
        return True
    except:
        return False
        
    
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
class entSensorThresholdSeverity(int, Enum):
    """
    Enumeration of sensor Threshold Severity according to Cisco MIB
    """

    other=1
    minor=10
    major=20
    critical=30

@unique
class entSensorThresholdRelation(int, Enum):
    """
    Enumeration of sensor Threshold Relation according to Cisco MIB
    """

    lessThan=1
    lessOrEqual=2
    greaterThan=3
    greaterOrEqual=4
    equalTo=5
    notEqualTo=6

@unique
class entSensorThresholdEvaluation(int, Enum):
    """
    Enumeration of sensor Threshold Evaluation according to Cisco MIB
    """

    true=1
    false=2

@unique
class entSensorThresholdNotificationEnable(int, Enum):
    """
    Enumeration of sensor Threshold Notification Enable according to Cisco MIB
    """
    true=1
    false=2

class CiscoPhysicalSensorThretholdTableMIBUpdater(MIBUpdater):
    """
    Updater for sensors Threshold.
    """

    TRANSCEIVER_DOM_KEY_PATTERN = mibs.transceiver_dom_table("*")
    PSU_SENSOR_KEY_PATTERN = mibs.psu_info_table("*")
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

        # sensor threshold MIB required values
        self.sensor_threshold_map = {}
        self.transceiver_dom = []
        self.psu_sensor = []
        self.thermal_sensor = []
    
    def reinit_data(self):
        """
        Reinit data, clear cache
        """

        # clear cache
        self.ent_phy_sensor_type_map = {}
        
        transceiver_dom_encoded = Namespace.dbs_keys(self.statedb, mibs.STATE_DB, self.TRANSCEIVER_DOM_KEY_PATTERN) 
        if transceiver_dom_encoded:
            self.transceiver_dom = [entry for entry in transceiver_dom_encoded]

        psu_sensor_encoded = self.statedb[HOST_NAMESPACE_DB_IDX].keys(self.statedb[HOST_NAMESPACE_DB_IDX].STATE_DB,
                                                                      self.PSU_SENSOR_KEY_PATTERN)
        if psu_sensor_encoded:
            self.psu_sensor = [entry for entry in psu_sensor_encoded]

        thermal_sensor_encoded = self.statedb[HOST_NAMESPACE_DB_IDX].keys(self.statedb[HOST_NAMESPACE_DB_IDX].STATE_DB,
                                                                          self.THERMAL_SENSOR_KEY_PATTERN)
        if thermal_sensor_encoded:
            self.thermal_sensor = [entry for entry in thermal_sensor_encoded]
            
            
    
  
  
    def update_xcvr_sensors_threshold(self):
        """
        Subclass update sesnor threshold information
        """
 
        if not self.transceiver_dom:
            return

        # update transceiver sensors cache
        for transceiver_dom_entry in self.transceiver_dom:
            interface = transceiver_dom_entry.split(mibs.TABLE_NAME_SEPARATOR_VBAR)[-1]
            ifindex = port_util.get_index_from_str(interface)

            if ifindex is None:
                mibs.logger.warning(
                    "Invalid interface name in {} \
                     in STATE_DB, skipping".format(transceiver_dom_entry))
                continue

            transceiver_dom_entry_data = Namespace.dbs_get_all(self.statedb, mibs.STATE_DB, transceiver_dom_entry)
            if not transceiver_dom_entry_data:
                continue
            
            sensor_data_list = TransceiverSensorData.create_sensor_data(transceiver_dom_entry_data)
            for sensor_data in sensor_data_list:
                raw_sensor_value = sensor_data.get_raw_value()
                sub_id = get_transceiver_sensor_sub_id(ifindex, sensor_data.get_oid_offset())
                self.sensor_threshold_map[sub_id] = {'highalarm': {}, 'lowalarm':{}}
                
                try :
                    float(raw_sensor_value) 
                    highalarmkey= sensor_data._sensor_attrs.get('highalarmkey', None) 
                    if highalarmkey :                      
                        raw_threshold_value = transceiver_dom_entry_data.get(highalarmkey, 'N/A')
                        if isfloat(raw_threshold_value):
                            self.sensor_threshold_map[sub_id]["highalarm"] = {
                                                                        "Severity": entSensorThresholdSeverity.critical,
                                                                        "Relation": entSensorThresholdRelation.greaterThan,
                                                                        "Value": transceiver_dom_entry_data.get(highalarmkey, None),
                                                                        "Evaluation": entSensorThresholdEvaluation.false if float(raw_sensor_value) < float(transceiver_dom_entry_data.get(highalarmkey)) else entSensorThresholdEvaluation.true,
                                                                        "ThresholdNotification": entSensorThresholdNotificationEnable.true,
                                                                    }
                            if sub_id not in self.sub_ids:
                                self.sub_ids.append(sub_id)
                        else:
                            self.sensor_threshold_map[sub_id] ["highalarm"] = {
                                                                        "Severity": entSensorThresholdSeverity.other,
                                                                        "Relation": entSensorThresholdRelation.notEqualTo,
                                                                        "Value": 'N/A',
                                                                        "Evaluation": entSensorThresholdEvaluation.false,
                                                                        "ThresholdNotification": entSensorThresholdNotificationEnable.false
                                                                    }
                except Exception as e:
                    continue
                
                try : 
                    lowalarmkey =  sensor_data._sensor_attrs.get('lowalarmkey', None)
                    if lowalarmkey:
                        raw_threshold_value = transceiver_dom_entry_data.get(highalarmkey, 'N/A')
                        if isfloat(raw_threshold_value):
                            self.sensor_threshold_map[sub_id][ "lowalarm"] = {
                                                                        "Severity": entSensorThresholdSeverity.critical,
                                                                        "Relation": entSensorThresholdRelation.lessThan,
                                                                        "Value": transceiver_dom_entry_data.get(lowalarmkey, None),
                                                                        "Evaluation": entSensorThresholdEvaluation.false if float(raw_sensor_value) > float(transceiver_dom_entry_data.get(lowalarmkey)) else entSensorThresholdEvaluation.true,
                                                                        "ThresholdNotification": entSensorThresholdNotificationEnable.true
                                                                    }
                            if sub_id not in self.sub_ids:
                                self.sub_ids.append(sub_id)
                        else:
                            self.sensor_threshold_map[sub_id] ["lowalarm"] = {
                                                                        "Severity": entSensorThresholdSeverity.other,
                                                                        "Relation": entSensorThresholdRelation.notEqualTo,
                                                                        "Value": 'N/A',
                                                                        "Evaluation": entSensorThresholdEvaluation.false,
                                                                        "ThresholdNotification": entSensorThresholdNotificationEnable.false
                                                                    }
                except Exception as e:
                    continue 
        return
    
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
                sub_id = get_psu_sensor_sub_id(psu_sub_id, sensor_data.get_name().lower())
                self.sensor_threshold_map[sub_id] = {'highalarm': {}, 'lowalarm':{}}
                try :
                    float(raw_sensor_value) 
                    highalarmkey= sensor_data._sensor_attrs.get('highalarmkey', None)
                    if highalarmkey:
                        threshold_raw_value = psu_sensor_entry_data.get(highalarmkey, None)
                        float(psu_sensor_entry_data.get(highalarmkey))
                        if isfloat(threshold_raw_value):
                            self.sensor_threshold_map[sub_id]["highalarm"] =  {
                                                                        "Severity": entSensorThresholdSeverity.major,
                                                                        "Relation": entSensorThresholdRelation.greaterThan,
                                                                        "Value": psu_sensor_entry_data.get(highalarmkey, None),
                                                                        "Evaluation": entSensorThresholdEvaluation.false if float(raw_sensor_value) < float(psu_sensor_entry_data.get(highalarmkey)) else entSensorThresholdEvaluation.true,
                                                                        "ThresholdNotification": entSensorThresholdNotificationEnable.true
                                                                    }
                            if sub_id not in self.sub_ids:
                                self.sub_ids.append(sub_id)
                        else:
                            self.sensor_threshold_map[sub_id] ["highalarm"] = {
                                                                        "Severity": entSensorThresholdSeverity.other,
                                                                        "Relation": entSensorThresholdRelation.notEqualTo,
                                                                        "Value": 'N/A',
                                                                        "Evaluation": entSensorThresholdEvaluation.false,
                                                                        "ThresholdNotification": entSensorThresholdNotificationEnable.false
                                                                    }                                                     
                except Exception as e:
                    continue
                
                try :
                    lowalarmkey= sensor_data._sensor_attrs.get('lowalarmkey', None)
                    if lowalarmkey:
                        threshold_raw_value = psu_sensor_entry_data.get(lowalarmkey, None)
                        if isfloat(threshold_raw_value):# check if no key in sensor att dict and value is float in db
                            self.sensor_threshold_map[sub_id]["lowalarm"] =  {
                                                                        "Severity": entSensorThresholdSeverity.major,
                                                                        "Relation": entSensorThresholdRelation.lessThan,
                                                                        "Value": psu_sensor_entry_data.get(lowalarmkey, None),
                                                                        "Evaluation": entSensorThresholdEvaluation.false if float(raw_sensor_value) > float(psu_sensor_entry_data.get(lowalarmkey)) else entSensorThresholdEvaluation.true,
                                                                        "ThresholdNotification": entSensorThresholdNotificationEnable.true
                                                                    }
                            if sub_id not in self.sub_ids:
                                self.sub_ids.append(sub_id)
                        else:
                            self.sensor_threshold_map[sub_id] ["lowalarm"] = {
                                                                        "Severity": entSensorThresholdSeverity.other,
                                                                        "Relation": entSensorThresholdRelation.notEqualTo,
                                                                        "Value": 'N/A',
                                                                        "Evaluation": entSensorThresholdEvaluation.false,
                                                                        "ThresholdNotification": entSensorThresholdNotificationEnable.false
                                                                    }
                except Exception as e:
                    continue
        return
    
    def update_thermal_sensor_data(self):
        if not self.thermal_sensor:
            return

        for thermal_sensor_entry in self.thermal_sensor:
            thermal_name = thermal_sensor_entry.split(mibs.TABLE_NAME_SEPARATOR_VBAR)[-1]
            thermal_relation_info = self.statedb[HOST_NAMESPACE_DB_IDX].get_all(
                self.statedb[HOST_NAMESPACE_DB_IDX].STATE_DB, mibs.physical_entity_info_table(thermal_name))
            thermal_position, thermal_parent_name = get_db_data(thermal_relation_info, PhysicalRelationInfoDB)

            if is_null_empty_str(thermal_parent_name) or is_null_empty_str(thermal_parent_name):
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

                sub_id = get_chassis_thermal_sub_id(thermal_position) if CHASSIS_NAME_SUB_STRING in thermal_parent_name.lower() \
                    else get_psu_thermal_sub_id(thermal_position)
                    
                self.sensor_threshold_map[sub_id] = {'highalarm': {}, 'lowalarm':{}}
                try :
                    float(raw_sensor_value) 
                    highalarmkey= sensor_data._sensor_attrs.get('highalarmkey', None)
                    if highalarmkey :
                        threshold_raw_value = thermal_sensor_entry_data.get(highalarmkey, 'N/A')
                        if isfloat(threshold_raw_value): # check if no key in db dict or no value at that key 
                            self.sensor_threshold_map[sub_id]['highalarm'] = {
                                                                        "Severity": entSensorThresholdSeverity.major,
                                                                        "Relation": entSensorThresholdRelation.greaterThan,
                                                                        "Value": thermal_sensor_entry_data.get(highalarmkey, None),
                                                                        "Evaluation": entSensorThresholdEvaluation.false if float(raw_sensor_value) < float(thermal_sensor_entry_data.get(highalarmkey)) else entSensorThresholdEvaluation.true,
                                                                        "ThresholdNotification": entSensorThresholdNotificationEnable.true
                                                                    }
                            if sub_id not in self.sub_ids:
                                self.sub_ids.append(sub_id)
                        else:
                            self.sensor_threshold_map[sub_id] ["highalarm"] = {
                                                                        "Severity": entSensorThresholdSeverity.other,
                                                                        "Relation": entSensorThresholdRelation.notEqualTo,
                                                                        "Value": 'N/A',
                                                                        "Evaluation": entSensorThresholdEvaluation.false,
                                                                        "ThresholdNotification": entSensorThresholdNotificationEnable.false
                                                                    }
                except Exception as e:
                    continue 
                
                try :
                    lowalarmkey =  sensor_data._sensor_attrs.get('lowalarmkey', None) 
                    if lowalarmkey:
                        threshold_raw_value = thermal_sensor_entry_data.get(lowalarmkey, None)
                        if isfloat(threshold_raw_value):
                            self.sensor_threshold_map[sub_id] ["lowalarm"] = {
                                                                        "Severity": entSensorThresholdSeverity.major,
                                                                        "Relation": entSensorThresholdRelation.lessThan,
                                                                        "Value": thermal_sensor_entry_data.get(lowalarmkey, 'N/A'),
                                                                        "Evaluation": entSensorThresholdEvaluation.false if float(raw_sensor_value) > float(thermal_sensor_entry_data.get(lowalarmkey)) else entSensorThresholdEvaluation.true,
                                                                        "ThresholdNotification": entSensorThresholdNotificationEnable.true
                                                                    }
                            if sub_id not in self.sub_ids:
                                self.sub_ids.append(sub_id)
                        else:
                            self.sensor_threshold_map[sub_id] ["lowalarm"] = {
                                                                        "Severity": entSensorThresholdSeverity.other,
                                                                        "Relation": entSensorThresholdRelation.notEqualTo,
                                                                        "Value": 'N/A',
                                                                        "Evaluation": entSensorThresholdEvaluation.false,
                                                                        "ThresholdNotification": entSensorThresholdNotificationEnable.false
                                                                    }       
                except Exception as e:
                    continue 
        return

    def update_data(self):
        """
        Update sensors thresold cache.
        """

        self.sub_ids = []

        self.update_xcvr_sensors_threshold()
        self.update_psu_sensor_data()
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
       
    def get_high_sensors_severity(self,sub_id):
        if sub_id in self.sub_ids:
            return   self.sensor_threshold_map[sub_id]['highalarm'].get('Severity', None)
        return None
    
    def get_low_sensors_severity(self,sub_id):
        if sub_id in self.sub_ids:
            return   self.sensor_threshold_map[sub_id]['lowalarm'].get('Severity', None)
        return None
    
    def get_high_sensors_relation(self,sub_id):
        if sub_id in self.sub_ids:
            return   self.sensor_threshold_map[sub_id]['highalarm'].get('Relation',None)  
        return None
    
    def get_low_sensors_relation(self,sub_id):
        if sub_id in self.sub_ids:
            return   self.sensor_threshold_map[sub_id]['lowalarm'].get('Relation',None)
        return None
    
    def get_high_sensors_threshold(self,sub_id):
        if sub_id in self.sub_ids:
            return   self.sensor_threshold_map[sub_id]['highalarm'].get('Value', None)
        return None
    
    def get_low_sensors_threshold(self,sub_id):
        if sub_id in self.sub_ids:
            return   self.sensor_threshold_map[sub_id]['lowalarm'].get('Value', None)
        return None
    
    def get_high_sensors_evaluation(self,sub_id):
        if sub_id in self.sub_ids:
            return   self.sensor_threshold_map[sub_id]['highalarm'].get('Evaluation',None)
        return None
    
    def get_low_sensors_evaluation(self,sub_id):
        if sub_id in self.sub_ids:
            return   self.sensor_threshold_map[sub_id]['lowalarm'].get('Evaluation',None)
        return None
    
    def get_high_sensors_notification(self,sub_id):
        if sub_id in self.sub_ids:
            return   self.sensor_threshold_map[sub_id]['highalarm'].get('ThresholdNotification',None)
        return None
    
    def get_low_sensors_notification(self,sub_id):
        if sub_id in self.sub_ids:
            return   self.sensor_threshold_map[sub_id]['lowalarm'].get('ThresholdNotification',None)
        return None