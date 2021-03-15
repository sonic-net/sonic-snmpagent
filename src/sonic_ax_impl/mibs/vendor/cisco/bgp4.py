from bisect import bisect_right
from sonic_ax_impl import mibs
from ax_interface import MIBMeta, ValueType, MIBUpdater, SubtreeMIBEntry
from ax_interface.util import ip2byte_tuple
from sonic_ax_impl.mibs import Namespace
import ipaddress

STATE_CODE = {
    "Idle": 1,
    "Idle (Admin)": 1,
    "Connect": 2,
    "Active": 3,
    "OpenSent": 4,
    "OpenConfirm": 5,
    "Established": 6
};


class BgpSessionUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.db_conn = Namespace.init_namespace_dbs()

        self.neigh_state_map = {}
        self.session_status_map = {}
        self.session_status_list = []

    def reinit_data(self):
        Namespace.connect_all_dbs(self.db_conn, mibs.STATE_DB)
        self.neigh_state_map = Namespace.dbs_keys_namespace(self.db_conn, mibs.STATE_DB, "NEIGH_STATE_TABLE|*")

    def update_data(self):
        self.session_status_map = {}
        self.session_status_list = []

        for neigh_key, db_index in self.neigh_state_map.items():
            neigh_str = neigh_key
            neigh_str = neigh_str.split('|')[1]
            neigh_info = self.db_conn[db_index].get_all(mibs.STATE_DB, neigh_key, blocking=False)
            if neigh_info:
                state = neigh_info['state']
                ip = ipaddress.ip_address(neigh_str)
                if type(ip) is ipaddress.IPv4Address:
                    oid_head = (1, 4)
                else:
                    oid_head = (2, 16)
                oid_ip = ip2byte_tuple(neigh_str)

                if state.isdigit():
                    status = 6
                elif state in STATE_CODE:
                    status = STATE_CODE[state]
                else:
                    continue

                oid = oid_head + oid_ip
                self.session_status_list.append(oid)
                self.session_status_map[oid] = status

        self.session_status_list.sort()

    def sessionstatus(self, sub_id):
        return self.session_status_map.get(sub_id, None)

    def get_next(self, sub_id):
        right = bisect_right(self.session_status_list, sub_id)
        if right >= len(self.session_status_list):
            return None

        return self.session_status_list[right]


class CiscoBgp4MIB(metaclass=MIBMeta, prefix='.1.3.6.1.4.1.9.9.187'):
    bgpsession_updater = BgpSessionUpdater()

    cbgpPeer2State = SubtreeMIBEntry('1.2.5.1.3', bgpsession_updater, ValueType.INTEGER, bgpsession_updater.sessionstatus)
