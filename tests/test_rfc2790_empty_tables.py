import os
import sys

# noinspection PyUnresolvedReferences
import tests.mock_tables.dbconnector

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

from unittest import TestCase
from unittest.mock import patch, MagicMock

from sonic_ax_impl.mibs.ietf import rfc2790
from sonic_ax_impl import mibs


class TestFsHandlerNoMountPoints(TestCase):
    """Test fsHandler when no MOUNT_POINTS entries exist in STATE_DB."""

    def _create_handler_with_empty_keys(self):
        """Helper to create an fsHandler with statedb.keys returning None."""
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.return_value = None
            handler = rfc2790.fsHandler()
        return handler, mock_db

    def test_init_fs_no_mount_points_logs_debug(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.return_value = []

            with patch.object(mibs.logger, 'info') as mock_info:
                handler = rfc2790.fsHandler()
                mock_info.assert_any_call(
                    'init_fs - No mount point found in STATE_DB MOUNT_POINTS table'
                )

    def test_fs_entries_empty_when_no_mount_points(self):
        handler, _ = self._create_handler_with_empty_keys()
        self.assertEqual(handler.fs_entries, [])

    def test_get_next_none_returns_none_when_no_mount_points(self):
        handler, mock_db = self._create_handler_with_empty_keys()
        mock_db.keys.return_value = None
        result = handler.get_next(None)
        self.assertIsNone(result)

    def test_get_next_with_sub_id_returns_none_when_no_mount_points(self):
        handler, mock_db = self._create_handler_with_empty_keys()
        mock_db.keys.return_value = None
        result = handler.get_next((1,))
        self.assertIsNone(result)

    def test_get_fs_type_returns_none_for_none_sub_id(self):
        handler, _ = self._create_handler_with_empty_keys()
        self.assertIsNone(handler.get_fs_type(None))

    def test_get_fs_mount_returns_none_for_none_sub_id(self):
        handler, _ = self._create_handler_with_empty_keys()
        self.assertIsNone(handler.get_fs_mount(None))


class TestFsHandlerNoMemoryStats(TestCase):
    """Test fsHandler when MOUNT_POINTS exist but no MEMORY_STATS entries."""

    def _keys_side_effect(self, db, pattern):
        if 'MOUNT_POINTS' in pattern:
            return ['MOUNT_POINTS|/dev']
        if 'MEMORY_STATS' in pattern:
            return []
        return None

    def _create_handler_no_memory_stats(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = self._keys_side_effect
            mock_db.get_all.return_value = {
                'Type': 'ext4', 'MountPoint': '/dev'
            }
            handler = rfc2790.fsHandler()
        return handler, mock_db

    def test_init_fs_no_memory_stats_logs_debug(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = self._keys_side_effect
            mock_db.get_all.return_value = {
                'Type': 'ext4', 'MountPoint': '/dev'
            }

            with patch.object(mibs.logger, 'info') as mock_info:
                handler = rfc2790.fsHandler()
                mock_info.assert_any_call(
                    'init_fs - No memory stats found in STATE_DB MEMORY_STATS table'
                )

    def test_fs_entries_has_mount_points_when_no_memory_stats(self):
        handler, _ = self._create_handler_no_memory_stats()
        self.assertEqual(handler.fs_entries, ['MOUNT_POINTS|/dev'])

    def test_get_next_none_returns_first_when_no_memory_stats(self):
        handler, mock_db = self._create_handler_no_memory_stats()
        mock_db.keys.side_effect = self._keys_side_effect
        mock_db.get_all.return_value = {
            'Type': 'ext4', 'MountPoint': '/dev'
        }
        result = handler.get_next(None)
        self.assertEqual(result, (1,))

    def test_get_next_with_sub_id_returns_none_past_end_when_no_memory_stats(self):
        handler, _ = self._create_handler_no_memory_stats()
        result = handler.get_next((len(handler.fs_entries),))
        self.assertIsNone(result)


class TestFsHandlerNeitherMountPointsNorMemoryStats(TestCase):
    """Test fsHandler when neither MOUNT_POINTS nor MEMORY_STATS exist."""

    def test_init_fs_logs_mount_points_missing_and_continues(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.return_value = []

            with patch.object(mibs.logger, 'info') as mock_info:
                handler = rfc2790.fsHandler()
                mock_info.assert_any_call(
                    'init_fs - No mount point found in STATE_DB MOUNT_POINTS table'
                )
                mock_info.assert_any_call(
                    'init_fs - No memory stats found in STATE_DB MEMORY_STATS table'
                )

            self.assertEqual(handler.fs_entries, [])


class TestHrStorageHandlerNoMountPoints(TestCase):
    """Test hrStorageHandler when no MOUNT_POINTS entries exist in STATE_DB."""

    def _create_handler_with_empty_keys(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.return_value = None
            handler = rfc2790.hrStorageHandler()
        return handler, mock_db

    def test_init_hr_storage_no_mount_points_logs_debug(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.return_value = []

            with patch.object(mibs.logger, 'info') as mock_info:
                handler = rfc2790.hrStorageHandler()
                mock_info.assert_any_call(
                    'init_hr_storage - No mount point found in STATE_DB MOUNT_POINTS table'
                )

    def test_hr_storage_entries_empty_when_no_mount_points(self):
        handler, _ = self._create_handler_with_empty_keys()
        self.assertEqual(handler.hr_storage_entries, [])

    def test_get_next_none_returns_none_when_no_mount_points(self):
        handler, mock_db = self._create_handler_with_empty_keys()
        mock_db.keys.return_value = None
        result = handler.get_next(None)
        self.assertIsNone(result)

    def test_get_next_with_sub_id_returns_none_when_no_mount_points(self):
        handler, mock_db = self._create_handler_with_empty_keys()
        mock_db.keys.return_value = None
        result = handler.get_next((1,))
        self.assertIsNone(result)

    def test_get_hrstorage_used_returns_none_for_none_sub_id(self):
        handler, _ = self._create_handler_with_empty_keys()
        self.assertIsNone(handler.get_hrstorage_used(None))

    def test_get_hrstorage_size_returns_none_for_none_sub_id(self):
        handler, _ = self._create_handler_with_empty_keys()
        self.assertIsNone(handler.get_hrstorage_size(None))

    def test_get_hrstorage_descr_returns_none_for_none_sub_id(self):
        handler, _ = self._create_handler_with_empty_keys()
        self.assertIsNone(handler.get_hrstorage_descr(None))

    def test_get_hrstorage_alloc_returns_none_for_none_sub_id(self):
        handler, _ = self._create_handler_with_empty_keys()
        self.assertIsNone(handler.get_hrstorage_alloc(None))


class TestHrStorageHandlerNoMemoryStats(TestCase):
    """Test hrStorageHandler when MOUNT_POINTS exist but no MEMORY_STATS."""

    def _keys_side_effect(self, db, pattern):
        if 'MOUNT_POINTS' in pattern:
            return ['MOUNT_POINTS|/dev']
        if 'MEMORY_STATS' in pattern:
            return []
        return None

    def _create_handler_no_memory_stats(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = self._keys_side_effect
            mock_db.get_all.return_value = {
                '1K-blocks': '52829740', 'Used': '0',
                'Filesystem': '/host'
            }
            handler = rfc2790.hrStorageHandler()
        return handler, mock_db

    def test_init_hr_storage_no_memory_stats_logs_debug(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = self._keys_side_effect
            mock_db.get_all.return_value = {
                '1K-blocks': '52829740', 'Used': '0',
                'Filesystem': '/host'
            }

            with patch.object(mibs.logger, 'info') as mock_info:
                handler = rfc2790.hrStorageHandler()
                mock_info.assert_any_call(
                    'init_hr_storage - No memory stats found in STATE_DB MEMORY_STATS table'
                )

    def test_hr_storage_entries_has_mount_points_when_no_memory_stats(self):
        handler, _ = self._create_handler_no_memory_stats()
        self.assertEqual(handler.hr_storage_entries, ['MOUNT_POINTS|/dev'])

    def test_get_next_none_returns_first_when_no_memory_stats(self):
        handler, mock_db = self._create_handler_no_memory_stats()
        mock_db.keys.side_effect = self._keys_side_effect
        mock_db.get_all.return_value = {
            '1K-blocks': '52829740', 'Used': '0',
            'Filesystem': '/host'
        }
        result = handler.get_next(None)
        self.assertEqual(result, (1,))

    def test_get_next_with_sub_id_returns_none_past_end_when_no_memory_stats(self):
        handler, _ = self._create_handler_no_memory_stats()
        result = handler.get_next((len(handler.hr_storage_entries),))
        self.assertIsNone(result)


class TestHrStorageHandlerNeitherMountPointsNorMemoryStats(TestCase):
    """Test hrStorageHandler when neither MOUNT_POINTS nor MEMORY_STATS exist."""

    def test_init_hr_storage_logs_mount_points_missing_and_continues(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.return_value = []

            with patch.object(mibs.logger, 'info') as mock_info:
                handler = rfc2790.hrStorageHandler()
                mock_info.assert_any_call(
                    'init_hr_storage - No mount point found in STATE_DB MOUNT_POINTS table'
                )
                mock_info.assert_any_call(
                    'init_hr_storage - No memory stats found in STATE_DB MEMORY_STATS table'
                )

            self.assertEqual(handler.hr_storage_entries, [])


# ===================================================================
# Tests for stale data clearing after Redis is emptied
# ===================================================================

def _populated_keys_side_effect(db, pattern):
    """Return realistic MOUNT_POINTS and MEMORY_STATS keys."""
    if 'MOUNT_POINTS' in pattern:
        return ['MOUNT_POINTS|/dev', 'MOUNT_POINTS|/dev2']
    if 'MEMORY_STATS' in pattern:
        return ['MEMORY_STATS|Physical']
    return None


def _populated_get_all_side_effect(db, key):
    """Return realistic field data for each key."""
    data = {
        'MOUNT_POINTS|/dev': {
            'Type': 'ext4', 'MountPoint': '/dev',
            '1K-blocks': '52829740', 'Used': '0', 'Filesystem': '/host',
        },
        'MOUNT_POINTS|/dev2': {
            'Type': 'ext3', 'MountPoint': '/dev2',
            '1K-blocks': '12345', 'Used': '10', 'Filesystem': '/host2',
        },
        'MEMORY_STATS|Physical': {
            '1K-blocks': '100000', 'Used': '1000',
        },
    }
    return data.get(key, {})


class TestFsHandlerStaleDataClearing(TestCase):
    """Verify that fsHandler clears stale cached entries when Redis is emptied."""

    def _create_populated_handler(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = _populated_keys_side_effect
            mock_db.get_all.side_effect = _populated_get_all_side_effect
            handler = rfc2790.fsHandler()
        return handler, mock_db

    def test_stale_fs_entries_cleared_when_mount_points_emptied(self):
        handler, mock_db = self._create_populated_handler()
        self.assertGreater(len(handler.fs_entries), 0,
                           "Precondition: handler should start with entries")

        mock_db.keys.side_effect = None
        mock_db.keys.return_value = None
        result = handler.get_next(None)

        self.assertIsNone(result)
        self.assertEqual(handler.fs_entries, [])

    def test_stale_fs_entries_updated_when_memory_stats_emptied(self):
        handler, mock_db = self._create_populated_handler()
        original_count = len(handler.fs_entries)
        self.assertGreater(original_count, 0)

        def keys_no_memory(db, pattern):
            if 'MOUNT_POINTS' in pattern:
                return ['MOUNT_POINTS|/dev']
            if 'MEMORY_STATS' in pattern:
                return None
            return None

        mock_db.keys.side_effect = keys_no_memory
        mock_db.get_all.side_effect = _populated_get_all_side_effect
        result = handler.get_next(None)

        self.assertEqual(result, (1,))
        self.assertEqual(handler.fs_entries, ['MOUNT_POINTS|/dev'])

    def test_reinit_data_clears_stale_fs_entries(self):
        handler, mock_db = self._create_populated_handler()
        self.assertGreater(len(handler.fs_entries), 0)

        mock_db.keys.side_effect = None
        mock_db.keys.return_value = None
        handler.reinit_data()

        self.assertEqual(handler.fs_entries, [])

    def test_reinit_data_repopulates_fs_entries(self):
        handler, mock_db = self._create_populated_handler()
        mock_db.keys.side_effect = None
        mock_db.keys.return_value = None
        handler.reinit_data()
        self.assertEqual(handler.fs_entries, [])

        mock_db.keys.side_effect = _populated_keys_side_effect
        mock_db.get_all.side_effect = _populated_get_all_side_effect
        handler.reinit_data()
        self.assertGreater(len(handler.fs_entries), 0)


class TestHrStorageHandlerStaleDataClearing(TestCase):
    """Verify that hrStorageHandler clears stale cached entries when Redis is emptied."""

    def _create_populated_handler(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = _populated_keys_side_effect
            mock_db.get_all.side_effect = _populated_get_all_side_effect
            handler = rfc2790.hrStorageHandler()
        return handler, mock_db

    def test_stale_hr_storage_entries_cleared_when_mount_points_emptied(self):
        handler, mock_db = self._create_populated_handler()
        self.assertGreater(len(handler.hr_storage_entries), 0,
                           "Precondition: handler should start with entries")

        mock_db.keys.side_effect = None
        mock_db.keys.return_value = None
        result = handler.get_next(None)

        self.assertIsNone(result)
        self.assertEqual(handler.hr_storage_entries, [])

    def test_stale_hr_storage_entries_updated_when_memory_stats_emptied(self):
        handler, mock_db = self._create_populated_handler()
        self.assertGreater(len(handler.hr_storage_entries), 0)

        def keys_no_memory(db, pattern):
            if 'MOUNT_POINTS' in pattern:
                return ['MOUNT_POINTS|/dev']
            if 'MEMORY_STATS' in pattern:
                return None
            return None

        mock_db.keys.side_effect = keys_no_memory
        mock_db.get_all.side_effect = _populated_get_all_side_effect
        result = handler.get_next(None)

        self.assertEqual(result, (1,))
        self.assertEqual(handler.hr_storage_entries, ['MOUNT_POINTS|/dev'])

    def test_reinit_data_clears_stale_hr_storage_entries(self):
        handler, mock_db = self._create_populated_handler()
        self.assertGreater(len(handler.hr_storage_entries), 0)

        mock_db.keys.side_effect = None
        mock_db.keys.return_value = None
        handler.reinit_data()

        self.assertEqual(handler.hr_storage_entries, [])

    def test_reinit_data_repopulates_hr_storage_entries(self):
        handler, mock_db = self._create_populated_handler()
        mock_db.keys.side_effect = None
        mock_db.keys.return_value = None
        handler.reinit_data()
        self.assertEqual(handler.hr_storage_entries, [])

        mock_db.keys.side_effect = _populated_keys_side_effect
        mock_db.get_all.side_effect = _populated_get_all_side_effect
        handler.reinit_data()
        self.assertGreater(len(handler.hr_storage_entries), 0)


# ===================================================================
# Tests for out-of-bounds and empty-list getter safety
# ===================================================================

class TestFsHandlerGetterBoundsChecking(TestCase):
    """Verify fsHandler getters return None for out-of-bounds or empty entries."""

    def _create_handler_with_empty_keys(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.return_value = None
            handler = rfc2790.fsHandler()
        return handler, mock_db

    def _create_populated_handler(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = _populated_keys_side_effect
            mock_db.get_all.side_effect = _populated_get_all_side_effect
            handler = rfc2790.fsHandler()
        return handler, mock_db

    def test_get_fs_type_returns_none_on_empty_entries(self):
        handler, _ = self._create_handler_with_empty_keys()
        self.assertIsNone(handler.get_fs_type((1,)))

    def test_get_fs_mount_returns_none_on_empty_entries(self):
        handler, _ = self._create_handler_with_empty_keys()
        self.assertIsNone(handler.get_fs_mount((1,)))

    def test_get_fs_type_returns_none_for_out_of_bounds(self):
        handler, _ = self._create_populated_handler()
        oob_index = len(handler.fs_entries) + 1
        self.assertIsNone(handler.get_fs_type((oob_index,)))

    def test_get_fs_mount_returns_none_for_out_of_bounds(self):
        handler, _ = self._create_populated_handler()
        oob_index = len(handler.fs_entries) + 1
        self.assertIsNone(handler.get_fs_mount((oob_index,)))

    def test_get_next_past_last_entry_returns_none(self):
        handler, _ = self._create_populated_handler()
        last_index = len(handler.fs_entries)
        self.assertIsNone(handler.get_next((last_index,)))


class TestHrStorageHandlerGetterBoundsChecking(TestCase):
    """Verify hrStorageHandler getters return None for out-of-bounds or empty entries."""

    def _create_handler_with_empty_keys(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.return_value = None
            handler = rfc2790.hrStorageHandler()
        return handler, mock_db

    def _create_populated_handler(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = _populated_keys_side_effect
            mock_db.get_all.side_effect = _populated_get_all_side_effect
            handler = rfc2790.hrStorageHandler()
        return handler, mock_db

    def test_get_hrstorage_used_returns_none_on_empty_entries(self):
        handler, _ = self._create_handler_with_empty_keys()
        self.assertIsNone(handler.get_hrstorage_used((1,)))

    def test_get_hrstorage_size_returns_none_on_empty_entries(self):
        handler, _ = self._create_handler_with_empty_keys()
        self.assertIsNone(handler.get_hrstorage_size((1,)))

    def test_get_hrstorage_descr_returns_none_on_empty_entries(self):
        handler, _ = self._create_handler_with_empty_keys()
        self.assertIsNone(handler.get_hrstorage_descr((1,)))

    def test_get_hrstorage_used_returns_none_for_out_of_bounds(self):
        handler, _ = self._create_populated_handler()
        oob_index = len(handler.hr_storage_entries) + 1
        self.assertIsNone(handler.get_hrstorage_used((oob_index,)))

    def test_get_hrstorage_size_returns_none_for_out_of_bounds(self):
        handler, _ = self._create_populated_handler()
        oob_index = len(handler.hr_storage_entries) + 1
        self.assertIsNone(handler.get_hrstorage_size((oob_index,)))

    def test_get_hrstorage_descr_returns_none_for_out_of_bounds(self):
        handler, _ = self._create_populated_handler()
        oob_index = len(handler.hr_storage_entries) + 1
        self.assertIsNone(handler.get_hrstorage_descr((oob_index,)))

    def test_get_next_past_last_entry_returns_none(self):
        handler, _ = self._create_populated_handler()
        last_index = len(handler.hr_storage_entries)
        self.assertIsNone(handler.get_next((last_index,)))


# ===================================================================
# Tests for _db_call helper and STATE_DB access failure paths
# ===================================================================

class TestDbCallHelper(TestCase):
    """Verify _db_call logs errors and returns None on exception,
    and returns results on success."""

    def test_db_call_returns_result_on_success(self):
        mock_func = MagicMock(return_value=['key1', 'key2'])
        result = rfc2790._db_call(mock_func, 'test_context', 'arg1', 'arg2')
        self.assertEqual(result, ['key1', 'key2'])
        mock_func.assert_called_once_with('arg1', 'arg2')

    def test_db_call_returns_none_on_success(self):
        mock_func = MagicMock(return_value=None)
        result = rfc2790._db_call(mock_func, 'test_context', 'arg1')
        self.assertIsNone(result)

    def test_db_call_logs_and_returns_none_on_exception(self):
        mock_func = MagicMock(side_effect=ConnectionError("Redis unavailable"))
        with patch.object(mibs.logger, 'error') as mock_error:
            result = rfc2790._db_call(mock_func, 'MY_TABLE', 'arg1')
            self.assertIsNone(result)
            mock_error.assert_called_once()
            self.assertIn('MY_TABLE', mock_error.call_args[0][0])
            self.assertIn('Redis unavailable', mock_error.call_args[0][0])


class TestFsHandlerDbAccessFailure(TestCase):
    """Verify fsHandler degrades gracefully when STATE_DB operations throw."""

    def test_connect_failure_degrades_gracefully(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.connect.side_effect = ConnectionError("Redis down")
            mock_db.keys.return_value = None
            handler = rfc2790.fsHandler()
            self.assertEqual(handler.fs_entries, [])

    def test_connect_failure_logs_error(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.connect.side_effect = ConnectionError("Redis down")
            mock_db.keys.return_value = None
            with patch.object(mibs.logger, 'error') as mock_error:
                handler = rfc2790.fsHandler()
                mock_error.assert_called()
                error_messages = [str(c) for c in mock_error.call_args_list]
                self.assertTrue(
                    any('Redis down' in msg for msg in error_messages))

    def test_init_fs_keys_failure_degrades_gracefully(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = ConnectionError("Redis gone")
            handler = rfc2790.fsHandler()
            self.assertEqual(handler.fs_entries, [])

    def test_init_fs_get_all_failure_degrades_gracefully(self):
        def keys_side_effect(db, pattern):
            if 'MOUNT_POINTS' in pattern:
                return ['MOUNT_POINTS|/dev']
            return None

        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = keys_side_effect
            mock_db.get_all.side_effect = ConnectionError("Redis timeout")
            handler = rfc2790.fsHandler()
            self.assertEqual(handler.fs_entries, [])

    def test_init_fs_memory_stats_keys_failure_keeps_mount_points(self):
        def keys_side_effect(db, pattern):
            if 'MOUNT_POINTS' in pattern:
                return ['MOUNT_POINTS|/dev']
            if 'MEMORY_STATS' in pattern:
                raise ConnectionError("Redis lost")
            return None

        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = keys_side_effect
            mock_db.get_all.return_value = {
                'Type': 'ext4', 'MountPoint': '/dev'
            }
            handler = rfc2790.fsHandler()
            self.assertEqual(handler.fs_entries, ['MOUNT_POINTS|/dev'])

    def test_get_fs_type_db_failure_returns_none(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = _populated_keys_side_effect
            mock_db.get_all.side_effect = _populated_get_all_side_effect
            handler = rfc2790.fsHandler()

        mock_db.get_all.side_effect = ConnectionError("Redis error")
        result = handler.get_fs_type((1,))
        self.assertIsNone(result)

    def test_get_fs_mount_db_failure_returns_none(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = _populated_keys_side_effect
            mock_db.get_all.side_effect = _populated_get_all_side_effect
            handler = rfc2790.fsHandler()

        mock_db.get_all.side_effect = ConnectionError("Redis error")
        result = handler.get_fs_mount((1,))
        self.assertIsNone(result)


class TestHrStorageHandlerDbAccessFailure(TestCase):
    """Verify hrStorageHandler degrades gracefully when STATE_DB operations throw."""

    def test_connect_failure_degrades_gracefully(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.connect.side_effect = ConnectionError("Redis down")
            mock_db.keys.return_value = None
            handler = rfc2790.hrStorageHandler()
            self.assertEqual(handler.hr_storage_entries, [])

    def test_connect_failure_logs_error(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.connect.side_effect = ConnectionError("Redis down")
            mock_db.keys.return_value = None
            with patch.object(mibs.logger, 'error') as mock_error:
                handler = rfc2790.hrStorageHandler()
                mock_error.assert_called()
                error_messages = [str(c) for c in mock_error.call_args_list]
                self.assertTrue(
                    any('Redis down' in msg for msg in error_messages))

    def test_init_hr_storage_keys_failure_degrades_gracefully(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = ConnectionError("Redis gone")
            handler = rfc2790.hrStorageHandler()
            self.assertEqual(handler.hr_storage_entries, [])

    def test_init_hr_storage_get_all_failure_degrades_gracefully(self):
        def keys_side_effect(db, pattern):
            if 'MOUNT_POINTS' in pattern:
                return ['MOUNT_POINTS|/dev']
            return None

        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = keys_side_effect
            mock_db.get_all.side_effect = ConnectionError("Redis timeout")
            handler = rfc2790.hrStorageHandler()
            self.assertEqual(handler.hr_storage_entries, [])

    def test_init_hr_storage_memory_stats_keys_failure_keeps_mount_points(self):
        def keys_side_effect(db, pattern):
            if 'MOUNT_POINTS' in pattern:
                return ['MOUNT_POINTS|/dev']
            if 'MEMORY_STATS' in pattern:
                raise ConnectionError("Redis lost")
            return None

        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = keys_side_effect
            mock_db.get_all.return_value = {
                '1K-blocks': '52829740', 'Used': '0', 'Filesystem': '/host'
            }
            handler = rfc2790.hrStorageHandler()
            self.assertEqual(handler.hr_storage_entries, ['MOUNT_POINTS|/dev'])

    def test_get_hrstorage_used_db_failure_returns_none(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = _populated_keys_side_effect
            mock_db.get_all.side_effect = _populated_get_all_side_effect
            handler = rfc2790.hrStorageHandler()

        mock_db.get_all.side_effect = ConnectionError("Redis error")
        result = handler.get_hrstorage_used((1,))
        self.assertIsNone(result)

    def test_get_hrstorage_size_db_failure_returns_none(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = _populated_keys_side_effect
            mock_db.get_all.side_effect = _populated_get_all_side_effect
            handler = rfc2790.hrStorageHandler()

        mock_db.get_all.side_effect = ConnectionError("Redis error")
        result = handler.get_hrstorage_size((1,))
        self.assertIsNone(result)

    def test_get_hrstorage_descr_db_failure_returns_none(self):
        with patch.object(rfc2790.mibs, 'init_db') as mock_init_db:
            mock_db = MagicMock()
            mock_init_db.return_value = mock_db
            mock_db.STATE_DB = 'STATE_DB'
            mock_db.keys.side_effect = _populated_keys_side_effect
            mock_db.get_all.side_effect = _populated_get_all_side_effect
            handler = rfc2790.hrStorageHandler()

        mock_db.get_all.side_effect = ConnectionError("Redis error")
        result = handler.get_hrstorage_descr((1,))
        self.assertIsNone(result)

