from enum import Enum, unique
from sonic_ax_impl import mibs
from ax_interface import MIBMeta, MIBUpdater, ValueType, SubtreeMIBEntry
import sonic_ax_impl.mibs.ietf.physical_entity_sub_oid_generator as fru_oids
import re

@unique
class hrFSinfoDB(str, Enum):
    """
    hr FS info keys
    """
    TYPE = "Type"
    MOUNT = "MountPoint"

def _db_call(func, context, *args):
    """Execute a STATE_DB operation, returning None on access failure."""
    try:
        return func(*args)
    except Exception as e:
        mibs.logger.error('Failed to access STATE_DB for {}: Reason: {}'.format(context, e))
        return None

def get_FS_data(fs_info):
    """
    :param chassis_info: chassis info dict
    :return: tuple of chassis;
    Empty string if field not in chassis_info
    """
    return tuple(fs_info.get(field.value, "") for field in hrFSinfoDB)

class fsHandler(MIBUpdater):
    """
    Class to handle the SNMP request
    """
    def __init__(self):
        """
        init the handler
        """
        super().__init__()
        self.fs_entries = []
        self.statedb = mibs.init_db()
        _db_call(self.statedb.connect, 'STATE_DB connect', self.statedb.STATE_DB)
        self.init_fs()

    def reinit_data(self):
        self.init_fs()

    def update_data(self):
        pass

    def init_fs(self):
        self.fs_entries = []

        fs_entries = _db_call(self.statedb.keys, 'MOUNT_POINTS',
                self.statedb.STATE_DB, 'MOUNT_POINTS' + mibs.TABLE_NAME_SEPARATOR_VBAR + '*')
        if fs_entries is None:
            fs_entries = []
        elif not fs_entries:
            mibs.logger.info('init_fs - No mount point found in STATE_DB MOUNT_POINTS table')

        sorted_fs_entries = sorted(fs_entries)

        for entry in fs_entries:
            fs_info = _db_call(self.statedb.get_all, entry, self.statedb.STATE_DB, entry)
            if not fs_info:
                mibs.logger.info('Failed to get data for entry {}'.format(entry))
                sorted_fs_entries.remove(entry)
                continue
            fs_type, fs_mount = get_FS_data(fs_info)
            if fs_type == "" and fs_mount == "":
                sorted_fs_entries.remove(entry) 

        physical_memory_entries = _db_call(self.statedb.keys, 'MEMORY_STATS',
                self.statedb.STATE_DB, 'MEMORY_STATS' + mibs.TABLE_NAME_SEPARATOR_VBAR + '*')
        if physical_memory_entries is None:
            physical_memory_entries = []
        elif not physical_memory_entries:
            mibs.logger.info('init_fs - No memory stats found in STATE_DB MEMORY_STATS table')

        sorted_fs_entries += physical_memory_entries
        self.fs_entries = sorted_fs_entries

    def get_next(self, sub_id):
        """
        :param sub_id: The 1-based snmp sub-identifier query.
        :return: the next sub id.
        """
        if not sub_id:
            self.init_fs()
            if not self.fs_entries:
                return None
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
        if oid >= len(self.fs_entries):
            mibs.logger.info('fs_type - Index out of range. Size of fs_entries: {}'.format(len(self.fs_entries)))
            return None
        fs_name = self.fs_entries[oid]
        fs_info = _db_call(self.statedb.get_all, fs_name, self.statedb.STATE_DB, fs_name)
        if not fs_info:
            mibs.logger.info('get_all() returned empty data for {}'.format(fs_name))
            return None
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
        if oid >= len(self.fs_entries):
            mibs.logger.info('fs_mount - Index out of range. Size of fs_entries: {}'.format(len(self.fs_entries)))
            return None
        fs_name = self.fs_entries[oid]
        fs_info = _db_call(self.statedb.get_all, fs_name, self.statedb.STATE_DB, fs_name)
        if not fs_info:
            mibs.logger.info('get_all() returned empty data for {}'.format(fs_name))
            return None

        mount_str = fs_name.split('|')[1]
        mibs.logger.debug('fs storage info {} name {} mountpoint {}'.format(oid, fs_name, mount_str))
        ret_str = mount_str.encode('utf-8')

        if fs_name.split('|')[0] == "MEMORY_STATS":
            ret_str = ""

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

