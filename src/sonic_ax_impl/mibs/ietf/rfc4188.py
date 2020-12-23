from swsssdk import port_util
from sonic_ax_impl import mibs
from ax_interface import MIBMeta, ValueType, MIBUpdater, SubtreeMIBEntry, MIBEntry
from bisect import bisect_right


class Dot1dBaseTypeConst:
    unknown = 1
    transparent = 2
    source_route = 3
    srt = 4

class Dot1dBaseUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.db_conn = mibs.init_db()
        self.dot1dbase_port_map = {}
        self.dot1dbase_port_list = []
        self.dot1dbase_bridge_addr = None
        self.dot1d_aging_time = 600

    def reinit_data(self):
        """
        Subclass update interface information
        """
        self.db_conn.connect(mibs.CONFIG_DB)
        self.dot1dbase_bridge_addr = self.db_conn.get(mibs.CONFIG_DB, "DEVICE_METADATA|localhost", 'mac')

    def update_data(self):
        """
        Update redis (caches config)
        Pulls the table references for each vlan member.
        """
        self.dot1dbase_port_map = {}
        self.dot1dbase_port_list = []

        self.db_conn.connect(mibs.CONFIG_DB)
        fdb_aging_time = self.db_conn.get(mibs.CONFIG_DB, "SWITCH|switch", 'fdb_aging_time')
        if fdb_aging_time:
            self.dot1d_aging_time = int(fdb_aging_time)
        else:
            self.dot1d_aging_time = 600

        vlanmem_entries = self.db_conn.keys(mibs.CONFIG_DB, "VLAN_MEMBER|*")
        if not vlanmem_entries:
            return

        for vmem_entry in vlanmem_entries:
            ifname = vmem_entry.split('|')[2]
            if_index = port_util.get_index_from_str(ifname)
            self.dot1dbase_port_map[if_index-1] = if_index

        self.dot1dbase_port_list = sorted(self.dot1dbase_port_map.keys())
        self.dot1dbase_port_list = [(i,) for i in self.dot1dbase_port_list]
        mibs.logger.debug('Port map entries : {}' .format(self.dot1dbase_port_map))
        mibs.logger.debug('Port list : {}' .format(self.dot1dbase_port_list))

    def get_dot1dbase_bridge_addr(self):
        return self.dot1dbase_bridge_addr

    def get_dot1d_base_num_ports(self):
        return len(self.dot1dbase_port_map)

    def get_dot1d_base_type(self):
        return Dot1dBaseTypeConst.transparent

    def get_dot1d_aging_time(self):
        return self.dot1d_aging_time

    def get_dot1dbase_port(self, sub_id):
        if sub_id:
            if sub_id in self.dot1dbase_port_list:
               return sub_id[0]
        return 

    def get_dot1dbase_port_ifindex(self, sub_id):
        if sub_id:
            return self.dot1dbase_port_map.get(sub_id[0], None)

    def get_dot1dbase_port_delay_discard(self, sub_id):
        if sub_id:
            return 0

    def get_dot1dbase_port_mtu_discard(self, sub_id):
        if sub_id:
            return 0

    def get_next(self, sub_id):
        right = bisect_right(self.dot1dbase_port_list, sub_id)
        if right == len(self.dot1dbase_port_list):
            return None

        return self.dot1dbase_port_list[right]

class Dot1dBaseMIB(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.17'):
    """
    ' dot1dBase MIB' https://tools.ietf.org/html/rfc4188 
    """

    dot1dbase_updater = Dot1dBaseUpdater()

    # (subtree, value_type, callable_, *args, handler=None)
    dot1dBaseBridgeAddress = MIBEntry('1.1.0', ValueType.OCTET_STRING, dot1dbase_updater.get_dot1dbase_bridge_addr)
    dot1dBaseNumPorts = MIBEntry('1.2.0', ValueType.INTEGER, dot1dbase_updater.get_dot1d_base_num_ports)
    dot1dBaseType = MIBEntry('1.3.0', ValueType.INTEGER, dot1dbase_updater.get_dot1d_base_type)

    dot1dBasePort = \
        SubtreeMIBEntry('1.4.1.1', dot1dbase_updater, ValueType.INTEGER, dot1dbase_updater.get_dot1dbase_port)
    dot1dBasePortIfIndex = \
        SubtreeMIBEntry('1.4.1.2', dot1dbase_updater, ValueType.INTEGER, dot1dbase_updater.get_dot1dbase_port_ifindex)
    dot1dBasePortDelayExceededDiscards = \
        SubtreeMIBEntry('1.4.1.4', dot1dbase_updater, ValueType.COUNTER_32, dot1dbase_updater.get_dot1dbase_port_delay_discard)
    dot1dBasePortMtuExceededDiscards = \
        SubtreeMIBEntry('1.4.1.5', dot1dbase_updater, ValueType.COUNTER_32, dot1dbase_updater.get_dot1dbase_port_mtu_discard)

    dot1dTpAgingTime = MIBEntry('4.2.0', ValueType.INTEGER, dot1dbase_updater.get_dot1d_aging_time)

