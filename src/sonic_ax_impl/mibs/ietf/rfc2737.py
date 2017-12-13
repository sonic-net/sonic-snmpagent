from enum import Enum, unique
from bisect import bisect_right

from swsssdk import ConfigDBConnector
from ax_interface import MIBMeta, MIBUpdater, ValueType, SubtreeMIBEntry


@unique
class PhysicalClass(int, Enum):
    """
    Physical classes defined in RFC 2737.
    """
    OTHER = 1
    UNKNOWN = 2
    CHASSIS = 3
    BACKPLANE = 4
    CONTAINER = 5
    POWERSUPPLY = 6
    FAN = 7
    SENSOR = 8
    MODULE = 9
    PORT = 10
    STACK = 11


class PhysicalTableMIBUpdater(MIBUpdater):

    DEVICE_METADATA = "DEVICE_METADATA"
    CHASSIS_ID = 1

    def __init__(self):
        super().__init__()

        self.configdb = ConfigDBConnector()
        self.configdb.connect()

        self.physical_classes = []
        self.physical_classes_map = {}

        self.reinit_data()

    def reinit_data(self):
        """
        Re-initialize all data.
        """
        device_metadata = self.configdb.get_table(self.DEVICE_METADATA)
        self.physical_classes = [(self.CHASSIS_ID, )]
        self.physical_classes_map = {
            (self.CHASSIS_ID, ): (PhysicalClass.CHASSIS,
                                  device_metadata["localhost"]["chassis_serial_number"])
        }

    def update_data(self):
        """
        Update сache.
        NOTE: Nothing to update right now. Implementation is required by framework.
        """
        return

    def get_next(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query.
        :return: the next sub id.
        """
        right = bisect_right(self.physical_classes, sub_id)
        if right == len(self.physical_classes):
            return None
        return self.physical_classes[right]


    def get_physical_class(self, sub_id):
        """
        Get physical class ID for specified subid.
        :param sub_id: The 1-based sub-identifier query. 
        :return: Physical class ID. 
        """
        data = self.physical_classes_map.get(sub_id)
        if not data:
            return

        return data[0]

    def get_serial_number(self, sub_id):
        """
        Get serial number for specified subid.
        :param sub_id: The 1-based sub-identifier query. 
        :return: Serial number. 
        """
        data = self.physical_classes_map.get(sub_id)
        if not data:
            return

        return data[1]


class PhysicalTableMIB(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.47.1.1.1'):
    updater = PhysicalTableMIBUpdater()

    entPhysicalClass = \
        SubtreeMIBEntry('1.5', updater, ValueType.INTEGER, updater.get_physical_class)

    entPhysicalSerialNum = \
        SubtreeMIBEntry('1.1.1.11', updater, ValueType.OCTET_STRING, updater.get_serial_number)