class hrStorageHandler(MIBUpdater):
    """
    Class to handle the SNMP request
    """
    def __init__(self):
        """
        init the handler
        """
        super().__init__()
        self.hr_storage_entries = []
        self.statedb = mibs.init_db()
        _db_call(self.statedb.connect, 'STATE_DB connect', self.statedb.STATE_DB)
        self.init_hr_storage()

    def reinit_data(self):
        self.init_hr_storage()

    def update_data(self):
        pass

    def init_hr_storage(self):
        self.hr_storage_entries = []

        hr_storage_entries = _db_call(self.statedb.keys, 'MOUNT_POINTS',
                self.statedb.STATE_DB, 'MOUNT_POINTS' + mibs.TABLE_NAME_SEPARATOR_VBAR + '*')
        if hr_storage_entries is None:
            hr_storage_entries = []
        elif not hr_storage_entries:
            mibs.logger.info('init_hr_storage - No mount point found in STATE_DB MOUNT_POINTS table')

        sorted_hr_storage_entries = sorted(hr_storage_entries)

        for entry in hr_storage_entries:
            hr_info = _db_call(self.statedb.get_all, entry, self.statedb.STATE_DB, entry)
            if not hr_info:
                mibs.logger.info('Failed to get data for entry {}'.format(entry))
                sorted_hr_storage_entries.remove(entry)
                continue
            hr_block, hr_used, hr_fs = get_hrStorage_data(hr_info)
            if hr_block == "" and hr_used == "" and hr_fs == "":
                sorted_hr_storage_entries.remove(entry)

        physical_memory_entries = _db_call(self.statedb.keys, 'MEMORY_STATS',
                self.statedb.STATE_DB, 'MEMORY_STATS' + mibs.TABLE_NAME_SEPARATOR_VBAR + '*')
        if physical_memory_entries is None:
            physical_memory_entries = []
        elif not physical_memory_entries:
            mibs.logger.info('init_hr_storage - No memory stats found in STATE_DB MEMORY_STATS table')

        sorted_hr_storage_entries += physical_memory_entries
        self.hr_storage_entries = sorted_hr_storage_entries

    def get_next(self, sub_id):
        """
        :param sub_id: The 1-based snmp sub-identifier query.
        :return: the next sub id.
        """
        if not sub_id:
            self.init_hr_storage()
            if not self.hr_storage_entries:
                return None
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
        if oid >= len(self.hr_storage_entries):
            mibs.logger.info('hrstorage_used - Index out of range. Size of hr_storage_entries: {}'.format(len(self.hr_storage_entries)))
            return None
        hrstorage_name = self.hr_storage_entries[oid]
        hrstorage_info = _db_call(self.statedb.get_all, hrstorage_name,
                self.statedb.STATE_DB, hrstorage_name)
        if not hrstorage_info:
            mibs.logger.info('get_all() returned empty data for {}'.format(hrstorage_name))
            return None
        kblocks, used, filesystem = get_hrStorage_data(hrstorage_info)
        mibs.logger.debug('hr storage info {} name {} used {}'.format(oid, hrstorage_name, used))

        if not used:
            mibs.logger.info('No "Used" field for {}'.format(hrstorage_name))
            return None
        return int(used)

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
        if oid >= len(self.hr_storage_entries):
            mibs.logger.info('hrstorage_size - Index out of range. Size of hr_storage_entries: {}'.format(len(self.hr_storage_entries)))
            return None
        hrstorage_name = self.hr_storage_entries[oid]
        hrstorage_info = _db_call(self.statedb.get_all, hrstorage_name,
                self.statedb.STATE_DB, hrstorage_name)
        if not hrstorage_info:
            mibs.logger.info('get_all() returned empty data for {}'.format(hrstorage_name))
            return None
        kblocks, used, filesystem = get_hrStorage_data(hrstorage_info)
        mibs.logger.debug('hr storage info {} name {} size {}'.format(oid, hrstorage_name, kblocks))

        if not kblocks:
            mibs.logger.info('No "1K-blocks" field for {}'.format(hrstorage_name))
            return None
        return int(kblocks)

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
        if oid >= len(self.hr_storage_entries):
            mibs.logger.info('hrstorage_descr - Index out of range. Size of hr_storage_entries: {}'.format(len(self.hr_storage_entries)))
            return None
        hrstorage_name = self.hr_storage_entries[oid]
        hrstorage_info = _db_call(self.statedb.get_all, hrstorage_name,
                self.statedb.STATE_DB, hrstorage_name)
        if not hrstorage_info:
            mibs.logger.info('get_all() returned empty data for {}'.format(hrstorage_name))
            return None
        kblocks, used, fs_descr = get_hrStorage_data(hrstorage_info)
        mibs.logger.debug('hr storage info {} name {} filesystem {}'.format(oid, hrstorage_name, fs_descr))
        if not fs_descr:
            fs_descr = hrstorage_name.split('|')[1] + " Memory"

        return fs_descr

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
