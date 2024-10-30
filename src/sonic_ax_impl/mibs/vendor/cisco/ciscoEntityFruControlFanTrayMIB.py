from enum import Enum, unique
from sonic_ax_impl import mibs
from ax_interface import MIBMeta, ValueType, SubtreeMIBEntry
import sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator as fru_oids
import re


PRESENCE_OK = 'true'
STATUS_OK = 'true'

@unique
class FanTrayInfoDB(str, Enum):
    """
    FAN info keys
    """
    PRESENCE = "presence"
    STATUS = "status"

def get_fantray_data(fantray_info):
    """
    :param chassis_info: chassis info dict
    :return: tuple (psu_num) of chassis;
    Empty string if field not in chassis_info
    """

    return tuple(fantray_info.get(field.value, "") for field in  FanTrayInfoDB)

class FanStatusHandler:
    """
    Class to handle the SNMP request
    """
    def __init__(self):
        """
        init the handler
        """
        self.statedb = mibs.init_db()
        self.statedb.connect(self.statedb.STATE_DB)
        self.init_fan_trays()

    def init_fan_trays(self):
        fan_trays = self.statedb.keys(self.statedb.STATE_DB,
                'FAN_DRAWER_INFO' + mibs.TABLE_NAME_SEPARATOR_VBAR + '*')
        if not fan_trays:
            mibs.logger.debug('No fan trays found in {}'.format(fan_trays))
            return None
        fan_trays = sorted(fan_trays)
        positions = [int(re.findall(r'\d+', s)[0]) for s in fan_trays]
        oids = [fru_oids.get_fan_drawer_sub_id(pos) for pos in positions]
        self.oids = oids
        self.fan_trays = fan_trays

    def get_next(self, sub_id):
        """
        :param sub_id: The 1-based snmp sub-identifier query.
        :return: the next sub id.
        """
        if not sub_id:
            self.init_fan_trays()
            return (1, )

        index = sub_id[0]
        if index >= len(self.fan_trays):
            return None

        return (index + 1,)

    def _get_fantray_status(self, oid):
        """
        :return: oper status of requested sub_id according to cefcFanTrayOperStatus
                 1 - unknown
                 2 - ok
                 3 - down
                 4 - warning
        :ref: https://mibbrowser.online/mibdb_search.php?mib=CISCO-ENTITY-FRU-CONTROL-MIB
        """
        fantray_name = self.fan_trays[oid - 1]
        fantray_info = self.statedb.get_all(self.statedb.STATE_DB, fantray_name)
        presence, status = get_fantray_data(fantray_info)
        mibs.logger.debug('Fantray {} name {} presence {} status {}'.format(oid, fantray_name, presence, status))
        if presence.lower() == "true" and status.lower() == "true":
                return 2
        return 3

    def get_fantray_status(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query. Only iterate the entity
        :              of type FAN
        :return: oper status of requested sub_id according to cefcFanTrayOperStatus
                 1 - unknown
                 2 - ok
                 3 - down
                 4 - warning
        :ref: https://mibbrowser.online/mibdb_search.php?mib=CISCO-ENTITY-FRU-CONTROL-MIB
        """
        if not sub_id:
            return None

        return self._get_fantray_status(sub_id[0])

class cefcFruFanTrayStatusTable(metaclass=MIBMeta, prefix='.1.3.6.1.4.1.9.9.117.1.4.1'):
    """
    'cefcFruFanStatusTable' http://oidref.com/.1.3.6.1.4.1.9.9.117.1.4.1
    """
    handler = FanStatusHandler()
    fan_status = SubtreeMIBEntry('1.1', handler, ValueType.INTEGER, handler.get_fantray_status)
