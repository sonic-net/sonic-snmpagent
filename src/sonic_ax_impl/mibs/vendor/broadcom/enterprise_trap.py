import re
import threading

from sonic_ax_impl import mibs
from ax_interface.mib import ValueType
from ax_interface.trap import Trap, TrapInfra
from ax_interface.encodings import ObjectIdentifier, ValueRepresentation

class configChangeTrap(Trap):
    def __init__(self):
        super().__init__(dbKeys=["__keyspace@4__:*"])
        #self.db_conn = mibs.init_db()
        # Connect to all required DBs
        #self.db_conn.connect(mibs.CONFIG_DB)
        self.update_thread = None
        self.lock = threading.Lock()
        self.num_changes = 0
        self.last_num_changes = 0

    def send_config_change_trap(self):
        varBindsList = list()
        varbindsList = []

        mibs.logger.debug("generating configuration change trap.")
        TrapOid = ObjectIdentifier(14, 0, 0, 0, (1,3,6,1,4,1,4413,1,2,2,1,2,0,1))
        #returnDict["TrapOid"] = ObjectIdentifier(12, 0, 0, 0, (1,3,6,1,4,1,4413,1,2,1,1,999))
        #returnDict["varBinds"] = varBindsList
        snmpTrapOid = ObjectIdentifier(11, 0, 0, 0, (1, 3, 6, 1, 6, 3, 1, 1, 4, 1, 0))
        snmpTrapVarBind = ValueRepresentation(ValueType.OBJECT_IDENTIFIER, 0, snmpTrapOid, TrapOid)
        varbindsList.append(snmpTrapVarBind) 
        """append varbind list if mib objects present"""
        try:
            TrapInfra(None, None).dispatch_trap(varbindsList)
        except Exception as e:
            mibs.logger.warning("TrapInfra().dispatch_trap Exeception: '{}'.".format(e))


    def check_and_send_conf_change_trap(self):
        with self.lock:
            if self.last_num_changes == self.num_changes and self.num_changes > 0:
                self.send_config_change_trap()
                self.last_num_changes = 0
                self.num_changes = 0
                self.update_thread = None
            else:
                mibs.logger.info("{} Configuration changes detected in the last 30 sec window.".format(self.num_changes - self.last_num_changes))
                self.last_num_changes = self.num_changes
                self.update_thread = threading.Timer(30, self.check_and_send_conf_change_trap)
                self.update_thread.start()

    def trap_process(self, dbMessage, changedKey):
        db_num = re.match(r'__keyspace@(\d+)__:',changedKey).group(1)
        if db_num != '4':
            return None
        with self.lock:
            if self.num_changes == 0:
                mibs.logger.info("Configuration change detected.")
            self.num_changes = self.num_changes + 1
            if not self.update_thread:
                self.update_thread = threading.Timer(30, self.check_and_send_conf_change_trap)
                self.update_thread.start()


