"""
MIB implementation defined in RFC 2737
"""

from enum import Enum, unique
from bisect import bisect_right, insort_right

from swsssdk import port_util
from ax_interface import MIBMeta, MIBUpdater, ValueType, SubtreeMIBEntry

from sonic_ax_impl import mibs
from sonic_ax_impl.mibs import Namespace

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


@unique
class XcvrInfoDB(bytes, Enum):
    """
    Transceiver info keys
    """

    TYPE              = b"type"
    HARDWARE_REVISION = b"hardwarerev"
    SERIAL_NUMBER     = b"serialnum"
    MANUFACTURE_NAME  = b"manufacturename"
    MODEL_NAME        = b"modelname"


# Map used to generate sensor description
SENSOR_NAME_MAP = {
    "temperature" : "Temperature",
    "voltage"     : "Voltage",
    "rx1power"    : "RX Power",
    "rx2power"    : "RX Power",
    "rx3power"    : "RX Power",
    "rx4power"    : "RX Power",
    "tx1bias"     : "TX Bias",
    "tx2bias"     : "TX Bias",
    "tx3bias"     : "TX Bias",
    "tx4bias"     : "TX Bias",
    "tx1power"    : "TX Power",
    "tx2power"    : "TX Power",
    "tx3power"    : "TX Power",
    "tx4power"    : "TX Power",
}

QSFP_LANES = (1, 2, 3, 4)


def get_transceiver_data(xcvr_info):
    """
    :param xcvr_info: transceiver info dict
    :return: tuple (type, hw_version, mfg_name, model_name) of transceiver;
    Empty string if field not in xcvr_info
    """

    return (xcvr_info.get(xcvr_field.value, b"").decode()
            for xcvr_field in XcvrInfoDB)


def get_transceiver_description(sfp_type, if_alias):
    """
    :param sfp_type: SFP type of transceiver
    :param if_alias: Port alias name
    :return: Transceiver decsription
    """

    return "{} for {}".format(sfp_type, if_alias)

def get_transceiver_sensor_description(sensor, if_alias):
    """
    :param sensor: sensor key name
    :param if_alias: interface alias
    :return: description string about sensor
    """

    # assume sensors that is per channel in transceiver port
    # has digit equals to channel number in the sensor's key name in DB
    # e.g. rx3power (lane 3)
    lane_number = list(filter(lambda c: c.isdigit(), sensor))

    if len(lane_number) == 0:
        port_name = if_alias
    elif len(lane_number) == 1 and int(lane_number[0]) in QSFP_LANES:
        port_name = "{}/{}".format(if_alias, lane_number[0])
    else:
        mibs.logger.warning("Tried to parse lane number from sensor name - {} ".format(sensor)
                + "but parsed value is not a valid QSFP lane number")
        # continue as with non per channel sensor
        port_name = if_alias

    return "DOM {} Sensor for {}".format(SENSOR_NAME_MAP[sensor], port_name)


