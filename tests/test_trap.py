import asyncio
import json
import os
import re
import sys
import tempfile
from unittest import TestCase
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from ax_interface import trap as trap_module
from ax_interface.trap import Trap, TrapInfra
from ax_interface.encodings import ObjectIdentifier, ValueRepresentation
from ax_interface.mib import ValueType


def make_trap_result(index=1, value=2):
    """Build a minimal, valid handler result dict as returned by Trap.trap_process()."""
    status_oid = ObjectIdentifier(15, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2, index))
    varbind = ValueRepresentation(ValueType.INTEGER, 0, status_oid, value)
    return {
        "TrapOid": ObjectIdentifier(14, 0, 0, 0, (1, 3, 6, 1, 4, 1, 9, 9, 117, 1, 1, 2, 1, 2)),
        "varBinds": [varbind],
    }


class TestCollectTraps(TestCase):
    """
    _collect_traps() is the blocking-safe handler dispatcher that
    _reader_loop() now runs on a worker thread via run_in_executor(). It must
    never touch the AgentX transport and must isolate individual handler
    failures instead of letting one bad handler take down the others.
    """

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.infra = TrapInfra(self.loop, None)

    def tearDown(self):
        self.loop.close()

    def _register(self, pattern, handlers):
        self.infra.dbKeyToHandler = {pattern: handlers}
        self.infra._compile_patterns()

    def test_no_matching_handlers_returns_empty_list(self):
        self._register("__keyspace@6__:PSU_INFO|*", [MagicMock()])
        result = self.infra._collect_traps(
            b"__keyspace@6__:FAN_INFO|Fantray1_1", [b"hset"]
        )
        self.assertEqual(result, [])

    def test_handler_returning_none_produces_no_trap(self):
        handler = MagicMock()
        handler.trap_process.return_value = None
        self._register("__keyspace@6__:PSU_INFO|*", [handler])

        result = self.infra._collect_traps(b"__keyspace@6__:PSU_INFO|Psu2", [b"hset"])

        self.assertEqual(result, [])
        handler.trap_process.assert_called_once()

    def test_handler_result_is_collected(self):
        handler = MagicMock()
        expected = make_trap_result()
        handler.trap_process.return_value = expected
        self._register("__keyspace@6__:PSU_INFO|*", [handler])

        result = self.infra._collect_traps(b"__keyspace@6__:PSU_INFO|Psu2", [b"hset"])

        self.assertEqual(result, [expected])

    def test_one_handler_raising_does_not_block_others(self):
        bad_handler = MagicMock()
        bad_handler.trap_process.side_effect = RuntimeError("boom")
        good_handler = MagicMock()
        good_handler.trap_process.return_value = make_trap_result(index=2)
        self._register("__keyspace@6__:PSU_INFO|*", [bad_handler, good_handler])

        result = self.infra._collect_traps(b"__keyspace@6__:PSU_INFO|Psu2", [b"hset"])

        self.assertEqual(len(result), 1)
        good_handler.trap_process.assert_called_once()

    def test_malformed_handler_result_is_rejected_not_raised(self):
        handler = MagicMock()
        handler.trap_process.return_value = {"TrapOid": None}  # missing varBinds
        self._register("__keyspace@6__:PSU_INFO|*", [handler])

        # Should be swallowed by the per-handler try/except, not propagate.
        result = self.infra._collect_traps(b"__keyspace@6__:PSU_INFO|Psu2", [b"hset"])
        self.assertEqual(result, [])


