import os
import csv
import unittest
from unittest import TestCase, mock
from unittest.mock import patch, mock_open, MagicMock

INPUT_DIR = os.path.dirname(os.path.abspath(__file__))

import python_arptable

# Backup original function
_get_arp_table = getattr(python_arptable, 'get_arp_table')
# Mock arp table for host arp information on mulit-asic plaform.
# In multi-asic platform, the namespace ARP inforamtion is retrieved
# from NEIGH_TABLE from namespace APP_DBs. Host arp information is
# retrieved from kernel.
arp_filename = '/host_arp.txt'

# Monkey patch
def get_arp_table():
    with open(INPUT_DIR + arp_filename) as farp:
        file_content = mock_open(read_data = farp.read())
        file_content.return_value.__iter__ = lambda self : iter(self.readline, '')
        # file_content = MagicMock(name = 'open', spec = open)
        # file_content.return_value = iter(farp.readlines())
        with patch('builtins.open', file_content):
            return _get_arp_table()

# Replace the function with mocked one
python_arptable.get_arp_table = get_arp_table
