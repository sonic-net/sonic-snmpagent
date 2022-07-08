import os
import json

import tests.mock_tables.dbconnector
from sonic_py_common import multi_asic
from swsssdk import SonicDBConfig


INPUT_DIR = os.path.dirname(os.path.abspath(__file__))
int_port_channel = ['PortChannel01', 'PortChannel02', 'PortChannel03', 'PortChannel04']

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
        return True if port_channel in int_port_channel else False

def mock_get_port_table_for_asic(namespace=None):
    if namespace is not None:
        fname = os.path.join(INPUT_DIR, namespace, 'config_db.json')
    else:
        fname = os.path.join(INPUT_DIR, 'config_db.json')
    port_table = {}
    db = {}
    with open(fname) as f:
        db = json.load(f)
    for k in db:
        if 'PORT_TABLE' in k:
            new_key = k[len('PORT_TABLE:'):]
            port_table[new_key] = db[k]
    return port_table

multi_asic.get_num_asics = mock_get_num_asics
multi_asic.is_multi_asic = mock_is_multi_asic
multi_asic.get_all_namespaces = mock_get_all_namespaces
multi_asic.is_port_channel_internal = mock_is_port_channel_internal
multi_asic.get_port_table_for_asic = mock_get_port_table_for_asic
