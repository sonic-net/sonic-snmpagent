# MONKEY PATCH!!!
import json
import os

import mockredis
from swsssdk.interface import redis, DBInterface
from swsssdk import SonicV2Connector
from swsssdk import SonicDBConfig
from sonic_py_common import multi_asic


def clean_up_config():
    # Set SonicDBConfig variables to initial state
    # so that it can be loaded with single or multiple
    # namespaces before the test begins.
    SonicDBConfig._sonic_db_config = {}
    SonicDBConfig._sonic_db_global_config_init = False
    SonicDBConfig._sonic_db_config_init = False


# TODO Convert this to fixture as all Test classes require it.
def load_namespace_config():
    # To support testing single namespace and multiple
    # namespace scenario, SonicDBConfig load_sonic_global_db_config
    # is invoked to load multiple namespaces to support multiple
    # namespace testing.
    clean_up_config()
    SonicDBConfig.load_sonic_global_db_config(
        global_db_file_path=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'database_global.json'))


# TODO Convert this to fixture as all Test classes require it.
def load_database_config():
    # Load local database_config.json for single namespace test scenario
    clean_up_config()
    SonicDBConfig.load_sonic_db_config(
        sonic_db_file_path=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'database_config.json'))

_old_connect_SonicV2Connector = SonicV2Connector.connect

def connect_SonicV2Connector(self, db_name, retry_on=True):
    ns_list = SonicDBConfig.get_ns_list()
    # In case of multiple namespaces, namespace string passed to
    # SonicV2Connector will specify the namespace or can be empty.
    # Empty namespace represents global or host namespace.
    if len(ns_list) > 1 and self.namespace == "":
        self.dbintf.redis_kwargs['namespace'] = "global_db"
    else:
        self.dbintf.redis_kwargs['namespace'] = self.namespace
    # Mock DB filename for unit-test
    self.dbintf.redis_kwargs['db_name'] = db_name
    _old_connect_SonicV2Connector(self, db_name, retry_on)


def _subscribe_keyspace_notification(self, db_name, client):
    pass


def config_set(self, *args):
    pass


class MockPubSub:
    def get_message(self):
        return None

    def psubscribe(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return self


INPUT_DIR = os.path.dirname(os.path.abspath(__file__))


class SwssSyncClient(mockredis.MockRedis):
    def __init__(self, *args, **kwargs):
        super(SwssSyncClient, self).__init__(strict=True, *args, **kwargs)
        # Namespace is added in kwargs specifically for unit-test
        # to identify the file path to load the db json files.
        namespace = kwargs.pop('namespace')
        db_name = kwargs.pop('db_name')
        fname = db_name.lower() + ".json"
        self.pubsub = MockPubSub()

        if namespace is not None:
            fname = os.path.join(INPUT_DIR, namespace, fname)
        else:
            fname = os.path.join(INPUT_DIR, fname)

        with open(fname) as f:
            js = json.load(f)
            for h, table in js.items():
                for k, v in table.items():
                    self.hset(h, k, v)

    # Patch mockredis/mockredis/client.py
    # The official implementation will filter out keys with a slash '/'
    # ref: https://github.com/locationlabs/mockredis/blob/master/mockredis/client.py
    def keys(self, pattern='*'):
        """Emulate keys."""
        import fnmatch
        import re

        # making sure the pattern is unicode/str.
        try:
            pattern = pattern.decode('utf-8')
            # This throws an AttributeError in python 3, or an
            # UnicodeEncodeError in python 2
        except (AttributeError, UnicodeEncodeError):
            pass

        # Make regex out of glob styled pattern.
        regex = fnmatch.translate(pattern)
        regex = re.compile(regex)

        # Find every key that matches the pattern
        return [key for key in self.redis.keys() if regex.match(key.decode('utf-8'))]

def mock_get_num_asics():
    ns_list = SonicDBConfig.get_ns_list()
    if len(ns_list) > 1:
        return(len(ns_list) - 1)
    else:
        return 1


def mock_is_multi_asic():
    if mock_get_num_asics() > 1:
        return True
    else:
        return False

def mock_get_all_namespaces():
   if mock_get_num_asics() == 1:
       return {'front_ns': [], 'back_ns': []}
   else:
       return {'front_ns': ['asic0', 'asic1'], 'back_ns': ['asic2']}

def mock_is_port_channel_internal(port_channel, namespace=None):
    if (mock_get_num_asics() == 1):
        return False
    else:
        return True if '_BP' in port_channel else False


multi_asic.get_num_asics = mock_get_num_asics
multi_asic.is_multi_asic = mock_is_multi_asic
multi_asic.get_all_namespaces = mock_get_all_namespaces
multi_asic.is_port_channel_internal = mock_is_port_channel_internal

DBInterface._subscribe_keyspace_notification = _subscribe_keyspace_notification
mockredis.MockRedis.config_set = config_set
redis.StrictRedis = SwssSyncClient
SonicV2Connector.connect = connect_SonicV2Connector