class PhysicalTableMIBUpdater(MIBUpdater):
    """
    Updater class for physical table MIB
    """

    CHASSIS_ID = 1
    TRANSCEIVER_KEY_PATTERN = mibs.transceiver_info_table("*")

    def __init__(self):
        super().__init__()

        self.statedb = Namespace.init_namespace_dbs()
        Namespace.connect_all_dbs(self.statedb, mibs.STATE_DB)

        self.if_alias_map = {}

        # List of available sub OIDs.
        self.physical_entities = []

        # Map sub ID to its data.
        self.physical_classes_map = {}
        self.physical_description_map = {}
        self.physical_hw_version_map = {}
        self.physical_serial_number_map = {}
        self.physical_mfg_name_map = {}
        self.physical_model_name_map = {}

        self.pubsub = [None] * len(self.statedb)

    def reinit_data(self):
        """
        Re-initialize all data.
        """

        # reinit cache
        self.physical_classes_map = {}
        self.physical_description_map = {}
        self.physical_hw_version_map = {}
        self.physical_serial_number_map = {}
        self.physical_mfg_name_map = {}
        self.physical_model_name_map = {}

        # update interface maps
        _, self.if_alias_map, _, _, _, _ = \
            Namespace.init_namespace_sync_d_interface_tables(Namespace.init_namespace_dbs())

        device_metadata = mibs.get_device_metadata(self.statedb[0])
        chassis_sub_id = (self.CHASSIS_ID, )
        self.physical_entities = [chassis_sub_id]

        if not device_metadata or not device_metadata.get(b"chassis_serial_number"):
            chassis_serial_number = ""
        else:
            chassis_serial_number = device_metadata[b"chassis_serial_number"]

        self.physical_classes_map[chassis_sub_id] = PhysicalClass.CHASSIS
        self.physical_serial_number_map[chassis_sub_id] = chassis_serial_number

        # retrieve the initial list of transceivers that are present in the system
        transceiver_info = Namespace.dbs_keys(self.statedb, mibs.STATE_DB, self.TRANSCEIVER_KEY_PATTERN)
        if transceiver_info:
            self.transceiver_entries = [entry.decode() \
                for entry in transceiver_info]
        else:
            self.transceiver_entries = []

        # update cache with initial data
        for transceiver_entry in self.transceiver_entries:
            # extract interface name
            interface = transceiver_entry.split(mibs.TABLE_NAME_SEPARATOR_VBAR)[-1]
            self._update_transceiver_cache(interface)

    def _update_per_namespace_data(self, pubsub):
        """
        Update cache.
        Here we listen to changes in STATE_DB TRANSCEIVER_INFO table
        and update data only when there is a change (SET, DELETE)
        """

        # This code is not executed in unit test, since mockredis
        # does not support pubsub
        while True:
            msg = pubsub.get_message()

            if not msg:
                break

            transceiver_entry = msg["channel"].split(b":")[-1].decode()
            data = msg['data'] # event data

            # extract interface name
            interface = transceiver_entry.split(mibs.TABLE_NAME_SEPARATOR_VBAR)[-1]

            # get interface from interface name
            ifindex = port_util.get_index_from_str(interface)

            if ifindex is None:
                # interface name invalid, skip this entry
                mibs.logger.warning(
                    "Invalid interface name in {} \
                     in STATE_DB, skipping".format(transceiver_entry))
                continue

            if b"set" in data:
                self._update_transceiver_cache(interface)
            elif b"del" in data:
                # remove deleted transceiver
                remove_sub_ids = [mibs.get_transceiver_sub_id(ifindex)]

                # remove all sensor OIDs associated with removed transceiver
                for sensor in SENSOR_NAME_MAP:
                    remove_sub_ids.append(mibs.get_transceiver_sensor_sub_id(ifindex, sensor))

                for sub_id in remove_sub_ids:
                    if sub_id and sub_id in self.physical_entities:
                        self.physical_entities.remove(sub_id)

    def update_data(self):
        # This code is not executed in unit test, since mockredis
        # does not support pubsub
        for i in range(len(self.statedb)):
            if not self.pubsub[i]:
                pattern = self.TRANSCEIVER_KEY_PATTERN
                self.pubsub[i] = mibs.get_redis_pubsub(self.statedb[i], self.statedb[i].STATE_DB, pattern)
            self._update_per_namespace_data(self.pubsub[i])

    def _update_transceiver_cache(self, interface):
        """
        Update data for single transceiver
        :param: interface: Interface name associated with transceiver
        """

        # get interface from interface name
        ifindex = port_util.get_index_from_str(interface)

        # update xcvr info from DB
        # use port's name as key for transceiver info entries
        sub_id = mibs.get_transceiver_sub_id(ifindex)

        # add interface to available OID list
        insort_right(self.physical_entities, sub_id)

        # get transceiver information from transceiver info entry in STATE DB
        transceiver_info = Namespace.dbs_get_all(self.statedb, mibs.STATE_DB,
                                                mibs.transceiver_info_table(interface))

        if not transceiver_info:
            return

        # physical class - network port
        self.physical_classes_map[sub_id] = PhysicalClass.PORT

        # save values into cache
        sfp_type, \
        self.physical_hw_version_map[sub_id],\
        self.physical_serial_number_map[sub_id], \
        self.physical_mfg_name_map[sub_id], \
        self.physical_model_name_map[sub_id] = get_transceiver_data(transceiver_info)

        ifalias = self.if_alias_map.get(interface.encode(), b"").decode()

        # generate a description for this transceiver
        self.physical_description_map[sub_id] = get_transceiver_description(sfp_type, ifalias)

        # update transceiver sensor cache
        self._update_transceiver_sensor_cache(interface)

    def _update_transceiver_sensor_cache(self, interface):
        """
        Update sensor data for single transceiver
        :param: interface: Interface name associated with transceiver
        """

        ifalias = self.if_alias_map.get(interface.encode(), b"").decode()
        ifindex = port_util.get_index_from_str(interface)

        # get transceiver sensors from transceiver dom entry in STATE DB
        transceiver_dom_entry = Namespace.dbs_get_all(self.statedb, mibs.STATE_DB,
                                                     mibs.transceiver_dom_table(interface))

        if not transceiver_dom_entry:
            return

        # go over transceiver sensors
        for sensor in map(bytes.decode, transceiver_dom_entry):
            if sensor not in SENSOR_NAME_MAP:
                continue
            sensor_sub_id = mibs.get_transceiver_sensor_sub_id(ifindex, sensor)
            sensor_description = get_transceiver_sensor_description(sensor, ifalias)

            self.physical_classes_map[sensor_sub_id] = PhysicalClass.SENSOR
            self.physical_description_map[sensor_sub_id] = sensor_description

            # add to available OIDs list
            insort_right(self.physical_entities, sensor_sub_id)

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

    def get_phy_descr(self, sub_id):
        """
        :param sub_id: sub OID
        :return: description string for this OID
        """

        if sub_id in self.physical_entities:
            return self.physical_description_map.get(sub_id, "")
        return None

    def get_phy_name(self, sub_id):
        """
        :param sub_id: sub OID
        :return: name string for this OID
        """

        return "" if sub_id in self.physical_entities else None

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


class PhysicalTableMIB(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.47.1.1.1'):
    """
    Physical table
    """

    updater = PhysicalTableMIBUpdater()

    entPhysicalDescr = \
        SubtreeMIBEntry('1.2', updater, ValueType.OCTET_STRING, updater.get_phy_descr)

    entPhysicalClass = \
        SubtreeMIBEntry('1.5', updater, ValueType.INTEGER, updater.get_phy_class)

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
