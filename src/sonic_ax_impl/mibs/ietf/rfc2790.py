from enum import Enum, unique
from sonic_ax_impl import mibs
from ax_interface import MIBMeta, ValueType, SubtreeMIBEntry
import sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator as fru_oids
import re

@unique
class hrFSinfoDB(str, Enum):
    """
    hr FS info keys
    """
    TYPE = "Type"
    MOUNT = "MountPoint"

def get_FS_data(fs_info):
    """
    :param chassis_info: chassis info dict
    :return: tuple of chassis;
    Empty string if field not in chassis_info
    """
    return tuple(fs_info.get(field.value, "") for field in hrFSinfoDB)

class fsHandler:
    """
    Class to handle the SNMP request
    """
    def __init__(self):
        """
        init the handler
        """
        self.statedb = mibs.init_db()
        self.statedb.connect(self.statedb.STATE_DB)
        self.init_fs()

    def init_fs(self):
        fs_entries = self.statedb.keys(self.statedb.STATE_DB,
                'MOUNT_POINTS' + mibs.TABLE_NAME_SEPARATOR_VBAR + '*')
        if not fs_entries:
            mibs.logger.debug('No mount point found in {}'.format(fs_entries))
            return None
        fs_entries = sorted(fs_entries)
        self.fs_entries = fs_entries

    def get_next(self, sub_id):
        """
        :param sub_id: The 1-based snmp sub-identifier query.
        :return: the next sub id.
        """
        if not sub_id:
            self.init_fs()
            return (1, )

        index = sub_id[0]
        if index >= len(self.fs_entries):
            return None

        return (index + 1,)


    # Type of FS entry
    def _get_fs_type(self, oid):
        """
        :return: Type of requested sub_id according to hrFSTable 
        :ref: https://mibbrowser.online/mibdb_search.php?mib=HOST-RESOURCES-V2-MIB
        """
        fs_name = self.fs_entries[oid]
        fs_info = self.statedb.get_all(self.statedb.STATE_DB, fs_name)
        fs_type, fs_mount = get_FS_data(fs_info)
        mibs.logger.debug('fs storage info {} name {} type {}'.format(oid, fs_name, fs_type))

        return fs_type

    def get_fs_type(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query. Only iterate through the MOUNTPOINT
        :return: Type of requested sub_id according to hrFSTable 
        :ref: https://mibbrowser.online/mibdb_search.php?mib=HOST-RESOURCES-V2-MIB
        """
        if not sub_id:
            return None

        return self._get_fs_type(sub_id[0]-1)

    # Mountpoint of FS entry 
    def _get_fs_mount(self, oid):
        """
        :return: Mountpoint of requested sub_id according to hrFSTable 
        :ref: https://mibbrowser.online/mibdb_search.php?mib=HOST-RESOURCES-V2-MIB
        """
        fs_name = self.fs_entries[oid]
        fs_info = self.statedb.get_all(self.statedb.STATE_DB, fs_name)

        mount_str = fs_name.split('|')[1]
        mibs.logger.debug('fs storage info {} name {} mountpoint {}'.format(oid, fs_name, mount_str))
        ret_str = mount_str.encode('utf-8')
        return ret_str

    def get_fs_mount(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query. Only iterate through the MOUNTPOINT
        :return: Mountpoint of requested sub_id according to hrFSTable 
        :ref: https://mibbrowser.online/mibdb_search.php?mib=HOST-RESOURCES-V2-MIB
        """
        if not sub_id:
            return None
        return self._get_fs_mount(sub_id[0]-1)


class hrFSTable(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.25.3.8'):
    """
    'hrFSTable' http://oidref.com/1.3.6.1.2.1.25.3.8
    """
    handler = fsHandler()
    fsMountpoint = SubtreeMIBEntry('1.2', handler, ValueType.OCTET_STRING, handler.get_fs_mount)
    fsType = SubtreeMIBEntry('1.4', handler, ValueType.OCTET_STRING, handler.get_fs_type)


# =======================
@unique
class hrStorageInfoDB(str, Enum):
    """
    hr Storage info keys
    """
    KBLOCKS = "1K-blocks"
    USED = "Used"
    FILESYSTEM = "Filesystem"

def get_hrStorage_data(hrStorage_info):
    """
    :param chassis_info: chassis info dict
    :return: tuple of chassis;
    Empty string if field not in chassis_info
    """
    return tuple(hrStorage_info.get(field.value, "") for field in hrStorageInfoDB)

class hrStorageHandler:
    """
    Class to handle the SNMP request
    """
    def __init__(self):
        """
        init the handler
        """
        self.statedb = mibs.init_db()
        self.statedb.connect(self.statedb.STATE_DB)
        self.init_hr_storage()

    def init_hr_storage(self):
        hr_storage_entries = self.statedb.keys(self.statedb.STATE_DB,
                'MOUNT_POINTS' + mibs.TABLE_NAME_SEPARATOR_VBAR + '*')
        if not hr_storage_entries:
            mibs.logger.debug('No mount point found in {}'.format(hr_storage_entries))
            return None
        hr_storage_entries = sorted(hr_storage_entries)
        self.hr_storage_entries = hr_storage_entries 

    def get_next(self, sub_id):
        """
        :param sub_id: The 1-based snmp sub-identifier query.
        :return: the next sub id.
        """
        if not sub_id:
            self.init_hr_storage()
            return (1, )

        index = sub_id[0]
        if index >= len(self.hr_storage_entries):
            return None

        return (index + 1,)


    # Used space of HRStorage
    def _get_hrstorage_used(self, oid):
        """
        :return: Used space of requested sub_id according to hrStorageTable 
        :ref: https://mibbrowser.online/mibdb_search.php?mib=HOST-RESOURCES-V2-MIB
        """
        hrstorage_name = self.hr_storage_entries[oid]
        hrstorage_info = self.statedb.get_all(self.statedb.STATE_DB, hrstorage_name)
        kblocks, used, filesystem = get_hrStorage_data(hrstorage_info)
        mibs.logger.debug('hr storage info {} name {} used {}'.format(oid, hrstorage_name, used))

        used_num = int(used)
        return used_num 

    def get_hrstorage_used(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query. Only iterate through the MOUNTPOINT
        :return: Used space of requested sub_id according to hrStorageTable
        :ref: https://mibbrowser.online/mibdb_search.php?mib=HOST-RESOURCES-V2-MIB
        """
        if not sub_id:
            return None

        return self._get_hrstorage_used(sub_id[0]-1)


    """
    get_hrstorage_size will return 65536 if the output of 1k blocks (in df -T) is 65536 1k-blocks.
    hrStorageAllocationUnits (1.3.6.1.2.1.25.2.3.1.4) is an int_32 represents the size in bytes  
    hrStorageSize            (1.3.6.1.2.1.25.2.3.1.5) is an int_32 represents the size of storage in units of hrStorageAllocationUnits
    """
    # Size of HRStorage 
    def _get_hrstorage_size(self, oid):
        """
        :return: Size of requested sub_id according to hrStorageTable 
        :ref: https://mibbrowser.online/mibdb_search.php?mib=HOST-RESOURCES-V2-MIB
        """
        hrstorage_name = self.hr_storage_entries[oid]
        hrstorage_info = self.statedb.get_all(self.statedb.STATE_DB, hrstorage_name)
        kblocks, used, filesystem = get_hrStorage_data(hrstorage_info)
        mibs.logger.debug('hr storage info {} name {} size {}'.format(oid, hrstorage_name, kblocks))

        size_num = int(kblocks)
        return size_num

    def get_hrstorage_size(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query. Only iterate through the MOUNTPOINT
        :return: Size of requested sub_id according to hrStorageTable
        :ref: https://mibbrowser.online/mibdb_search.php?mib=HOST-RESOURCES-V2-MIB
        """
        if not sub_id:
            return None
        return self._get_hrstorage_size(sub_id[0]-1)


    # Description of the filesystem of HRStorage
    def _get_hrstorage_descr(self, oid):
        """
        :return: Description of requested sub_id according to hrStorageTable 
        :ref: https://mibbrowser.online/mibdb_search.php?mib=HOST-RESOURCES-V2-MIB
        """
        hrstorage_name = self.hr_storage_entries[oid]
        hrstorage_info = self.statedb.get_all(self.statedb.STATE_DB, hrstorage_name)
        kblocks, used, filesystem = get_hrStorage_data(hrstorage_info)
        mibs.logger.debug('hr storage info {} name {} filesystem {}'.format(oid, hrstorage_name, filesystem))
        return filesystem 

    def get_hrstorage_descr (self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query. Only iterate through the MOUNTPOINT
        :return: Descr of requested sub_id according to hrStorageTable
        :ref: https://mibbrowser.online/mibdb_search.php?mib=HOST-RESOURCES-V2-MIB
        """
        if not sub_id:
            return None
        return self._get_hrstorage_descr(sub_id[0]-1)


    # Alloc units of the filesystem of HRStorage
    def _get_hrstorage_alloc(self, oid):
        """
        :return: Allocation units of requested sub_id according to hrStorageTable 
        :ref: https://mibbrowser.online/mibdb_search.php?mib=HOST-RESOURCES-V2-MIB
        """
        return 1024

    def get_hrstorage_alloc(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query. Only iterate through the MOUNTPOINT
        :return: Alloc units of requested sub_id according to hrStorageTable
        :ref: https://mibbrowser.online/mibdb_search.php?mib=HOST-RESOURCES-V2-MIB
        """
        if not sub_id:
            return None
        return self._get_hrstorage_alloc(sub_id[0]-1)


class hrStorageTable(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.25.2.3'):
    """
    'hrStorageTable' http://oidref.com/1.3.6.1.2.1.25.2.3
    """
    handler = hrStorageHandler()
    hrStorageDescr = SubtreeMIBEntry('1.3', handler, ValueType.OCTET_STRING, handler.get_hrstorage_descr)
    hrStorageAlloc = SubtreeMIBEntry('1.4', handler, ValueType.INTEGER, handler.get_hrstorage_alloc)
    hrStorageSize = SubtreeMIBEntry('1.5', handler, ValueType.INTEGER, handler.get_hrstorage_size)
    hrStorageUsed = SubtreeMIBEntry('1.6', handler, ValueType.INTEGER, handler.get_hrstorage_used)
