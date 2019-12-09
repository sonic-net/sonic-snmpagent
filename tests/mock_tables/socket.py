import os
import sys
from collections import namedtuple
import unittest
from unittest import TestCase, mock
from unittest.mock import patch, mock_open, MagicMock

INPUT_DIR = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(modules_path, 'src'))

import socket

# Backup original class
_socket_class = socket.socket
_socket_gethostname = socket.gethostname

# Monkey patch
def MockGetHostname():
    return 'str-msn2700-05'

class MockSocket(_socket_class):
    def __init__(self, *args, **kwargs):
        super(MockSocket, self).__init__(*args, **kwargs)
        self._string_sent = b''
        self.prompt_hostname = MockGetHostname().encode()

    def connect(self, *args, **kwargs):
        pass

    def send(self, *args, **kwargs):
        string = args[0]
        self._string_sent = string
        pass

    def recv(self, *args, **kwargs):
        try:
            if self._string_sent == b'':
                return b'\r\nHello, this is Quagga (version 0.99.24.1).\r\nCopyright 1996-2005 Kunihiro Ishiguro, et al.\r\n\r\n\r\nUser Access Verification\r\n\r\n\xff\xfb\x01\xff\xfb\x03\xff\xfe"\xff\xfd\x1fPassword: '
            if self._string_sent == b'zebra\n':
                return self.prompt_hostname
            if b'show ip bgp summary\n' in self._string_sent:
                filename = INPUT_DIR + '/bgpsummary_ipv4.txt'
            elif b'show ipv6 bgp summary\n' in self._string_sent:
                filename = INPUT_DIR + '/bgpsummary_ipv6.txt'
            elif b'\n' in self._string_sent:
                return self.prompt_hostname
            else:
                return None

            with open(filename, 'rb') as f:
                ret = f.read()
            return ret + self.prompt_hostname
        finally:
            self._string_sent = b''

# Replace the function with mocked one
socket.socket = MockSocket
socket.gethostname = MockGetHostname

