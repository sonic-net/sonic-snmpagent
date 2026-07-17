import asyncio
import re
import json
import os
from concurrent.futures import ThreadPoolExecutor

from . import logger, constants
from .mib import ValueType
from .encodings import ObjectIdentifier, ValueRepresentation
from .pdu import PDUHeader
from .pdu_implementations import NotifyPDU

# Use redis-py asyncio API (redis>=4.2).
import redis.asyncio as redis

class TrapInfra:
    """
    Trap infrastructure core services.
    All logic preserved from original implementation.
    """

    protocol_obj = None  # set by AgentX protocol

    # Delay before a reader retries after losing its redis pubsub connection.
    RECONNECT_BACKOFF_SECONDS = 5

    def __init__(self, loop, trap_handlers):
        logger.debug("Init begins for Trap infra")

        self.loop = loop
        self.redis_instances = {}
        self.db_to_redis_dict = {}
        self.dbKeyToHandler = {}
        # precompiled patterns: list[(compiled_regex, [handlers], original_pattern)]
        self._compiled_patterns = []
        # reader tasks for graceful shutdown
        self._reader_tasks = []
        # Handlers perform blocking Redis reads (swsscommon). Run them off the
        # event loop thread so a burst of keyspace notifications can't stall
        # pubsub message delivery. Single worker preserves the original
        # in-order, non-concurrent handler semantics.
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="trap-handler")

        if trap_handlers is None:
            return

        self._init_trap_handlers(trap_handlers)

        logger.debug("Init successful for Trap infra")

    def _init_trap_handlers(self, trap_handlers):
        trap_handlers_set = set(trap_handlers)

        for handler_cls in trap_handlers_set:
            handler = handler_cls()
            for dbkey in handler.dbKeys:
                if dbkey not in self.dbKeyToHandler:
                    self.dbKeyToHandler[dbkey] = []
                self.dbKeyToHandler[dbkey].append(handler)

            handler.trap_init()

    async def db_listener(self):
        """
        Coroutine which listens for DB notification events using redis.asyncio.
        """
        logger.debug("starting redis co routine")
        logger.info("starting redis DB listener routine")

        self._load_db_config()
        # compile patterns once for fast matching and correct escaping
        self._compile_patterns()

        # Register keyspace patterns to redis (use original patterns)
        for pattern in self.dbKeyToHandler.keys():
            self._register_pattern(pattern)

        # One self-healing reader task per redis instance
        for instance in self.redis_instances:
            redis_info = self.redis_instances[instance]
            if redis_info["patternObjs"]:
                task = asyncio.create_task(self._reader_loop(instance))
                self._reader_tasks.append(task)

    async def _reader_loop(self, instance):
        """
        Subscribe to this redis instance's keyspace patterns and process
        notifications until cancelled.

        Unlike a plain listen loop, any error (connection drop, protocol
        hiccup, etc.) is caught and retried with a backoff instead of
        letting the task die silently - a dead reader previously meant
        permanent, unnoticed loss of all traps for that DB instance until
        the whole process was restarted.
        """
        redis_info = self.redis_instances[instance]
        address = f"redis://{redis_info['host']}:{redis_info['port']}"

        while True:
            pubsub = None
            try:
                redis_info["connection_obj"] = redis.from_url(address, decode_responses=False)
                pubsub = redis_info["connection_obj"].pubsub(ignore_subscribe_messages=True)
                redis_info["pubsub"] = pubsub

                await pubsub.psubscribe(*redis_info["patternObjs"])
                logger.debug("Listening for notifications on {}".format(instance))

                async for message in pubsub.listen():
                    if message['type'] in ('pmessage', 'message'):
                        channel = message['channel']
                        data = message['data']
                        # The handlers do blocking Redis reads (swsscommon).
                        # Run them off the event loop thread so they can't
                        # stall delivery of the next pubsub message; the
                        # actual trap PDU send still happens back here, on
                        # the event loop thread, since it isn't thread-safe.
                        results = await self.loop.run_in_executor(
                            self._executor, self._collect_traps, channel, [data]
                        )
                        for result in results:
                            self._send_trap(result)
                            logger.debug("Trap dispatched successfully for {}".format(channel))
            except asyncio.CancelledError:
                # normal during shutdown
                logger.debug("Trap redis reader cancelled for {}".format(instance))
                raise
            except Exception as e:
                logger.error(
                    "Reader loop for {} encountered an error, reconnecting in {}s: {}".format(
                        instance, self.RECONNECT_BACKOFF_SECONDS, e
                    ),
                    exc_info=True
                )
            finally:
                if pubsub is not None:
                    try:
                        await pubsub.close()
                    except Exception:
                        pass

            await asyncio.sleep(self.RECONNECT_BACKOFF_SECONDS)

    def _compile_patterns(self):
        """
        Compile redis keyspace patterns to safe, anchored regex.
        Rule: '*' -> '.*'; other characters are escaped literally.
        """
        self._compiled_patterns.clear()
        for pattern, handlers in self.dbKeyToHandler.items():
            # escape everything then re-enable '*' as wildcard
            escaped = re.escape(pattern)
            # replace escaped '*' with '.*' for wildcard semantics
            regex_str = '^' + escaped.replace(r'\*', '.*') + '$'
            try:
                cregex = re.compile(regex_str)
            except re.error:
                logger.error("Invalid trap pattern after compile: %s -> %s", pattern, regex_str)
                continue
            self._compiled_patterns.append((cregex, handlers, pattern))

    def _load_db_config(self):
        CONFIG_FILE = os.getenv(
            'DB_CONFIG_FILE',
            "/var/run/redis/sonic-db/database_config.json"
        )

        if not os.path.exists(CONFIG_FILE):
            raise RuntimeError(
                "[Trap:db_listener - DB config file not found " + str(CONFIG_FILE)
            )

        with open(CONFIG_FILE, "r") as config_file:
            db_config_data = json.load(config_file)

        if 'INSTANCES' not in db_config_data:
            raise RuntimeError(
                "[Trap:db_listener - No DB instances found in DB config file"
            )

        # Init redis instances
        for instance in db_config_data['INSTANCES']:
            entry = db_config_data['INSTANCES'][instance]
            if instance not in self.redis_instances:
                self.redis_instances[instance] = {
                    "host": entry["hostname"],
                    "port": entry["port"],
                    "keyPatterns": [],
                    "patternObjs": [],
                    "pubsub": None,
                    "connection_obj": None
                }

        # Map DB number to redis instance
        for db in db_config_data['DATABASES']:
            entry = db_config_data['DATABASES'][db]
            db_id = int(entry["id"])

            if db_id not in self.db_to_redis_dict:
                instance_name = entry["instance"]
                if instance_name not in self.redis_instances:
                    raise RuntimeError(
                        "[Trap:db_listener - No DB instance found for " +
                        str(instance_name)
                    )
                self.db_to_redis_dict[db_id] = self.redis_instances[instance_name]

    def _register_pattern(self, pattern):
        match = re.match(r'__keyspace@(\d+)__:', pattern)
        if not match:
            raise RuntimeError(
                "[Trap:db_listener - DB number cannot be determined for key " +
                str(pattern)
            )

        db_num = int(match.group(1))
        db_instance = self.db_to_redis_dict[db_num]

        db_instance["patternObjs"].append(pattern)
        db_instance["keyPatterns"].append(pattern)

    def dispatch_trap(self, varBinds):
        """
        Prepare Notify PDU and send to master using AgentX protocol.
        """
        logger.debug("dispatch_trap invoked")

        if TrapInfra.protocol_obj is None:
            logger.warning("Protocol Object is None, cannot process traps")
            return

        notifyPDU = NotifyPDU(
            header=PDUHeader(
                1,
                constants.PduTypes.NOTIFY,
                PDUHeader.MASK_NEWORK_BYTE_ORDER,
                0,
                TrapInfra.protocol_obj.session_id,
                0, 0, 0
            ),
            varBinds=varBinds
        )

        TrapInfra.protocol_obj.send_pdu(notifyPDU)
        logger.debug("processed trap successfully")

    def _collect_traps(self, channel, msg):
        """
        Invoke registered trap handlers for the given Redis notification and
        return the list of trap dicts (if any) they produced.

        This does the blocking work (handler.trap_process() performs
        synchronous Redis reads via swsscommon) and is run on a worker
        thread by _reader_loop - it must NOT touch the AgentX transport,
        which is only safe to use from the event loop thread. Sending is
        done by the caller via _send_trap() after this returns.
        """
        # Decode channel name, e.g., "__keyspace@6__:PSU_INFO|Psu1"
        full_channel = channel.decode('utf-8') if isinstance(channel, bytes) else str(channel)
        # msg[0] is the operation type, e.g., "hset" (not the key itself)
        operation = msg[0].decode('utf-8') if isinstance(msg[0], bytes) else str(msg[0])

        logger.debug("Redis Event: Channel={}, Operation={}".format(full_channel, operation))

        # Find matching handlers (precompiled regexes)
        handlers_to_call = []
        for cregex, handlers, original in self._compiled_patterns:
            if cregex.fullmatch(full_channel):
                logger.debug("Channel %s matched pattern %s", full_channel, original)
                handlers_to_call.extend(handlers)

        if not handlers_to_call:
            logger.debug("No handlers matched for {}".format(full_channel))
            return []

        # Invoke all matched handlers, collecting whatever traps they produce
        results = []
        for handler in handlers_to_call:
            try:
                # Pass full_channel to handler so it can determine the exact PSU/FAN
                result = handler.trap_process(msg, full_channel)

                if result is None:
                    continue

                assert isinstance(result, dict)
                assert 'TrapOid' in result
                assert 'varBinds' in result

                results.append(result)
            except Exception as e:
                logger.error("Error executing handler {}: {}".format(handler, e), exc_info=True)

        return results

    def _send_trap(self, result):
        varbinds = result['varBinds']
        trap_oid = result['TrapOid']

        assert isinstance(trap_oid, ObjectIdentifier)

        varbinds_list = []

        # Standard SNMP trap OID
        snmp_trap_oid = ObjectIdentifier(
            11, 0, 0, 0,
            (1, 3, 6, 1, 6, 3, 1, 1, 4, 1, 0)
        )

        varbinds_list.append(
            ValueRepresentation(
                ValueType.OBJECT_IDENTIFIER,
                0,
                snmp_trap_oid,
                trap_oid
            )
        )

        if not varbinds:
            raise RuntimeError("Return value must contain atleast one VarBind")

        for vb in varbinds:
            if not isinstance(vb, ValueRepresentation):
                raise RuntimeError(
                    "list entry is not of type ValueRepresentation"
                )
            varbinds_list.append(vb)

        self.dispatch_trap(varbinds_list)

    async def shutdown(self):
        # stop readers first
        for t in self._reader_tasks:
            t.cancel()
        if self._reader_tasks:
            await asyncio.gather(*self._reader_tasks, return_exceptions=True)

        for instance in self.redis_instances:
            redis_info = self.redis_instances[instance]

            if redis_info["keyPatterns"] and redis_info["pubsub"]:
                try:
                    await redis_info["pubsub"].punsubscribe(*redis_info["keyPatterns"])
                except Exception as e:
                    logger.debug("punsubscribe error on %s: %s", instance, e)

            if redis_info["pubsub"]:
                try:
                    await redis_info["pubsub"].close()
                except Exception:
                    pass
            if redis_info["connection_obj"]:
                try:
                    await redis_info["connection_obj"].close()
                except Exception:
                    pass

        self._executor.shutdown(wait=False)


class Trap:
    """
    Interface for developing Trap handlers.
    """

    def __init__(self, **kwargs):
        self.run_event = asyncio.Event()
        db_keys = kwargs.get("dbKeys")
        if not isinstance(db_keys, list):
            raise TypeError("Trap requires dbKeys=list of keyspace patterns")
        self.dbKeys = db_keys

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
