import re
from ax_interface.mib import ValueType
from sonic_ax_impl import mibs
from sonic_ax_impl.mibs import Namespace
from ax_interface.trap import Trap
from ax_interface.encodings import ObjectIdentifier, ValueRepresentation

class linkUpDownTrap(Trap):
    def __init__(self):
        super().__init__(dbKeys=["__keyspace@0__:LAG_TABLE:PortChannel*", \
            "__keyspace@0__:PORT_TABLE:Ethernet*", \
                "__keyspace@6__:MGMT_PORT_TABLE|eth*", \
                    "__keyspace@4__:MGMT_PORT|eth*"])
        self.db_conn = Namespace.init_namespace_dbs()
        # Connect to all required DBs
        Namespace.connect_all_dbs(self.db_conn, mibs.APPL_DB)
        Namespace.connect_all_dbs(self.db_conn, mibs.CONFIG_DB)
        Namespace.connect_all_dbs(self.db_conn, mibs.STATE_DB)

    def trap_init(self):
        self.ethernetKeys = Namespace.dbs_keys(self.db_conn, mibs.APPL_DB, "PORT_TABLE:Ethernet*")
        self.etherTable = dict()
        if self.ethernetKeys is None:
            self.ethernetKeys = []
        for etherKey in self.ethernetKeys:
            entry = etherKey
            etherEntry = Namespace.dbs_get_all(self.db_conn, mibs.APPL_DB, entry, blocking=True)
            self.etherTable[entry] = dict()
            if 'oper_status' in etherEntry:
                self.etherTable[entry]['oper_status'] = etherEntry['oper_status']
            else:
                self.etherTable[entry]['oper_status'] = 'down'
            if 'admin_status' in etherEntry:
                self.etherTable[entry]['admin_status'] = etherEntry['admin_status']
            else:
                self.etherTable[entry]['admin_status'] = 'down'

        self.portChannelKeys = Namespace.dbs_keys(self.db_conn, mibs.APPL_DB, "LAG_TABLE:PortChannel*")
        self.portChannelTable = dict()
        if self.portChannelKeys is None:
            self.portChannelKeys = []
        for portChannelKey in self.portChannelKeys:
            entry = portChannelKey
            portChannelEntry = Namespace.dbs_get_all(self.db_conn, mibs.APPL_DB, entry, blocking=True)
            self.portChannelTable[entry] = dict()
            if 'oper_status' in portChannelEntry:
                self.portChannelTable[entry]['oper_status'] = portChannelEntry['oper_status']
            else:
                self.portChannelTable[entry]['oper_status'] = 'down'
            if 'admin_status' in portChannelEntry:
                self.portChannelTable[entry]['admin_status'] = portChannelEntry['admin_status']
            else:
                self.portChannelTable[entry]['admin_status'] = 'down'            
        
        ## For mgmt interface
        # Get admin_status from configDB
        self.mgmtKeys = Namespace.dbs_keys(self.db_conn, mibs.CONFIG_DB, "MGMT_PORT|eth*")
        self.mgmtDict = dict()
        if self.mgmtKeys is not None:
            for mgmtKey in self.mgmtKeys:
                entry = mgmtKey
                mgmt_interface = entry.split('|')[1]
                self.mgmtDict[mgmt_interface] = dict()
                # check to see if admin_status is set if not set it as 'down'
                mgmtEntry = Namespace.dbs_get_all(self.db_conn, mibs.CONFIG_DB, entry, blocking=True)
                if 'admin_status' in mgmtEntry:
                    self.mgmtDict[mgmt_interface]["admin_status"] = mgmtEntry['admin_status']
                else:
                    self.mgmtDict[mgmt_interface]["admin_status"] = 'down'
                self.mgmtDict[mgmt_interface]["oper_status"] = 'down'

        # Get the oper_status from stateDB
        self.mgmtStateDBKeys = Namespace.dbs_keys(self.db_conn, mibs.STATE_DB, "MGMT_PORT_TABLE|eth*")
        if self.mgmtStateDBKeys is not None:
            for mgmtKey in self.mgmtStateDBKeys:
                entry = mgmtKey
                mgmt_interface = entry.split('|')[1]
                mgmtEntry = Namespace.dbs_get_all(self.db_conn, mibs.STATE_DB, entry, blocking=True)
                if mgmt_interface not in self.mgmtDict:
                    self.mgmtDict[mgmt_interface] = dict()
                    self.mgmtDict[mgmt_interface]["admin_status"] = 'down'
                    self.mgmtDict[mgmt_interface]["oper_status"] = mgmtEntry['oper_status']
                else:
                    self.mgmtDict[mgmt_interface]["oper_status"] = mgmtEntry['oper_status']

    def trap_process(self, dbMessage, changedKey):
        returnDict = dict()
        genTrap = False
        dbCache = None
        if_name = None
        varBindsList = list()
        status_map = {
            "up": 1,
            "down": 2
        }

        # Get the actual key
        actualKey = changedKey[len(re.match(r'__keyspace@(\d+)__:',changedKey).group(0)):]

        # handle MGMT interface
        db_num = re.match(r'__keyspace@(\d+)__:',changedKey).group(1)
        if db_num == '6':
            try:
                dbEntry = Namespace.dbs_get_all(self.db_conn, mibs.STATE_DB, actualKey, blocking=False)
                if not dbEntry:
                    return None
            except Exception as e:
                mibs.logger.warning("{}, no Trap generated.".format(e))
                return None

            oper_status = dbEntry['oper_status']
            actualKey = actualKey.split('|')[1]            
            if 'admin_status' in self.mgmtDict:
                admin_status = self.mgmtDict['admin_status']
            else:
                admin_status = 'down'
        elif db_num == '4':
            try:
                dbEntry = Namespace.dbs_get_all(self.db_conn, mibs.CONFIG_DB, actualKey, blocking=False)
                if not dbEntry:
                    return None
            except Exception as e:
                mibs.logger.warning("{}, no Trap generated.".format(e))
                return None

            actualKey = actualKey.split('|')[1] 
            admin_status = dbEntry['admin_status']
            if 'oper_status' in self.mgmtDict:
                oper_status = self.mgmtDict['oper_status']
            else:
                oper_status = 'down'
        else:
            # retrieve current DB entry
            try:
                dbEntry = Namespace.dbs_get_all(self.db_conn, mibs.APPL_DB, actualKey, blocking=False)
                if not dbEntry:
                    return None
            except Exception as e:
                mibs.logger.warning("{}, no Trap generated.".format(e))
                return None

            # Extract required fields
            if 'admin_status' in dbEntry:
                admin_status = dbEntry['admin_status']
            else:
                admin_status = 'down'
            if 'oper_status' in dbEntry:
                oper_status = dbEntry['oper_status']
            else:
                oper_status = 'down'
       
        # check if there is an entry in cache and update if required
        if actualKey.startswith('PORT_TABLE:Ethernet'):
            dbCache = self.etherTable
            if_name = actualKey[11:] 
        elif actualKey.startswith('LAG_TABLE:PortChannel'):
            dbCache = self.portChannelTable
            if_name = actualKey[10:] 
        elif actualKey.startswith('eth'):
            dbCache = self.mgmtDict
            if_name = actualKey
        else:
            dbCache = None

        if dbCache is None:
           mibs.logger.warning("No table found in cache for DB entry " + changedKey) 
           return None

        if actualKey not in dbCache:
            genTrap = True
            dbCache[actualKey]=dict()
            dbCache[actualKey]['oper_status'] = oper_status
            dbCache[actualKey]['admin_status'] = admin_status
        else:
            if dbCache[actualKey]['oper_status'] != oper_status or dbCache[actualKey]['admin_status'] != admin_status:
                # Update Cache
                dbCache[actualKey]['oper_status'] = oper_status
                dbCache[actualKey]['admin_status'] = admin_status
                genTrap = True
 
        # Generate Trap if required
        if genTrap:
           if oper_status == 'up':
               returnDict["TrapOid"] = ObjectIdentifier(10, 0, 0, 0, (1, 3, 6, 1, 6, 3, 1, 1, 5, 4))
           elif oper_status == 'down':
               returnDict["TrapOid"] = ObjectIdentifier(10, 0, 0, 0, (1, 3, 6, 1, 6, 3, 1, 1, 5, 3))        
           else:
               mibs.logger.warning("Incorrect entry in DB for oper_status, No Trap generated")
               return None
           # Fill VarBinds
           # For if_index
           if_index_value = mibs.get_index_from_str(if_name)
           if_index_oid = ObjectIdentifier(11, 0, 0, 0, (1, 3, 6, 1, 2, 1, 2, 2, 1, 1, if_index_value))
           if_index_vb = ValueRepresentation(ValueType.INTEGER, 0, if_index_oid, if_index_value)
           varBindsList.append(if_index_vb)

           # For admin status 
           admin_status_oid = ObjectIdentifier(11, 0, 0, 0, (1, 3, 6, 1, 2, 1, 2, 2, 1, 7, if_index_value))
           admin_status_value = status_map[admin_status]
           admin_status_vb = ValueRepresentation(ValueType.INTEGER, 0, admin_status_oid, admin_status_value)
           varBindsList.append(admin_status_vb)

           # For oper status 
           oper_status_oid = ObjectIdentifier(11, 0, 0, 0, (1, 3, 6, 1, 2, 1, 2, 2, 1, 8, if_index_value))
           oper_status_value = status_map[oper_status]
           oper_status_vb = ValueRepresentation(ValueType.INTEGER, 0, oper_status_oid, oper_status_value)
           varBindsList.append(oper_status_vb)

           returnDict["varBinds"] = varBindsList
           return returnDict

        else:
            mibs.logger.debug("No change in DB entry, therefore Trap is not generated")
            return None 

