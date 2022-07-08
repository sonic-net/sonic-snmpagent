# MONKEY PATCH!!!
import json
import os
import sys

import mockredis
import redis
from swsscommon.swsscommon import SonicV2Connector_Native, SonicDBConfig, DBInterface
from swsscommon import swsscommon
from sonic_py_common import multi_asic


if sys.version_info >= (3, 0):
    long = int
    xrange = range
    basestring = str

def clean_up_config():
    # Set SonicDBConfig variables to initial state
    # so that it can be loaded with single or multiple
    # namespaces before the test begins.
    SonicDBConfig._sonic_db_config = {}
    SonicDBConfig._sonic_db_global_config_init = False
    SonicDBConfig._sonic_db_config_init = False

def mock_SonicDBConfig_isGlobalInit():
    return SonicDBConfig._sonic_db_global_config_init


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

class MockSonicV2Connector(SonicV2Connector_Native):
    ## Note: there is no easy way for SWIG to map ctor parameter netns(C++) to namespace(python)
    def __init__(self, use_unix_socket_path = False, namespace = '', **kwargs):
        if 'host' in kwargs:
            # Note: host argument will be ignored, same as in sonic-py-swsssdk
            kwargs.pop('host')
        if 'decode_responses' in kwargs and kwargs.pop('decode_responses') != True:
            raise ValueError('decode_responses must be True if specified, False is not supported')
        ns_list = SonicDBConfig.get_ns_list()
        if len(ns_list) > 1 and (namespace == "" or namespace == None):
             namespace = 'global_db'
        super(MockSonicV2Connector, self).__init__(use_unix_socket_path = use_unix_socket_path, netns = namespace)

        # Add database name attributes into MockSonicV2Connector instance
        # Note: this is difficult to implement in C++
        for db_name in self.get_db_list():
            # set a database name as a constant value attribute.
            setattr(self, db_name, db_name)

    @property
    def namespace(self):
        return self.getNamespace()

    def get_all(self, db_name, _hash, blocking=False):
        return dict(super(MockSonicV2Connector, self).get_all(db_name, _hash, blocking))

    def keys(self, *args, **kwargs):
        return list(super(MockSonicV2Connector, self).keys(*args, **kwargs))


def _subscribe_keyspace_notification(self, db_name):
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
        self.decode_responses = kwargs.pop('decode_responses', False) == True
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
    # The offical implementation assume decode_responses=False
    # Here we detect the option and decode after doing encode
    def _encode(self, value):
        "Return a bytestring representation of the value. Taken from redis-py connection.py"

        value = super(SwssSyncClient, self)._encode(value)

        if self.decode_responses:
           return value.decode('utf-8')

    # Patch mockredis/mockredis/client.py
    # The official implementation will filter out keys with a slash '/'
    # ref: https://github.com/locationlabs/mockredis/blob/master/mockredis/client.py
    def keys(self, pattern='*'):
        """Emulate keys."""
        import fnmatch
        import re

        # Make regex out of glob styled pattern.
        regex = fnmatch.translate(pattern)
        regex = re.compile(regex)

        # Find every key that matches the pattern
        return [key for key in self.redis.keys() if regex.match(key)]

DBInterface._subscribe_keyspace_notification = _subscribe_keyspace_notification
mockredis.MockRedis.config_set = config_set
redis.StrictRedis = SwssSyncClient
swsscommon.SonicV2Connector = MockSonicV2Connector
swsscommon.SonicDBConfig = SonicDBConfig
swsscommon.SonicDBConfig.isGlobalInit = mock_SonicDBConfig_isGlobalInit

# pytest case collecting will import some module before monkey patch, so reload
from importlib import reload
import sonic_ax_impl.mibs
reload(sonic_ax_impl.mibs)
