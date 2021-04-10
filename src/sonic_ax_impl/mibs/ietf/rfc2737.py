"""
MIB implementation defined in RFC 2737
"""

from enum import Enum, unique
from bisect import bisect_right, insort_right

from swsssdk import port_util
from ax_interface import MIBMeta, MIBUpdater, ValueType, SubtreeMIBEntry

from sonic_ax_impl import mibs
from sonic_ax_impl.mibs import Namespace

from .physical_entity_sub_oid_generator import CHASSIS_SUB_ID
from .physical_entity_sub_oid_generator import CHASSIS_MGMT_SUB_ID
from .physical_entity_sub_oid_generator import get_chassis_thermal_sub_id
from .physical_entity_sub_oid_generator import get_fan_sub_id
from .physical_entity_sub_oid_generator import get_fan_drawer_sub_id
from .physical_entity_sub_oid_generator import get_fan_tachometers_sub_id
from .physical_entity_sub_oid_generator import get_psu_sub_id
from .physical_entity_sub_oid_generator import get_psu_sensor_sub_id
from .physical_entity_sub_oid_generator import get_transceiver_sub_id
from .physical_entity_sub_oid_generator import get_transceiver_sensor_sub_id
from .transceiver_sensor_data import TransceiverSensorData


@unique
class PhysicalClass(int, Enum):
    """
    Physical classes defined in RFC 2737.
    """

    OTHER       = 1
    UNKNOWN     = 2
    CHASSIS     = 3
    BACKPLANE   = 4
    CONTAINER   = 5
    POWERSUPPLY = 6
    FAN         = 7
    SENSOR      = 8
    MODULE      = 9
    PORT        = 10
    STACK       = 11
    CPU         = 12   # Added in RFC 6933


@unique
class FanInfoDB(str, Enum):
    """
    FAN info keys
    """
    MODEL       = 'model'
    PRESENCE    = 'presence'
    SERIAL      = 'serial'
    SPEED       = 'speed'
    REPLACEABLE = 'is_replaceable'


@unique
class FanDrawerInfoDB(str, Enum):
    """
    FAN drawer info keys
    """
    MODEL       = 'model'
    PRESENCE    = 'presence'
    SERIAL      = 'serial'
    REPLACEABLE = 'is_replaceable'


@unique
class PhysicalRelationInfoDB(str, Enum):
    """
    Physical relation info keys
    """
    POSITION_IN_PARENT    = 'position_in_parent'
    PARENT_NAME           = 'parent_name'


@unique
class PsuInfoDB(str, Enum):
    """
    PSU info keys
    """
    MODEL       = 'model'
    SERIAL      = 'serial'
    CURRENT     = 'current'
    POWER       = 'power'
    PRESENCE    = 'presence'
    VOLTAGE     = 'voltage'
    TEMPERATURE = 'temp'
    REPLACEABLE = 'is_replaceable'


@unique
class XcvrInfoDB(str, Enum):
    """
    Transceiver info keys
    """
    TYPE              = "type"
    HARDWARE_REVISION = "hardware_rev"
    SERIAL_NUMBER     = "serial"
    MANUFACTURE_NAME  = "manufacturer"
    MODEL_NAME        = "model"
    REPLACEABLE       = 'is_replaceable'

@unique
class ThermalInfoDB(str, Enum):
    """
    FAN drawer info keys
    """
    TEMPERATURE = 'temperature'
    REPLACEABLE = 'is_replaceable'


# Map used to generate PSU sensor description
PSU_SENSOR_NAME_MAP = {
    'temperature': 'Temperature',
    'power'      : 'Power',
    'current'    : 'Current',
    'voltage'    : 'Voltage'
}

PSU_SENSOR_POSITION_MAP = {
    'temperature': 1,
    'power'      : 2,
    'current'    : 3,
    'voltage'    : 4
}

NOT_AVAILABLE = 'N/A'

def is_null_str(value):
    """
    Indicate if a string value is null
    :param value: input string value
    :return: True is string value is empty or equal to 'N/A' or 'None'
    """
    if not isinstance(value, str) or value == NOT_AVAILABLE or value == 'None':
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


def get_transceiver_description(sfp_type, if_alias):
    """
    :param sfp_type: SFP type of transceiver
    :param if_alias: Port alias name
    :return: Transceiver decsription
    """
    if not if_alias:
        description = "{}".format(sfp_type)
    else:
        description = "{} for {}".format(sfp_type, if_alias)

    return description

def get_transceiver_sensor_description(name, lane_number, if_alias):
    """
    :param name: sensor name
    :param lane_number: lane number of this sensor
    :param if_alias: interface alias
    :return: description string about sensor
    """
    if lane_number == 0:
        port_name = if_alias
    else:
        port_name = "{}/{}".format(if_alias, lane_number)

    return "DOM {} Sensor for {}".format(name, port_name)


class Callback(object):
    """
    Utility class to store a callable and its arguments for future invoke
    """
    def __init__(self, function, args):
        # A callable
        self.function = function

        # Arguments for the given callable
        self.args = args

    def invoke(self):
        """
        Invoke the callable
        """
        self.function(*self.args)


