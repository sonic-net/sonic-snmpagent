# MONKEY PATCH!!!
import json
import os

import unittest.mock
import mockredis
import swsssdk.interface
from swsssdk.interface import redis
from swsssdk import SonicV2Connector
from swsssdk import SonicDBConfig
import importlib

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

def init_SonicV2Connector(self, use_unix_socket_path=False, namespace=None, **kwargs):
    self.namespace = namespace
    self.use_unix_socket_path = use_unix_socket_path
    for db_name in SonicDBConfig.get_dblist(self.namespace):
        setattr(self, db_name, db_name)
    ns_list = SonicDBConfig.get_ns_list()
    # In case of multiple namespaces, namespace string passed to
    # SonicV2Connector will specify the namespace or can be empty.
    # Empty namespace represents global or host namespace.
    if len(ns_list) > 1 and namespace == "":
        kwargs['namespace'] = "global_db"
    else:
        kwargs['namespace'] = namespace
    self.dbintf = swsssdk.interface.DBInterface(**kwargs)

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
        db = kwargs.pop('db')
        # Namespace is added in kwargs specifically for unit-test
        # to identify the file path to load the db json files.
        namespace = kwargs.pop('namespace')
        if db == 0:
            fname = 'appl_db.json'
        elif db == 1:
            fname = 'asic_db.json'
        elif db == 2:
            fname = 'counters_db.json'
        elif db == 4:
            fname = 'config_db.json'
        elif db == 6:
            fname = 'state_db.json'
        elif db == 7:
            fname = 'snmp_overlay_db.json'
        else:
            raise ValueError("Invalid db")
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


swsssdk.interface.DBInterface._subscribe_keyspace_notification = _subscribe_keyspace_notification
mockredis.MockRedis.config_set = config_set
redis.StrictRedis = SwssSyncClient
swsssdk.dbconnector.SonicV2Connector.__init__ = init_SonicV2Connector