class TestSendAndDispatch(TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.infra = TrapInfra(self.loop, None)

    def tearDown(self):
        self.loop.close()
        TrapInfra.protocol_obj = None

    def test_send_trap_prepends_standard_trap_oid_varbind(self):
        result = make_trap_result()
        with patch.object(self.infra, 'dispatch_trap') as mock_dispatch:
            self.infra._send_trap(result)

        mock_dispatch.assert_called_once()
        varbinds_list = mock_dispatch.call_args[0][0]
        self.assertEqual(len(varbinds_list), 2)
        self.assertEqual(varbinds_list[0].name.subids, (1, 3, 6, 1, 6, 3, 1, 1, 4, 1, 0))
        self.assertEqual(varbinds_list[1], result["varBinds"][0])

    def test_send_trap_raises_on_empty_varbinds(self):
        result = {"TrapOid": ObjectIdentifier(10, 0, 0, 0, (1, 3, 6, 1)), "varBinds": []}
        with self.assertRaises(RuntimeError):
            self.infra._send_trap(result)

    def test_send_trap_raises_on_wrong_varbind_type(self):
        result = {"TrapOid": ObjectIdentifier(10, 0, 0, 0, (1, 3, 6, 1)), "varBinds": ["not a varbind"]}
        with self.assertRaises(RuntimeError):
            self.infra._send_trap(result)

    def test_dispatch_trap_is_noop_without_protocol_obj(self):
        TrapInfra.protocol_obj = None
        # Must not raise even though nothing is connected yet.
        self.infra.dispatch_trap([])

    def test_dispatch_trap_sends_pdu_when_protocol_available(self):
        mock_protocol = MagicMock()
        mock_protocol.session_id = 7
        TrapInfra.protocol_obj = mock_protocol

        oid = ObjectIdentifier(11, 0, 0, 0, (1, 3, 6, 1, 2, 1, 1))
        varbind = ValueRepresentation(ValueType.INTEGER, 0, oid, 1)

        self.infra.dispatch_trap([varbind])

        mock_protocol.send_pdu.assert_called_once()


class TestReaderLoopReconnect(TestCase):
    """
    Regression coverage for the self-healing reconnect behaviour: previously
    any error inside the reader coroutine (e.g. a dropped redis connection)
    caused it to exit silently and never resume, permanently losing all
    traps for that DB instance. _reader_loop() must instead log, back off,
    and retry.
    """

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.infra = TrapInfra(self.loop, None)
        self.infra.RECONNECT_BACKOFF_SECONDS = 0  # keep the test fast
        pattern = "__keyspace@6__:PSU_INFO|*"
        self.infra.redis_instances = {
            "redis": {
                "host": "127.0.0.1",
                "port": 6379,
                "keyPatterns": [pattern],
                "patternObjs": [pattern],
                "pubsub": None,
                "connection_obj": None,
            }
        }

    def tearDown(self):
        self.loop.close()

    def test_reconnects_after_subscribe_failure_instead_of_dying(self):
        attempts = {"count": 0}

        def fake_from_url(*args, **kwargs):
            attempts["count"] += 1
            pubsub = MagicMock()
            pubsub.close = AsyncMock()
            if attempts["count"] == 1:
                # Simulate a broken connection on the first attempt.
                pubsub.psubscribe = AsyncMock(side_effect=ConnectionError("boom"))
            else:
                # Second attempt succeeds and then idles until cancelled.
                pubsub.psubscribe = AsyncMock()

                async def hang_listen():
                    await asyncio.Event().wait()
                    yield  # pragma: no cover - never reached

                pubsub.listen = hang_listen

            conn = MagicMock()
            conn.pubsub = MagicMock(return_value=pubsub)
            return conn

        with patch.object(trap_module.redis, 'from_url', side_effect=fake_from_url):
            task = self.loop.create_task(self.infra._reader_loop("redis"))

            async def drive():
                await asyncio.sleep(0.05)
                # Must have reconnected at least once after the first failure.
                self.assertGreaterEqual(attempts["count"], 2)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task

            self.loop.run_until_complete(drive())

    def test_retries_even_if_pubsub_close_itself_fails_during_cleanup(self):
        attempts = {"count": 0}

        def fake_from_url(*args, **kwargs):
            attempts["count"] += 1
            pubsub = MagicMock()
            # Cleanup itself is broken too - the loop must not let this
            # secondary failure stop it from retrying.
            pubsub.close = AsyncMock(side_effect=RuntimeError("close failed"))
            pubsub.psubscribe = AsyncMock(side_effect=ConnectionError("boom"))
            conn = MagicMock()
            conn.pubsub = MagicMock(return_value=pubsub)
            return conn

        with patch.object(trap_module.redis, 'from_url', side_effect=fake_from_url):
            task = self.loop.create_task(self.infra._reader_loop("redis"))

            async def drive():
                await asyncio.sleep(0.05)
                self.assertGreaterEqual(attempts["count"], 2)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task

            self.loop.run_until_complete(drive())

    def test_cancellation_propagates_and_closes_pubsub(self):
        pubsub = MagicMock()
        pubsub.psubscribe = AsyncMock()
        pubsub.close = AsyncMock()

        async def hang_listen():
            await asyncio.Event().wait()
            yield  # pragma: no cover - never reached

        pubsub.listen = hang_listen
        conn = MagicMock()
        conn.pubsub = MagicMock(return_value=pubsub)

        with patch.object(trap_module.redis, 'from_url', return_value=conn):
            task = self.loop.create_task(self.infra._reader_loop("redis"))

            async def drive():
                await asyncio.sleep(0.02)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task

            self.loop.run_until_complete(drive())

        pubsub.close.assert_called_once()


class TestReaderLoopMessageFlow(TestCase):
    """
    End-to-end coverage of the new dispatch path: a real pubsub message is
    handed to _collect_traps() via loop.run_in_executor() (a real
    ThreadPoolExecutor, not mocked) and, once results come back on the event
    loop thread, _send_trap()/dispatch_trap() actually fires.
    """

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.infra = TrapInfra(self.loop, None)
        self.infra.RECONNECT_BACKOFF_SECONDS = 0
        pattern = "__keyspace@6__:PSU_INFO|*"
        self.handler = MagicMock()
        self.handler.trap_process.return_value = make_trap_result()
        self.infra.dbKeyToHandler = {pattern: [self.handler]}
        self.infra._compile_patterns()
        self.infra.redis_instances = {
            "redis": {
                "host": "127.0.0.1",
                "port": 6379,
                "keyPatterns": [pattern],
                "patternObjs": [pattern],
                "pubsub": None,
                "connection_obj": None,
            }
        }

    def tearDown(self):
        self.loop.close()
        TrapInfra.protocol_obj = None

    def test_message_is_processed_off_thread_and_trap_dispatched(self):
        mock_protocol = MagicMock()
        mock_protocol.session_id = 7
        TrapInfra.protocol_obj = mock_protocol

        pubsub = MagicMock()
        pubsub.psubscribe = AsyncMock()
        pubsub.close = AsyncMock()

        async def one_message_then_hang():
            yield {
                "type": "pmessage",
                "channel": b"__keyspace@6__:PSU_INFO|Psu2",
                "data": b"hset",
            }
            await asyncio.Event().wait()
            yield  # pragma: no cover - never reached

        pubsub.listen = one_message_then_hang
        conn = MagicMock()
        conn.pubsub = MagicMock(return_value=pubsub)

        with patch.object(trap_module.redis, 'from_url', return_value=conn):
            task = self.loop.create_task(self.infra._reader_loop("redis"))

            async def drive():
                # Give the executor round trip time to complete.
                await asyncio.sleep(0.1)
                self.handler.trap_process.assert_called_once()
                mock_protocol.send_pdu.assert_called_once()
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task

            self.loop.run_until_complete(drive())


class TestDbListener(TestCase):
    """
    db_listener() now only does setup (load config, compile/register
    patterns) and launches one self-healing _reader_loop() task per redis
    instance that actually has registered patterns - instances with no
    patterns must not get a wasted reader task.
    """

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.infra = TrapInfra(self.loop, None)

    def tearDown(self):
        self.loop.close()

    def test_creates_one_reader_task_per_instance_with_patterns(self):
        pattern = "__keyspace@6__:PSU_INFO|*"
        self.infra.dbKeyToHandler = {pattern: [MagicMock()]}

        def fake_load_db_config():
            self.infra.redis_instances = {
                "redis": {
                    "host": "127.0.0.1", "port": 6379,
                    "keyPatterns": [], "patternObjs": [],
                    "pubsub": None, "connection_obj": None,
                },
                "empty": {
                    "host": "127.0.0.1", "port": 6380,
                    "keyPatterns": [], "patternObjs": [],
                    "pubsub": None, "connection_obj": None,
                },
            }
            self.infra.db_to_redis_dict = {6: self.infra.redis_instances["redis"]}

        with patch.object(self.infra, '_load_db_config', side_effect=fake_load_db_config), \
             patch.object(self.infra, '_reader_loop', new_callable=AsyncMock) as mock_reader_loop:
            self.loop.run_until_complete(self.infra.db_listener())
            # AsyncMock resolves immediately; let the created task run to completion.
            self.loop.run_until_complete(asyncio.gather(*self.infra._reader_tasks))

        mock_reader_loop.assert_called_once_with("redis")
        self.assertEqual(len(self.infra._reader_tasks), 1)
        # The pattern was actually registered against the "redis" instance.
        self.assertEqual(
            self.infra.redis_instances["redis"]["patternObjs"], [pattern]
        )


class TestShutdown(TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.infra = TrapInfra(self.loop, None)

    def tearDown(self):
        self.loop.close()

    def test_shutdown_cancels_readers_closes_connections_and_executor(self):
        async def never_ending():
            await asyncio.Event().wait()

        task = self.loop.create_task(never_ending())
        self.infra._reader_tasks = [task]

        pubsub = MagicMock()
        pubsub.punsubscribe = AsyncMock()
        pubsub.close = AsyncMock()
        conn = MagicMock()
        conn.close = AsyncMock()

        self.infra.redis_instances = {
            "redis": {
                "host": "127.0.0.1",
                "port": 6379,
                "keyPatterns": ["__keyspace@6__:PSU_INFO|*"],
                "patternObjs": ["__keyspace@6__:PSU_INFO|*"],
                "pubsub": pubsub,
                "connection_obj": conn,
            }
        }

        self.loop.run_until_complete(self.infra.shutdown())

        self.assertTrue(task.cancelled())
        pubsub.punsubscribe.assert_called_once()
        pubsub.close.assert_called_once()
        conn.close.assert_called_once()

        # The executor must be shut down too - no new work can be scheduled.
        with self.assertRaises(RuntimeError):
            self.infra._executor.submit(lambda: None)

    def test_shutdown_tolerates_punsubscribe_and_close_failures(self):
        pubsub = MagicMock()
        pubsub.punsubscribe = AsyncMock(side_effect=RuntimeError("punsubscribe failed"))
        pubsub.close = AsyncMock(side_effect=RuntimeError("close failed"))
        conn = MagicMock()
        conn.close = AsyncMock(side_effect=RuntimeError("conn close failed"))

        self.infra.redis_instances = {
            "redis": {
                "host": "127.0.0.1",
                "port": 6379,
                "keyPatterns": ["__keyspace@6__:PSU_INFO|*"],
                "patternObjs": ["__keyspace@6__:PSU_INFO|*"],
                "pubsub": pubsub,
                "connection_obj": conn,
            }
        }

        # None of the individual cleanup failures above should propagate.
        self.loop.run_until_complete(self.infra.shutdown())

        pubsub.punsubscribe.assert_called_once()
        pubsub.close.assert_called_once()
        conn.close.assert_called_once()


class TestPatternHandling(TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.infra = TrapInfra(self.loop, None)

    def tearDown(self):
        self.loop.close()

    def test_compile_patterns_matches_wildcard_keys_only_in_scope(self):
        self.infra.dbKeyToHandler = {
            "__keyspace@6__:PSU_INFO|*": [MagicMock()],
        }
        self.infra._compile_patterns()

        cregex, handlers, original = self.infra._compiled_patterns[0]
        self.assertTrue(cregex.fullmatch("__keyspace@6__:PSU_INFO|Psu2"))
        self.assertFalse(cregex.fullmatch("__keyspace@6__:FAN_INFO|Fantray1_1"))
        self.assertFalse(cregex.fullmatch("__keyspace@4__:PSU_INFO|Psu2"))

    def test_register_pattern_requires_keyspace_prefix(self):
        self.infra.db_to_redis_dict = {6: {"patternObjs": [], "keyPatterns": []}}
        with self.assertRaises(RuntimeError):
            self.infra._register_pattern("PSU_INFO|*")

    def test_register_pattern_appends_to_matching_db_instance(self):
        target = {"patternObjs": [], "keyPatterns": []}
        self.infra.db_to_redis_dict = {6: target}

        self.infra._register_pattern("__keyspace@6__:PSU_INFO|*")

        self.assertEqual(target["patternObjs"], ["__keyspace@6__:PSU_INFO|*"])
        self.assertEqual(target["keyPatterns"], ["__keyspace@6__:PSU_INFO|*"])

    def test_invalid_compiled_pattern_is_logged_and_skipped(self):
        """
        re.escape() means a real invalid-regex pattern can't normally reach
        re.compile() here, but the except re.error branch is still there as
        a safety net - exercise it directly.
        """
        self.infra.dbKeyToHandler = {"__keyspace@6__:PSU_INFO|*": [MagicMock()]}

        with patch.object(trap_module.re, 'compile', side_effect=re.error("bad pattern")):
            self.infra._compile_patterns()

        self.assertEqual(self.infra._compiled_patterns, [])


class FakeTrapA(Trap):
    def __init__(self):
        super().__init__(dbKeys=["__keyspace@6__:PSU_INFO|*", "__keyspace@6__:FAN_INFO|*"])
        self.trap_init_called = False

    def trap_init(self):
        self.trap_init_called = True


class FakeTrapB(Trap):
    def __init__(self):
        super().__init__(dbKeys=["__keyspace@6__:PSU_INFO|*"])


class TestInitTrapHandlers(TestCase):
    """
    TrapInfra(loop, trap_handlers) instantiates each handler class, indexes
    it under every dbKey it declares, and calls trap_init() on it - this is
    how link_up_down_trap/psu_fan_trap get wired up at startup.
    """

    def setUp(self):
        self.loop = asyncio.new_event_loop()

    def tearDown(self):
        self.loop.close()

    def test_registers_handler_under_each_declared_dbkey_and_inits_it(self):
        infra = TrapInfra(self.loop, [FakeTrapA])

        self.assertIn("__keyspace@6__:PSU_INFO|*", infra.dbKeyToHandler)
        self.assertIn("__keyspace@6__:FAN_INFO|*", infra.dbKeyToHandler)

        handler = infra.dbKeyToHandler["__keyspace@6__:PSU_INFO|*"][0]
        self.assertIsInstance(handler, FakeTrapA)
        self.assertTrue(handler.trap_init_called)

    def test_multiple_handlers_sharing_a_dbkey_are_all_registered(self):
        infra = TrapInfra(self.loop, [FakeTrapA, FakeTrapB])

        handlers = infra.dbKeyToHandler["__keyspace@6__:PSU_INFO|*"]
        self.assertEqual(len(handlers), 2)
        self.assertEqual({type(h) for h in handlers}, {FakeTrapA, FakeTrapB})

    def test_trap_requires_dbkeys_list(self):
        with self.assertRaises(TypeError):
            Trap()


class TestLoadDbConfig(TestCase):
    """
    _load_db_config() reads $DB_CONFIG_FILE (sonic-db's database_config.json
    format) and builds redis_instances / db_to_redis_dict from it.
    """

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.infra = TrapInfra(self.loop, None)
        self._env_patcher = None

    def tearDown(self):
        self.loop.close()
        if self._env_patcher is not None:
            self._env_patcher.stop()

    def _use_config_file(self, content):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        json.dump(content, tmp)
        tmp.close()
        self._env_patcher = patch.dict(os.environ, {"DB_CONFIG_FILE": tmp.name})
        self._env_patcher.start()
        self.addCleanup(os.unlink, tmp.name)

    def test_missing_config_file_raises(self):
        self._env_patcher = patch.dict(
            os.environ, {"DB_CONFIG_FILE": "/nonexistent/database_config.json"}
        )
        self._env_patcher.start()

        with self.assertRaises(RuntimeError):
            self.infra._load_db_config()

    def test_missing_instances_key_raises(self):
        self._use_config_file({"DATABASES": {}})

        with self.assertRaises(RuntimeError):
            self.infra._load_db_config()

    def test_database_referencing_unknown_instance_raises(self):
        self._use_config_file({
            "INSTANCES": {
                "redis": {"hostname": "127.0.0.1", "port": 6379},
            },
            "DATABASES": {
                "STATE_DB": {"id": 6, "instance": "does_not_exist"},
            },
        })

        with self.assertRaises(RuntimeError):
            self.infra._load_db_config()

    def test_valid_config_populates_instances_and_db_mapping(self):
        self._use_config_file({
            "INSTANCES": {
                "redis": {"hostname": "127.0.0.1", "port": 6379},
                "redis_bmp": {"hostname": "127.0.0.1", "port": 6400},
            },
            "DATABASES": {
                "STATE_DB": {"id": 6, "instance": "redis"},
                "APPL_DB": {"id": 0, "instance": "redis"},
            },
        })

        self.infra._load_db_config()

        self.assertEqual(set(self.infra.redis_instances.keys()), {"redis", "redis_bmp"})
        self.assertEqual(self.infra.redis_instances["redis"]["host"], "127.0.0.1")
        self.assertEqual(self.infra.redis_instances["redis"]["port"], 6379)
        self.assertIs(self.infra.db_to_redis_dict[6], self.infra.redis_instances["redis"])
        self.assertIs(self.infra.db_to_redis_dict[0], self.infra.redis_instances["redis"])
        # An instance with no DB mapped to it is still created, just unused.
        self.assertNotIn(
            self.infra.redis_instances["redis_bmp"],
            self.infra.db_to_redis_dict.values(),
        )


class TestTrapBaseClassDefaults(TestCase):
    """The default Trap.trap_init()/trap_process() are no-op hooks children
    are expected to override; just confirm they exist and don't raise."""

    def test_defaults_are_callable_and_return_none(self):
        t = Trap(dbKeys=["__keyspace@6__:PSU_INFO|*"])
        self.assertIsNone(t.trap_init())
        self.assertIsNone(t.trap_process({}, "__keyspace@6__:PSU_INFO|Psu1"))
