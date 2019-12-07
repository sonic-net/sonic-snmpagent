import socket
from bisect import bisect_right
from sonic_ax_impl import mibs
from sonic_ax_impl.lib.perseverantsocket import PerseverantSocket
from sonic_ax_impl.lib.quaggaclient import QuaggaClient, bgp_peer_tuple
from ax_interface import MIBMeta, ValueType, MIBUpdater, SubtreeMIBEntry
from ax_interface.mib import MIBEntry

class BgpSessionUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.sock = PerseverantSocket(socket.AF_INET, socket.SOCK_STREAM
            , address_tuple=(QuaggaClient.HOST, QuaggaClient.PORT))
        self.QuaggaClient = QuaggaClient(socket.gethostname(), self.sock)

        self.session_status_map = {}
        self.session_status_list = []

    def reinit_data(self):
        pass

    def update_data(self):
        self.session_status_map = {}
        self.session_status_list = []

        try:
            if not self.sock.connected:
                try:
                    self.sock.reconnect()
                    mibs.logger.info('Connected quagga socket')
                except (ConnectionRefusedError, socket.timeout) as e:
                    mibs.logger.debug('Failed to connect quagga socket. Retry later...: {}.'.format(e))
                    return
                self.QuaggaClient.auth()
                mibs.logger.info('Authed quagga socket')

            sessions = self.QuaggaClient.union_bgp_sessions()

        except (socket.error, socket.timeout) as e:
            self.sock.close()
            mibs.logger.error('Failed to talk with quagga socket. Reconnect later...: {}.'.format(e))
            return
        except ValueError as e:
            self.sock.close()
            mibs.logger.error('Receive unexpected data from quagga socket. Reconnect later...: {}.'.format(e))
            return

        for nei, ses in sessions.items():
            oid, status = bgp_peer_tuple(ses)
            if oid is None: continue
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
