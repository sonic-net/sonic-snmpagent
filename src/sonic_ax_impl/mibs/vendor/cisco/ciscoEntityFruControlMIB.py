from enum import Enum, unique
from sonic_ax_impl import mibs
from ax_interface import MIBMeta, ValueType, SubtreeMIBEntry
from natsort import natsorted

CHASSIS_INFO_KEY_TEMPLATE = 'chassis {}'
PSU_INFO_KEY_TEMPLATE = 'PSU {}'

PSU_PRESENCE_OK = 'true'
PSU_STATUS_OK = 'true'

@unique
class CHASSISInfoDB(str, Enum):
    """
    CHASSIS info keys
    """

    PSU_NUM = "psu_num"

@unique
class PSUInfoDB(str, Enum):
    """
    PSU info keys
    """

    PRESENCE = "presence"
    STATUS = "status"

def get_chassis_data(chassis_info):
    """
    :param chassis_info: chassis info dict
    :return: tuple (psu_num) of chassis;
    Empty string if field not in chassis_info
    """

    return tuple(chassis_info.get(chassis_field.value, "") for chassis_field in CHASSISInfoDB)

def get_psu_data(psu_info):
    """
    :param psu_info: psu info dict
    :return: tuple (presence, status) of psu;
    Empty string if field not in psu_info
    """

    return tuple(psu_info.get(psu_field.value, "") for psu_field in PSUInfoDB)

class PowerStatusHandler:
    """
    Class to handle the SNMP request
    """
    def __init__(self):
        """
        init the handler
        """
        self.statedb = mibs.init_db()
        self.statedb.connect(self.statedb.STATE_DB)

    def _get_num_psus(self):
        """
        Get PSU number
        :return: the number of supported PSU
        """
        chassis_name = CHASSIS_INFO_KEY_TEMPLATE.format(1)
        chassis_info = self.statedb.get_all(self.statedb.STATE_DB, mibs.chassis_info_table(chassis_name))
        num_psus = get_chassis_data(chassis_info)

        return int(num_psus[0])

    def _get_psu_presence(self, psu_index):
        """
        Get PSU presence
        :return: the presence of particular PSU
        """
        psu_keys = natsorted(self.statedb.keys(self.statedb.STATE_DB, "PSU_INFO|*"))
        psu_name = psu_keys[psu_index-1].removeprefix("PSU_INFO|")
        psu_info = self.statedb.get_all(self.statedb.STATE_DB, mibs.psu_info_table(psu_name))
        presence, status = get_psu_data(psu_info)

        return presence == PSU_PRESENCE_OK

    def _get_psu_status(self, psu_index):
        """
        Get PSU status
        :return: the status of particular PSU
        """
        psu_keys = natsorted(self.statedb.keys(self.statedb.STATE_DB, "PSU_INFO|*"))
        psu_name = psu_keys[psu_index-1].removeprefix("PSU_INFO|")
        psu_info = self.statedb.get_all(self.statedb.STATE_DB, mibs.psu_info_table(psu_name))
        presence, status = get_psu_data(psu_info)

        return status == PSU_STATUS_OK

    def _get_psu_index(self, sub_id):
        """
        Get the PSU index from sub_id
        :return: the index of supported PSU
        """
        if not sub_id or len(sub_id) > 1:
            return None

        psu_index = int(sub_id[0])

        try:
            num_psus = self._get_num_psus()
        except Exception:
            # Any unexpected exception or error, log it and keep running
            mibs.logger.exception("PowerStatusHandler._get_psu_index() caught an unexpected exception during _get_num_psus()")
            return None

        if psu_index < 1 or psu_index > num_psus:
            return None

        return psu_index

    def get_next(self, sub_id):
        """
        :param sub_id: The 1-based snmp sub-identifier query.
        :return: the next sub id.
        """
        if not sub_id:
            return (1,)

        psu_index = self._get_psu_index(sub_id)
        try:
            num_psus = self._get_num_psus()
        except Exception:
            # Any unexpected exception or error, log it and keep running
            mibs.logger.exception("PowerStatusHandler.get_next() caught an unexpected exception during _get_num_psus()")
            return None

        if psu_index and psu_index + 1 <= num_psus:
            return (psu_index + 1,)

        return None

    def get_psu_status(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query.
        :return: the status of requested PSU according to cefcModuleOperStatus ModuleOperType
                 2 - PSU has correct functionalling - ok
                 7 - PSU has a problem with functionalling - failed
                 8 - the module is provisioned, but it is missing. This is a failure state.
        :ref: https://www.cisco.com/c/en/us/td/docs/switches/wan/mgx/mgx_8850/software/mgx_r2-0-10/pxm/reference/guide/pxm/cscoent.html
        """
        psu_index = self._get_psu_index(sub_id)

        if not psu_index:
            return None

        try:
            psu_presence = self._get_psu_presence(psu_index)
        except Exception:
            # Any unexpected exception or error, log it and keep running
            mibs.logger.exception("PowerStatusHandler.get_psu_status() caught an unexpected exception during _get_psu_presence()")
            return None

        if psu_presence:
            try:
                psu_status = self._get_psu_status(psu_index)
            except Exception:
                # Any unexpected exception or error, log it and keep running
                mibs.logger.exception("PowerStatusHandler.get_psu_status() caught an unexpected exception during _get_psu_status()")
                return None

            if psu_status:
                return 2

            return 7
        else:
            return 8

class cefcFruPowerStatusTable(metaclass=MIBMeta, prefix='.1.3.6.1.4.1.9.9.117.1.1.2'):
    """
    'cefcFruPowerStatusTable' http://oidref.com/1.3.6.1.4.1.9.9.117.1.1.2
    """

    power_status_handler = PowerStatusHandler()

    # cefcFruPowerStatusTable = '1.3.6.1.4.1.9.9.117.1.1.2'
    # csqIfQosGroupStatsEntry = '1.3.6.1.4.1.9.9.117.1.1.2.1'

    psu_status = SubtreeMIBEntry('1.2', power_status_handler, ValueType.INTEGER, power_status_handler.get_psu_status)
