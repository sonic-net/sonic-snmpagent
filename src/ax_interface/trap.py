import pdb
import asyncio
from . import logger, constants, exceptions
from .mib import ValueType
from .encodings import ObjectIdentifier, ValueRepresentation
from .pdu import PDUHeader
from .pdu_implementations import NotifyPDU
import re
import json
import os

class TrapInfra:
    """
    Trap infrastructure's core services are define here.
    """
    protocol_obj = None # this will be set in the AgentX protocol class
    def __init__(self, loop, trap_handlers):
        logger.debug("Init begins for Trap infra")
        self.loop = loop
        self.redis_instances = dict()
        self.db_to_redis_dict = dict()
        if trap_handlers is None:
            return
        self.dbKeyToHandler = dict()
        trap_handlers_set = set(trap_handlers)
        for t_handler in trap_handlers_set:
            t_instance = t_handler()
            dbKeys = t_instance.dbKeys
            for dbkey in dbKeys:
                if dbkey not in self.dbKeyToHandler:
                    self.dbKeyToHandler[dbkey] = list()
                    self.dbKeyToHandler[dbkey].append(t_instance)
                else:
                    self.dbKeyToHandler[dbkey].append(t_instance)
            t_instance.trap_init()
        logger.debug("Init successful for Trap infra")
    
    async def db_listener(self):
        """
        Co routine which listens for DB notification events
        """
        import aioredis
        from aioredis.pubsub import Receiver

        logger.debug("starting redis co routine")
        logger.info("starting redis DB listener routine")
        # Read Config File and setup DB instances
        CONFIG_FILE = os.getenv('DB_CONFIG_FILE', "/var/run/redis/sonic-db/database_config.json")
        if not os.path.exists(CONFIG_FILE):
            raise RuntimeError("[Trap:db_listener - DB config file not found " + str(CONFIG_FILE))
        else:
            with open(CONFIG_FILE, "r") as config_file:
                db_config_data = json.load(config_file)
                if not 'INSTANCES' in db_config_data:
                    raise RuntimeError("[Trap:db_listener - No DB instances found in DB config file")
                for instance in db_config_data['INSTANCES']:
                    entry = db_config_data['INSTANCES'][instance]
                    if instance not in self.redis_instances:
                        self.redis_instances[instance] = {"host": entry["hostname"], \
                            "port": entry["port"], "keyPatterns": [], \
                                "patternObjs": [], "receiver_handle": None, \
                                    "connection_obj": None \
                        }
                for db in db_config_data['DATABASES']:
                    entry = db_config_data['DATABASES'][db]
                    db_id = int(entry["id"])
                    if db_id not in self.db_to_redis_dict:
                        if entry["instance"] not in self.redis_instances:
                            raise RuntimeError("[Trap:db_listener - No DB instance found for " + str(entry["instance"]))
                        self.db_to_redis_dict[db_id] = self.redis_instances[entry["instance"]]

        async def reader(receiver_handle):
            logger.debug("Listening for notifications")
            async for channel, msg in receiver_handle.iter():
                logger.debug("Got {!r} in channel {!r}".format(msg, channel))
                self.process_trap(channel,msg)
        
        for instance in self.redis_instances:
            address_tuple = (self.redis_instances[instance]['host'], self.redis_instances[instance]['port'])
            self.redis_instances[instance]["connection_obj"] = await aioredis.create_redis_pool(address_tuple)
            receiver_handle = Receiver(loop=self.loop)
            self.redis_instances[instance]["receiver_handle"] = receiver_handle
            asyncio.ensure_future(reader(receiver_handle))

        for pat in self.dbKeyToHandler.keys():
            #Get DB number
            db_num = re.match(r'__keyspace@(\d+)__:',pat).group(1)
            if db_num is None or db_num == "":
                raise RuntimeError("[Trap:db_listener - DB number cannot be determined for key " + str(pat))
            
            db_num = int(db_num)
            db_instance = self.db_to_redis_dict[db_num]
            db_instance["patternObjs"].append(db_instance["receiver_handle"].pattern(pat))
            db_instance["keyPatterns"].append(pat)
        
        for instance in self.redis_instances:
            if len(self.redis_instances[instance]["patternObjs"]) == 0:
                continue
            await self.redis_instances[instance]["connection_obj"].psubscribe(*self.redis_instances[instance]["patternObjs"])

    def dispatch_trap(self, varBinds):
        """
        Prepare Notify PDU and sends to Master using AgentX protocol
        """
        logger.debug("dispatch_trap invoked")
        if TrapInfra.protocol_obj is not None:
            notifyPDU = NotifyPDU(header=PDUHeader(1, \
                constants.PduTypes.NOTIFY, \
                    PDUHeader.MASK_NEWORK_BYTE_ORDER, 0, \
                        TrapInfra.protocol_obj.session_id, \
                            0, 0, 0), varBinds=varBinds)
            TrapInfra.protocol_obj.send_pdu(notifyPDU)
            logger.debug("processed trap successfully")
        else:
            logger.warning("Protocol Object is None, cannot process traps")
    
    def process_trap(self, channel, msg):
        """
        Invokes trap handlers
        """
        db_pattern = channel.name.decode('utf-8')
        changed_key = msg[0].decode('utf-8')
        
        for t_instance in self.dbKeyToHandler[db_pattern]:
            varbindsDict = t_instance.trap_process(msg, changed_key)
            if varbindsDict is None:
                continue # no process
            assert isinstance(varbindsDict, dict)
            assert 'TrapOid' in varbindsDict
            assert 'varBinds' in varbindsDict
            varbinds = varbindsDict['varBinds']
            TrapOid = varbindsDict['TrapOid']
            assert isinstance(TrapOid, ObjectIdentifier)
            varbindsList = []
            # Insert standard SNMP trap
            snmpTrapOid = ObjectIdentifier(11, 0, 0, 0, (1, 3, 6, 1, 6, 3, 1, 1, 4, 1, 0))
            snmpTrapVarBind = ValueRepresentation(ValueType.OBJECT_IDENTIFIER, 0, snmpTrapOid, TrapOid)
            varbindsList.append(snmpTrapVarBind)            
            if len(varbinds) > 0:
                for vb in varbinds:
                    if not isinstance(vb, ValueRepresentation):
                        raise RuntimeError("list entry is not of type ValueRepresentation")
                    else:
                        varbindsList.append(vb)
            else:
                raise RuntimeError("Return value must contain atleast one VarBind")
            self.dispatch_trap(varbindsList)

    async def shutdown(self):
        for instance in self.redis_instances:
            if len(self.redis_instances[instance]["keyPatterns"]) > 0:
                 await self.redis_instances[instance]["connection_obj"].punsubscribe(*self.redis_instances[instance]["keyPatterns"])
            self.redis_instances[instance]["receiver_handle"].stop()
            self.redis_instances[instance]["connection_obj"].close()
            await self.redis_instances[instance]["connection_obj"].wait_closed()

class Trap:
    """
    Interface for developing Trap handlers
    """
    def __init__(self, **kwargs):
        self.run_event = asyncio.Event()
        assert isinstance(kwargs["dbKeys"], list)
        self.dbKeys = kwargs["dbKeys"]

    def trap_init(self):
        """
        Children may override this method.
        """
        logger.info("I am trap_init from infra")

    def trap_process(self, dbMessage, changedKey):
        """
        Children may override this method.
        """    
        logger.info("I am trap_process from infra")      




