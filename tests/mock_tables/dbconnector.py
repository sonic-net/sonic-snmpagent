# MONKEY PATCH!!!
import json
import os
import sys

import mockredis
import redis
from swsssdk import SonicV2Connector
from swsssdk import SonicDBConfig
from swsssdk.interface import DBInterface
from swsscommon import swsscommon
from swsscommon.swsscommon import Table, DBConnector
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


_old_connect_SonicV2Connector = SonicV2Connector.connect


def connect_SonicV2Connector(self, db_name, retry_on=True):
    ns_list = SonicDBConfig.get_ns_list()
    # In case of multiple namespaces, namespace string passed to
    # SonicV2Connector will specify the namespace or can be empty.
    # Empty namespace represents global or host namespace.
    if len(ns_list) > 1 and (self.namespace == "" or self.namespace == None):
        self.dbintf.redis_kwargs['namespace'] = "global_db"
    else:
        self.dbintf.redis_kwargs['namespace'] = self.namespace
    # Mock DB filename for unit-test
    self.dbintf.redis_kwargs['db_name'] = db_name
    self.dbintf.redis_kwargs['decode_responses'] = True
    _old_connect_SonicV2Connector(self, db_name, retry_on)


def _subscribe_keyspace_notification(self, db_name):
    pass

#FIXME: Mock DBConnector.__init__ and DBConnector.Table
_old___init__DBConnector = DBConnector.__init__

def __init__DBConnector(self, *args):
    # print("### __init__DBConnector self: {}, args: {}".format(self, args))
    pass
    # _old___init__DBConnector(self, *args)
    # mock_appdb_conn = {"mock_conn": "appl_db"}
    # return mock_appdb_conn

def Table_DBConnector(self, *args):
    # print("### Table_DBConnector self: {}, args: {}".format(self, args))
    # _old___init__DBConnector(self, *args)
    # fvs = swsscommon.FieldValuePairs([("admin_status", "up"), ("mtu", "9100")])
    mock_kfvt = swsscommon.TableMap({"11.0.0.11": [("nexthop", "111.0.0.111"),("ifname", "Ethernet11")], "22.0.0.22": [("nexthop", "222.0.0.222"),("ifname", "Ethernet22")]})

    return mock_kfvt

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
SonicV2Connector.connect = connect_SonicV2Connector
swsscommon.DBConnector = __init__DBConnector
#FIXME: Mock DBConnector.__init__ and DBConnector.Table
# swsscommon.Table = Table_DBConnector
swsscommon.SonicV2Connector = SonicV2Connector
swsscommon.SonicDBConfig = SonicDBConfig
swsscommon.SonicDBConfig.isGlobalInit = mock_SonicDBConfig_isGlobalInit

# pytest case collecting will import some module before monkey patch, so reload
from importlib import reload
import sonic_ax_impl.mibs
reload(sonic_ax_impl.mibs)
