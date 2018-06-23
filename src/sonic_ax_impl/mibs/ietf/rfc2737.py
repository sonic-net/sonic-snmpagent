"""
MIB implementation defined in RFC 2737
"""

from enum import Enum, unique
from bisect import bisect_right

from swsssdk import SonicV2Connector, port_util
from ax_interface import MIBMeta, MIBUpdater, ValueType, SubtreeMIBEntry

from sonic_ax_impl import mibs

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
}


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
    TRANSCEIVER_KEY_PATTERN =  mibs.transceiver_info_table("*")

    def __init__(self):
        super().__init__()

        self.statedb = SonicV2Connector()
        self.statedb.connect(self.statedb.STATE_DB)

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

        device_metadata = mibs.get_device_metadata(self.statedb)
        chassis_sub_id = (self.CHASSIS_ID, )
        self.physical_entities = [chassis_sub_id]

        if not device_metadata or not device_metadata.get(b"chassis_serial_number"):
            chassis_serial_number = ""
        else:
            chassis_serial_number = device_metadata[b"chassis_serial_number"]

        self.physical_classes_map[chassis_sub_id] = PhysicalClass.CHASSIS
        self.physical_serial_number_map[chassis_sub_id] = chassis_serial_number

        # update interface maps
        _, self.if_alias_map, _, _, _ = \
            mibs.init_sync_d_interface_tables(SonicV2Connector())

    def update_data(self):
        """
        Update cache.
        """

        chassis_sub_id = (self.CHASSIS_ID, )
        self.physical_entities = [chassis_sub_id]

        self.transceiver_entries = [entry.decode() \
            for entry in self.statedb.keys(self.statedb.STATE_DB,
                                           self.TRANSCEIVER_KEY_PATTERN)]

        if not self.transceiver_entries:
            # nothing in DB
            return

        # update xcvr info from DB
        # use port's name as key for transceiver info entries
        for transceiver_entry in self.transceiver_entries:
            # extract interface name
            interface = transceiver_entry.split(mibs.TABLE_NAME_SEPERATOR_VBAR)[-1]

            ifalias = self.if_alias_map.get(interface.encode(), b"").decode()

            # get interface from interface name
            ifindex = port_util.get_index_from_str(interface)

            if ifindex is None:
                # interface name invalid, skip this entry
                mibs.logger.warning(
                    "Invalid interface name in {} \
                     in STATE_DB, skipping".format(transceiver_entry))
                continue

            # get transceiver information from transceiver info entry in STATE DB
            transceiver_info = self.statedb.get_all(self.statedb.STATE_DB,
                                                    transceiver_entry)

            if not transceiver_info:
                continue

            # get sub OID based on interface index
            sub_id = mibs.get_transceiver_sub_id(ifindex)

            # add interface to available OID list
            self.physical_entities.append(sub_id)

            # physical class - network port
            self.physical_classes_map[sub_id] = PhysicalClass.PORT

            # save values into cache
            sfp_type, \
            self.physical_hw_version_map[sub_id],\
            self.physical_serial_number_map[sub_id], \
            self.physical_mfg_name_map[sub_id], \
            self.physical_model_name_map[sub_id] = get_transceiver_data(transceiver_info)

            # generate a description for this transceiver
            self.physical_description_map[sub_id] = get_transceiver_description(sfp_type, ifalias)

            # get transceiver sensors from transceiver dom entry in STATE DB
            transceiver_dom_entry = self.statedb.get_all(self.statedb.STATE_DB,
                                                         mibs.transceiver_dom_table(interface))

            if not transceiver_dom_entry:
                continue

            # go over transceiver sensors
            for sensor in map(bytes.decode, transceiver_dom_entry):
                if sensor not in SENSOR_NAME_MAP:
                    continue
                sensor_sub_id = mibs.get_transceiver_sensor_sub_id(ifindex, sensor)
                sensor_description = get_transceiver_sensor_description(sensor, ifalias)

                self.physical_classes_map[sensor_sub_id] = PhysicalClass.SENSOR
                self.physical_description_map[sensor_sub_id] = sensor_description

                # add to available OIDs list
                self.physical_entities.append(sensor_sub_id)

        self.physical_entities.sort()


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