class PhysicalTableMIBUpdater(MIBUpdater):
    """
    Updater class for physical table MIB
    """

    # Chassis key name in CHASSIS_INFO table
    CHASSIS_NAME = 'chassis 1'

    # Indicate that an entity is replaceable, according to RFC2737
    REPLACEABLE = 1

    # Indicate that an entity is not replaceable, according to RFC2737
    NOT_REPLACEABLE = 2

    # A list of physical entity updater, @decorator physical_entity_updater can register physical entity updater types
    # to this list, and these types will be used for create instance for each type
    physical_entity_updater_types = []

    def __init__(self):
        super().__init__()

        self.statedb = Namespace.init_namespace_dbs()
        Namespace.connect_all_dbs(self.statedb, mibs.STATE_DB)

        # List of available sub OIDs.
        self.physical_entities = []

        # Map sub ID to its data.
        self.physical_classes_map = {}
        self.physical_description_map = {}
        self.physical_name_map = {}
        self.physical_hw_version_map = {}
        self.physical_serial_number_map = {}
        self.physical_mfg_name_map = {}
        self.physical_model_name_map = {}
        self.physical_contained_in_map = {}
        self.physical_parent_relative_pos_map = {}
        self.physical_fru_map = {}

        # Map physical entity name and oid. According to RFC2737, entPhysicalContainedIn is indicates the value of
        # entPhysicalIndex for the physical entity which 'contains' this physical entity. However, there is
        # only parent entity name in database, so need a way to get physical entity oid by name.
        self.physical_name_to_oid_map = {}

        # Map physical entity name that need resolve. The key is the entity name, value is a list of Callback objects
        # that will be called when the entity name is added to self.physical_name_to_oid_map.
        # It's possible the parent name and parent oid are still not in self.physical_name_to_oid_map when child entity
        # update cache. In that case, the child entity might not be able to calculate its sub id and cannot update its
        # cache or do future operation. So this dictionary provides a way to store such operations for future executes.
        self.pending_resolve_parent_name_map = {}

        # physical entity updaters
        self.physical_entity_updaters = self.create_physical_entity_updaters()

    @classmethod
    def register_entity_updater_type(cls, object_type):
        """
        Register physical entity updater
        :param object_type: entity updater type
        """
        cls.physical_entity_updater_types.append(object_type)

    def create_physical_entity_updaters(self):
        """
        Create all physical entity updater instances
        :return: a list of physical entity updater instance
        """
        return [creator(self) for creator in PhysicalTableMIBUpdater.physical_entity_updater_types]

    def reinit_data(self):
        """
        Re-initialize all data.
        """

        # reinit cache
        self.physical_classes_map = {}
        self.physical_description_map = {}
        self.physical_name_map = {}
        self.physical_hw_version_map = {}
        self.physical_serial_number_map = {}
        self.physical_mfg_name_map = {}
        self.physical_model_name_map = {}
        self.physical_contained_in_map = {}
        self.physical_parent_relative_pos_map = {}
        self.physical_fru_map = {}

        self.physical_name_to_oid_map = {}
        self.pending_resolve_parent_name_map = {}

        device_metadata = mibs.get_device_metadata(self.statedb[0])
        chassis_sub_id = (CHASSIS_SUB_ID, )
        self.physical_entities = [chassis_sub_id]
        self.physical_name_to_oid_map[self.CHASSIS_NAME] = chassis_sub_id

        if not device_metadata or not device_metadata.get("chassis_serial_number"):
            chassis_serial_number = ""
        else:
            chassis_serial_number = device_metadata["chassis_serial_number"]

        self.physical_classes_map[chassis_sub_id] = PhysicalClass.CHASSIS
        self.physical_serial_number_map[chassis_sub_id] = chassis_serial_number
        self.physical_name_map[chassis_sub_id] = self.CHASSIS_NAME
        self.physical_description_map[chassis_sub_id] = self.CHASSIS_NAME
        self.physical_contained_in_map[chassis_sub_id] = 0
        self.physical_fru_map[chassis_sub_id] = self.NOT_REPLACEABLE

        # Add a chassis mgmt node
        chassis_mgmt_sub_id = (CHASSIS_MGMT_SUB_ID,)
        self.add_sub_id(chassis_mgmt_sub_id)
        self.physical_classes_map[chassis_mgmt_sub_id] = PhysicalClass.CPU
        self.physical_contained_in_map[chassis_mgmt_sub_id] = CHASSIS_SUB_ID
        self.physical_parent_relative_pos_map[chassis_mgmt_sub_id] = 1
        name = 'MGMT'
        self.physical_description_map[chassis_mgmt_sub_id] = name
        self.physical_name_map[chassis_mgmt_sub_id] = name
        self.physical_fru_map[chassis_mgmt_sub_id] = self.NOT_REPLACEABLE

        for updater in self.physical_entity_updaters:
            updater.reinit_data()

    def update_data(self):
        # This code is not executed in unit test, since mockredis
        # does not support pubsub
        for i in range(len(self.statedb)):
            for updater in self.physical_entity_updaters:
                updater.update_data(i, self.statedb[i])

    def add_sub_id(self, sub_id):
        insort_right(self.physical_entities, sub_id)

    def remove_sub_ids(self, remove_sub_ids):
        """
        Remove all data related to given sub id list
        :param remove_sub_ids: a list of sub ids that will be removed
        """
        for sub_id in remove_sub_ids:
            if not sub_id:
                continue
            if sub_id in self.physical_entities:
                self.physical_entities.remove(sub_id)
            if sub_id in self.physical_classes_map:
                self.physical_classes_map.pop(sub_id)
            if sub_id in self.physical_name_map:
                name = self.physical_name_map[sub_id]
                if name in self.physical_name_to_oid_map:
                    self.physical_name_to_oid_map.pop(name)
                if name in self.pending_resolve_parent_name_map:
                    self.pending_resolve_parent_name_map.pop(name)
                self.physical_name_map.pop(sub_id)
            if sub_id in self.physical_hw_version_map:
                self.physical_hw_version_map.pop(sub_id)
            if sub_id in self.physical_serial_number_map:
                self.physical_serial_number_map.pop(sub_id)
            if sub_id in self.physical_mfg_name_map:
                self.physical_mfg_name_map.pop(sub_id)
            if sub_id in self.physical_model_name_map:
                self.physical_model_name_map.pop(sub_id)
            if sub_id in self.physical_contained_in_map:
                self.physical_contained_in_map.pop(sub_id)
            if sub_id in self.physical_parent_relative_pos_map:
                self.physical_parent_relative_pos_map.pop(sub_id)
            if sub_id in self.physical_fru_map:
                self.physical_fru_map.pop(sub_id)

    def add_pending_entity_name_callback(self, name, function, args):
        """
        Store a callback for those entity whose parent entity name has not been resolved yet
        :param name: parent entity name
        :param function: a callable
        :param args: arguments for the callable
        """
        if name in self.pending_resolve_parent_name_map:
            self.pending_resolve_parent_name_map[name].append(Callback(function, args))
        else:
            self.pending_resolve_parent_name_map[name] = [Callback(function, args)]

    def update_name_to_oid_map(self, name, oid):
        """
        Update entity name to oid map. If the given name is in self.pending_resolve_parent_name_map, update physical
        contained in information accordingly.
        :param name: entity name
        :param oid: entity oid
        """
        self.physical_name_to_oid_map[name] = oid

        if name in self.pending_resolve_parent_name_map:
            for callback in self.pending_resolve_parent_name_map[name]:
                callback.invoke()
            self.pending_resolve_parent_name_map.pop(name)

    def set_phy_class(self, sub_id, phy_class):
        """
        :param sub_id: sub OID
        :param phy_class: physical entity class
        """
        self.physical_classes_map[sub_id] = phy_class

    def set_phy_parent_relative_pos(self, sub_id, pos):
        """
        :param sub_id: sub OID
        :param pos: 1-based relative position
        """
        self.physical_parent_relative_pos_map[sub_id] = pos

    def set_phy_descr(self, sub_id, phy_desc):
        """
        :param sub_id: sub OID
        :param phy_desc: physical entity description
        """
        self.physical_description_map[sub_id] = phy_desc

    def set_phy_name(self, sub_id, name):
        """
        :param sub_id: sub OID
        :param name: physical entity name
        """
        self.physical_name_map[sub_id] = name

    def set_phy_contained_in(self, sub_id, parent):
        """
        :param sub_id: sub OID
        :param parent: parent entity name or parent oid
        """

        if isinstance(parent, str):
            if parent in self.physical_name_to_oid_map:
                self.physical_contained_in_map[sub_id] = self.physical_name_to_oid_map[parent][0]
            else:
                self._add_pending_entity_name_callback(parent, self.set_phy_contained_in, [sub_id, parent])
        elif isinstance(parent, int):
            self.physical_contained_in_map[sub_id] = parent
        elif isinstance(parent, tuple):
            self.physical_contained_in_map[sub_id] = parent[0]

    def set_phy_hw_ver(self, sub_id, phy_hw_ver):
        """
        :param sub_id: sub OID
        :param phy_hw_ver: physical entity hardware version
        """
        self.physical_hw_version_map[sub_id] = phy_hw_ver

    def set_phy_serial_num(self, sub_id, phy_serial_num):
        """
        :param sub_id: sub OID
        :param phy_serial_num: physical entity serial number
        """
        self.physical_serial_number_map[sub_id] = phy_serial_num

    def set_phy_mfg_name(self, sub_id, phy_mfg_name):
        """
        :param sub_id: sub OID
        :param phy_mfg_name: physical entity manufacturer name
        """
        self.physical_mfg_name_map[sub_id] = phy_mfg_name

    def set_phy_model_name(self, sub_id, phy_model_name):
        """
        :param sub_id: sub OID
        :param phy_model_name: physical entity model name
        """
        self.physical_model_name_map[sub_id] = phy_model_name

    def set_phy_fru(self, sub_id, replaceable):
        """
        :param sub_id: sub OID
        :param replaceable: physical entity FRU
        """
        if isinstance(replaceable, str):
            replaceable = True if replaceable.lower() == 'true' else False
            self.physical_fru_map[sub_id] = self.REPLACEABLE if replaceable else self.NOT_REPLACEABLE
        elif isinstance(replaceable, bool):
            self.physical_fru_map[sub_id] = self.REPLACEABLE if replaceable else self.NOT_REPLACEABLE

    def get_next(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query.
        :return: the next sub id.
        """

        right = bisect_right(self.physical_entities, sub_id)
        if right == len(self.physical_entities):
            return None
        return self.physical_entities[right]

    def get_phy_class(self, sub_id):
        """
        :param sub_id: sub OID
        :return: physical class for this OID
        """

        if sub_id in self.physical_entities:
            return self.physical_classes_map.get(sub_id, PhysicalClass.UNKNOWN)
        return None

    def get_phy_parent_relative_pos(self, sub_id):
        """
        :param sub_id: sub OID
        :return: relative position in parent device for this OID
        """
        if sub_id in self.physical_entities:
            return self.physical_parent_relative_pos_map.get(sub_id, PhysicalClass.UNKNOWN)
        return None

    def get_phy_descr(self, sub_id):
        """
        :param sub_id: sub OID
        :return: description string for this OID
        """

        if sub_id in self.physical_entities:
            return self.physical_description_map.get(sub_id, "")
        return None

    def get_phy_vendor_type(self, sub_id):
        """
        :param sub_id: sub OID
        :return: vendor type for this OID
        """

        return "" if sub_id in self.physical_entities else None

    def get_phy_contained_in(self, sub_id):
        """
        :param sub_id: sub OID
        :return: physical contained in device OID for this OID
        """

        if sub_id in self.physical_entities:
            return self.physical_contained_in_map.get(sub_id, -1)
            #return sub_id_tuple[0] if isinstance(sub_id_tuple, tuple) else None
        return None

    def get_phy_name(self, sub_id):
        """
        :param sub_id: sub OID
        :return: name string for this OID
        """
        if sub_id in self.physical_entities:
            return self.physical_name_map.get(sub_id, "")
        return None

    def get_phy_hw_ver(self, sub_id):
        """
        :param sub_id: sub OID
        :return: hardware version for this OID
        """

        if sub_id in self.physical_entities:
            return self.physical_hw_version_map.get(sub_id, "")
        return None

    def get_phy_fw_ver(self, sub_id):
        """
        :param sub_id: sub OID
        :return: firmware version for this OID
        """

        return "" if sub_id in self.physical_entities else None

    def get_phy_sw_rev(self, sub_id):
        """
        :param sub_id: sub OID
        :return: software version for this OID
        """

        return "" if sub_id in self.physical_entities else None

    def get_phy_serial_num(self, sub_id):
        """
        :param sub_id: sub OID
        :return: serial number for this OID
        """

        if sub_id in self.physical_entities:
            return self.physical_serial_number_map.get(sub_id, "")
        return None

    def get_phy_mfg_name(self, sub_id):
        """
        :param sub_id: sub OID
        :return: manufacture name for this OID
        """

        if sub_id in self.physical_entities:
            return self.physical_mfg_name_map.get(sub_id, "")
        return None

    def get_phy_model_name(self, sub_id):
        """
        :param sub_id: sub OID
        :return: model name for this OID
        """

        if sub_id in self.physical_entities:
            return self.physical_model_name_map.get(sub_id, "")
        return None

    def get_phy_alias(self, sub_id):
        """
        :param sub_id: sub OID
        :return: alias for this OID
        """

        return "" if sub_id in self.physical_entities else None

    def get_phy_assert_id(self, sub_id):
        """
        :param sub_id: sub OID
        :return: assert ID for this OID
        """

        return "" if sub_id in self.physical_entities else None

    def is_fru(self, sub_id):
        """
        :param sub_id: sub OID
        :return: if it is FRU for this OID
        """
        if sub_id in self.physical_entities:
            return self.physical_fru_map.get(sub_id, self.NOT_REPLACEABLE)
        return None


def physical_entity_updater():
    """
    Decorator for auto registering physical entity types
    """
    def wrapper(object_type):
        PhysicalTableMIBUpdater.register_entity_updater_type(object_type)
        return object_type

    return wrapper


class PhysicalEntityCacheUpdater(object):
    """
    Base class for physical entity cache updater
    """
    def __init__(self, mib_updater):
        self.mib_updater = mib_updater
        self.pub_sub_dict = {}

        # Map to store fan to its related oid. The key is the db key in FAN_INFO table, the value is a list of oid that
        # relates to this fan entry. The map is used for removing fan mib objects when a fan removing from the system.
        self.entity_to_oid_map = {}

    def reinit_data(self):
        self.entity_to_oid_map.clear()
        # retrieve the initial list of entity in db
        key_info = Namespace.dbs_keys(self.mib_updater.statedb, mibs.STATE_DB, self.get_key_pattern())
        if key_info:
            keys = [entry for entry in key_info]
        else:
            keys = []

        # update cache with initial data
        for key in keys:
            # extract entity name
            name = key.split(mibs.TABLE_NAME_SEPARATOR_VBAR)[-1]
            self._update_entity_cache(name)

    def update_data(self, db_index, db):
        if db_index not in self.pub_sub_dict:
            self.pub_sub_dict[db_index] = mibs.get_redis_pubsub(db, db.STATE_DB, self.get_key_pattern())

        self._update_per_namespace_data(self.pub_sub_dict[db_index])

    def _update_per_namespace_data(self, pubsub):
        """
        Update cache.
        Here we listen to changes in STATE_DB table
        and update data only when there is a change (SET, DELETE)
        """
        while True:
            msg = pubsub.get_message()

            if not msg:
                break

            db_entry = msg["channel"].split(":")[-1]
            data = msg['data']  # event data
            if not isinstance(data, str):
                continue

            # extract interface name
            name = db_entry.split(mibs.TABLE_NAME_SEPARATOR_VBAR)[-1]

            if "set" in data:
                self._update_entity_cache(name)
            elif "del" in data:
                self._remove_entity_cache(name)

    def get_key_pattern(self):
        pass

    def _update_entity_cache(self, name):
        pass

    def get_physical_relation_info(self, name):
        return Namespace.dbs_get_all(self.mib_updater.statedb, mibs.STATE_DB,
                                     mibs.physical_entity_info_table(name))

    def _add_entity_related_oid(self, entity_name, oid):
        if entity_name not in self.entity_to_oid_map:
            self.entity_to_oid_map[entity_name] = [oid]
        else:
            self.entity_to_oid_map[entity_name].append(oid)

    def _remove_entity_cache(self, entity_name):
        if entity_name in self.entity_to_oid_map:
            self.mib_updater.remove_sub_ids(self.entity_to_oid_map[entity_name])
            self.entity_to_oid_map.pop(entity_name)


@physical_entity_updater()
class XcvrCacheUpdater(PhysicalEntityCacheUpdater):
    KEY_PATTERN = mibs.transceiver_info_table("*")

    def __init__(self, mib_updater):
        super(XcvrCacheUpdater, self).__init__(mib_updater)
        self.if_alias_map = {}

    def get_key_pattern(self):
        return XcvrCacheUpdater.KEY_PATTERN

    def reinit_data(self):
        # update interface maps
        _, self.if_alias_map, _, _ = \
            Namespace.get_sync_d_from_all_namespace(mibs.init_sync_d_interface_tables, Namespace.init_namespace_dbs())
        PhysicalEntityCacheUpdater.reinit_data(self)

    def _update_entity_cache(self, interface):
        """
        Update data for single transceiver
        :param: interface: Interface name associated with transceiver
        """

        # get interface from interface name
        ifindex = port_util.get_index_from_str(interface)

        if ifindex is None:
            # interface name invalid, skip this entry
            mibs.logger.warning(
                "Invalid interface name in {} \
                 in STATE_DB, skipping".format(interface))
            return

        # get transceiver information from transceiver info entry in STATE DB
        transceiver_info = Namespace.dbs_get_all(self.mib_updater.statedb, mibs.STATE_DB,
                                                 mibs.transceiver_info_table(interface))

        if not transceiver_info:
            return

        # update xcvr info from DB
        # use port's name as key for transceiver info entries
        sub_id = get_transceiver_sub_id(ifindex)

        # add interface to available OID list
        self.mib_updater.add_sub_id(sub_id)

        self._add_entity_related_oid(interface, sub_id)

        # physical class - network port
        self.mib_updater.set_phy_class(sub_id, PhysicalClass.PORT)

        # save values into cache
        sfp_type, hw_version, serial_number, mfg_name, model_name, replaceable = get_db_data(transceiver_info, XcvrInfoDB)
        self.mib_updater.set_phy_hw_ver(sub_id, hw_version)
        self.mib_updater.set_phy_serial_num(sub_id, serial_number)
        self.mib_updater.set_phy_mfg_name(sub_id, mfg_name)
        self.mib_updater.set_phy_model_name(sub_id, model_name)
        self.mib_updater.set_phy_contained_in(sub_id, CHASSIS_SUB_ID)
        self.mib_updater.set_phy_fru(sub_id, replaceable)
        # Relative position of SFP can be changed at run time. For example, plug out a normal cable SFP3 and plug in
        # a 1 split 4 SFP, the relative position of SFPs after SPF3 will change. In this case, it is hard to determine
        # the relative position for other SFP. According to RFC 2737, 'If the agent cannot determine the parent-relative position
        # for some reason, or if the associated value of entPhysicalContainedIn is '0', then the value '-1' is returned'.
        # See https://tools.ietf.org/html/rfc2737.
        self.mib_updater.set_phy_parent_relative_pos(sub_id, -1)

        ifalias = self.if_alias_map.get(interface, "")

        # generate a description for this transceiver
        self.mib_updater.set_phy_descr(sub_id, get_transceiver_description(sfp_type, ifalias))
        self.mib_updater.set_phy_name(sub_id, interface)

        # update transceiver sensor cache
        self._update_transceiver_sensor_cache(interface, sub_id)

    def _update_transceiver_sensor_cache(self, interface, sub_id):
        """
        Update sensor data for single transceiver
        :param: interface: Interface name associated with transceiver
        :param: sub_id: OID of transceiver
        """

        ifalias = self.if_alias_map.get(interface, "")
        ifindex = port_util.get_index_from_str(interface)

        # get transceiver sensors from transceiver dom entry in STATE DB
        transceiver_dom_entry = Namespace.dbs_get_all(self.mib_updater.statedb, mibs.STATE_DB,
                                                      mibs.transceiver_dom_table(interface))

        if not transceiver_dom_entry:
            return

        sensor_data_list = TransceiverSensorData.create_sensor_data(transceiver_dom_entry)
        sensor_data_list = TransceiverSensorData.sort_sensor_data(sensor_data_list)
        for index, sensor_data in enumerate(sensor_data_list):
            sensor_sub_id = get_transceiver_sensor_sub_id(ifindex, sensor_data.get_oid_offset())
            self._add_entity_related_oid(interface, sensor_sub_id)
            self.mib_updater.set_phy_class(sensor_sub_id, PhysicalClass.SENSOR)
            sensor_description = get_transceiver_sensor_description(sensor_data.get_name(), sensor_data.get_lane_number(), ifalias)
            self.mib_updater.set_phy_descr(sensor_sub_id, sensor_description)
            self.mib_updater.set_phy_name(sensor_sub_id, sensor_description)
            self.mib_updater.set_phy_contained_in(sensor_sub_id, sub_id)
            self.mib_updater.set_phy_parent_relative_pos(sensor_sub_id, index + 1)
            self.mib_updater.set_phy_fru(sensor_sub_id, False)
            # add to available OIDs list
            self.mib_updater.add_sub_id(sensor_sub_id)


@physical_entity_updater()
class PsuCacheUpdater(PhysicalEntityCacheUpdater):
    KEY_PATTERN = mibs.psu_info_table("*")

    def __init__(self, mib_updater):
        super(PsuCacheUpdater, self).__init__(mib_updater)

    def get_key_pattern(self):
        return PsuCacheUpdater.KEY_PATTERN

    def _update_entity_cache(self, psu_name):
        psu_info = Namespace.dbs_get_all(self.mib_updater.statedb, mibs.STATE_DB,
                                         mibs.psu_info_table(psu_name))

        if not psu_info:
            return

        model, serial, current, power, presence, voltage, temperature, replaceable = get_db_data(psu_info, PsuInfoDB)
        if presence.lower() != 'true':
            self._remove_entity_cache(psu_name)
            return

        psu_relation_info = self.get_physical_relation_info(psu_name)
        psu_position, psu_parent_name = get_db_data(psu_relation_info, PhysicalRelationInfoDB)
        psu_position = int(psu_position)
        psu_sub_id = get_psu_sub_id(psu_position)
        self._add_entity_related_oid(psu_name, psu_sub_id)
        self.mib_updater.update_name_to_oid_map(psu_name, psu_sub_id)

        # add PSU to available OID list
        self.mib_updater.add_sub_id(psu_sub_id)
        self.mib_updater.set_phy_class(psu_sub_id, PhysicalClass.POWERSUPPLY)
        self.mib_updater.set_phy_descr(psu_sub_id, psu_name)
        self.mib_updater.set_phy_name(psu_sub_id, psu_name)
        if not is_null_str(model):
            self.mib_updater.set_phy_model_name(psu_sub_id, model)
        if not is_null_str(serial):
            self.mib_updater.set_phy_serial_num(psu_sub_id, serial)
        self.mib_updater.set_phy_parent_relative_pos(psu_sub_id, psu_position)
        self.mib_updater.set_phy_contained_in(psu_sub_id, psu_parent_name)
        self.mib_updater.set_phy_fru(psu_sub_id, replaceable)

        # add psu current sensor as a physical entity
        if current and not is_null_str(current):
            self._update_psu_sensor_cache(psu_name, psu_sub_id, 'current')
        if power and not is_null_str(power):
            self._update_psu_sensor_cache(psu_name, psu_sub_id, 'power')
        if temperature and not is_null_str(temperature):
            self._update_psu_sensor_cache(psu_name, psu_sub_id, 'temperature')
        if voltage and not is_null_str(voltage):
            self._update_psu_sensor_cache(psu_name, psu_sub_id, 'voltage')

    def _update_psu_sensor_cache(self, psu_name, psu_sub_id, sensor_name):
        psu_current_sub_id = get_psu_sensor_sub_id(psu_sub_id, sensor_name)
        self._add_entity_related_oid(psu_name, psu_current_sub_id)
        self.mib_updater.add_sub_id(psu_current_sub_id)
        self.mib_updater.set_phy_class(psu_current_sub_id, PhysicalClass.SENSOR)
        desc = '{} for {}'.format(PSU_SENSOR_NAME_MAP[sensor_name], psu_name)
        self.mib_updater.set_phy_descr(psu_current_sub_id, desc)
        self.mib_updater.set_phy_name(psu_current_sub_id, desc)
        self.mib_updater.set_phy_parent_relative_pos(psu_current_sub_id, PSU_SENSOR_POSITION_MAP[sensor_name])
        self.mib_updater.set_phy_contained_in(psu_current_sub_id, psu_sub_id)
        self.mib_updater.set_phy_fru(psu_current_sub_id, False)


@physical_entity_updater()
class FanDrawerCacheUpdater(PhysicalEntityCacheUpdater):
    KEY_PATTERN = mibs.fan_drawer_info_table("*")

    def __init__(self, mib_updater):
        super(FanDrawerCacheUpdater, self).__init__(mib_updater)

    def get_key_pattern(self):
        return FanDrawerCacheUpdater.KEY_PATTERN

    def _update_entity_cache(self, drawer_name):
        drawer_info = Namespace.dbs_get_all(self.mib_updater.statedb, mibs.STATE_DB,
                                            mibs.fan_drawer_info_table(drawer_name))

        if not drawer_info:
            return

        model, presence, serial, replaceable = get_db_data(drawer_info, FanDrawerInfoDB)
        if presence.lower() != 'true':
            self._remove_entity_cache(drawer_name)
            return

        drawer_relation_info = self.get_physical_relation_info(drawer_name)
        if drawer_relation_info:
            drawer_position, drawer_parent_name = get_db_data(drawer_relation_info, PhysicalRelationInfoDB)
            drawer_position = int(drawer_position)
            drawer_sub_id = get_fan_drawer_sub_id(drawer_position)
            self._add_entity_related_oid(drawer_name, drawer_sub_id)
            self.mib_updater.update_name_to_oid_map(drawer_name, drawer_sub_id)

            # add fan drawer to available OID list
            self.mib_updater.add_sub_id(drawer_sub_id)
            self.mib_updater.set_phy_class(drawer_sub_id, PhysicalClass.CONTAINER)
            self.mib_updater.set_phy_descr(drawer_sub_id, drawer_name)
            self.mib_updater.set_phy_name(drawer_sub_id, drawer_name)
            self.mib_updater.set_phy_parent_relative_pos(drawer_sub_id, drawer_position)
            self.mib_updater.set_phy_contained_in(drawer_sub_id, drawer_parent_name)
            if model and not is_null_str(model):
                self.mib_updater.set_phy_model_name(drawer_sub_id, model)
            if serial and not is_null_str(serial):
                self.mib_updater.set_phy_serial_num(drawer_sub_id, serial)
            self.mib_updater.set_phy_fru(drawer_sub_id, replaceable)


@physical_entity_updater()
class FanCacheUpdater(PhysicalEntityCacheUpdater):
    KEY_PATTERN = mibs.fan_info_table("*")

    def __init__(self, mib_updater):
        super(FanCacheUpdater, self).__init__(mib_updater)

    def get_key_pattern(self):
        return FanCacheUpdater.KEY_PATTERN

    def _update_entity_cache(self, fan_name):
        fan_info = Namespace.dbs_get_all(self.mib_updater.statedb, mibs.STATE_DB,
                                         mibs.fan_info_table(fan_name))

        if not fan_info:
            return

        model, presence, serial, speed, replaceable = get_db_data(fan_info, FanInfoDB)
        if presence.lower() != 'true':
            self._remove_entity_cache(fan_name)
            return

        fan_relation_info = self.get_physical_relation_info(fan_name)
        fan_position, fan_parent_name = get_db_data(fan_relation_info, PhysicalRelationInfoDB)
        fan_position = int(fan_position)
        if fan_parent_name in self.mib_updater.physical_name_to_oid_map:
            self._update_fan_mib_info(fan_parent_name, fan_position, fan_name, serial, model, speed, replaceable)
        else:
            args = [fan_parent_name, fan_position, fan_name, serial, model, speed, replaceable]
            self.mib_updater.add_pending_entity_name_callback(fan_parent_name, self._update_fan_mib_info, args)

    def _update_fan_mib_info(self, fan_parent_name, fan_position, fan_name, serial, model, speed, replaceable):
        fan_parent_sub_id = self.mib_updater.physical_name_to_oid_map[fan_parent_name]
        fan_sub_id = get_fan_sub_id(fan_parent_sub_id, fan_position)
        self._add_entity_related_oid(fan_name, fan_sub_id)
        #self.mib_updater.update_name_to_oid_map(fan_name, fan_sub_id)

        # add fan to available OID list
        self.mib_updater.add_sub_id(fan_sub_id)
        self.mib_updater.set_phy_class(fan_sub_id, PhysicalClass.FAN)
        self.mib_updater.set_phy_descr(fan_sub_id, fan_name)
        self.mib_updater.set_phy_name(fan_sub_id, fan_name)
        self.mib_updater.set_phy_parent_relative_pos(fan_sub_id, fan_position)
        self.mib_updater.set_phy_contained_in(fan_sub_id, fan_parent_name)
        if serial and not is_null_str(serial):
            self.mib_updater.set_phy_serial_num(fan_sub_id, serial)
        if model and not is_null_str(model):
            self.mib_updater.set_phy_model_name(fan_sub_id, model)
        self.mib_updater.set_phy_fru(fan_sub_id, replaceable)

        # add fan tachometers as a physical entity
        if speed and not is_null_str(speed):
            fan_tachometers_sub_id = get_fan_tachometers_sub_id(fan_sub_id)
            self._add_entity_related_oid(fan_name, fan_tachometers_sub_id)
            self.mib_updater.add_sub_id(fan_tachometers_sub_id)
            self.mib_updater.set_phy_class(fan_tachometers_sub_id, PhysicalClass.SENSOR)
            desc = 'Tachometers for {}'.format(fan_name)
            self.mib_updater.set_phy_descr(fan_tachometers_sub_id, desc)
            self.mib_updater.set_phy_name(fan_tachometers_sub_id, desc)
            self.mib_updater.set_phy_parent_relative_pos(fan_tachometers_sub_id, 1)
            self.mib_updater.set_phy_contained_in(fan_tachometers_sub_id, fan_sub_id)
            self.mib_updater.set_phy_fru(fan_tachometers_sub_id, False)


@physical_entity_updater()
class ThermalCacheUpdater(PhysicalEntityCacheUpdater):
    KEY_PATTERN = mibs.thermal_info_table("*")

    def __init__(self, mib_updater):
        super(ThermalCacheUpdater, self).__init__(mib_updater)

    def get_key_pattern(self):
        return ThermalCacheUpdater.KEY_PATTERN

    def _update_entity_cache(self, thermal_name):
        thermal_info = Namespace.dbs_get_all(self.mib_updater.statedb, mibs.STATE_DB,
                                             mibs.thermal_info_table(thermal_name))
        if not thermal_info:
            return

        temperature, replaceable = get_db_data(thermal_info, ThermalInfoDB)
        if temperature and not is_null_str(temperature):
            thermal_relation_info = self.get_physical_relation_info(thermal_name)
            if not thermal_relation_info:
                return
            thermal_position, thermal_parent_name = get_db_data(thermal_relation_info, PhysicalRelationInfoDB)
            thermal_position = int(thermal_position)

            # only process thermals belong to chassis here, thermals belong to other
            # physical entity will be processed in other entity updater, for example
            # PSU thermal will be processed by PsuCacheUpdater
            if thermal_parent_name in self.mib_updater.physical_name_to_oid_map and \
                self.mib_updater.physical_name_to_oid_map[thermal_parent_name] == (CHASSIS_SUB_ID,):
                thermal_sub_id = get_chassis_thermal_sub_id(thermal_position)
                self._add_entity_related_oid(thermal_name, thermal_sub_id)

                # add thermal to available OID list
                self.mib_updater.add_sub_id(thermal_sub_id)
                self.mib_updater.set_phy_class(thermal_sub_id, PhysicalClass.SENSOR)
                self.mib_updater.set_phy_descr(thermal_sub_id, thermal_name)
                self.mib_updater.set_phy_name(thermal_sub_id, thermal_name)
                self.mib_updater.set_phy_parent_relative_pos(thermal_sub_id, thermal_position)
                self.mib_updater.set_phy_contained_in(thermal_sub_id, CHASSIS_MGMT_SUB_ID)
                self.mib_updater.set_phy_fru(thermal_sub_id, replaceable)
        else:
            self._remove_entity_cache(thermal_name)


class PhysicalTableMIB(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.47.1.1.1'):
    """
    Physical table
    """

    updater = PhysicalTableMIBUpdater()

    entPhysicalDescr = \
        SubtreeMIBEntry('1.2', updater, ValueType.OCTET_STRING, updater.get_phy_descr)

    entPhysicalVendorType = \
        SubtreeMIBEntry('1.3', updater, ValueType.OCTET_STRING, updater.get_phy_vendor_type)

    entPhysicalContainedIn = \
        SubtreeMIBEntry('1.4', updater, ValueType.INTEGER, updater.get_phy_contained_in)

    entPhysicalClass = \
        SubtreeMIBEntry('1.5', updater, ValueType.INTEGER, updater.get_phy_class)

    entPhysicalParentRelPos = \
        SubtreeMIBEntry('1.6', updater, ValueType.INTEGER, updater.get_phy_parent_relative_pos)

    entPhysicalName = \
        SubtreeMIBEntry('1.7', updater, ValueType.OCTET_STRING, updater.get_phy_name)

    entPhysicalHardwareVersion = \
        SubtreeMIBEntry('1.8', updater, ValueType.OCTET_STRING, updater.get_phy_hw_ver)

    entPhysicalFirmwareVersion = \
        SubtreeMIBEntry('1.9', updater, ValueType.OCTET_STRING, updater.get_phy_fw_ver)

    entPhysicalSoftwareRevision = \
        SubtreeMIBEntry('1.10', updater, ValueType.OCTET_STRING, updater.get_phy_sw_rev)

    entPhysicalSerialNumber = \
        SubtreeMIBEntry('1.11', updater, ValueType.OCTET_STRING, updater.get_phy_serial_num)

    entPhysicalMfgName = \
        SubtreeMIBEntry('1.12', updater, ValueType.OCTET_STRING, updater.get_phy_mfg_name)

    entPhysicalModelName = \
        SubtreeMIBEntry('1.13', updater, ValueType.OCTET_STRING, updater.get_phy_model_name)

    entPhysicalAlias = \
        SubtreeMIBEntry('1.14', updater, ValueType.OCTET_STRING, updater.get_phy_alias)

    entPhysicalAssetID = \
        SubtreeMIBEntry('1.15', updater, ValueType.OCTET_STRING, updater.get_phy_assert_id)

    entPhysicalIsFRU = \
        SubtreeMIBEntry('1.16', updater, ValueType.INTEGER, updater.is_fru)
