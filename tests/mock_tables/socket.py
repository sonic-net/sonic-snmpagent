import os
import sys
from collections import namedtuple
import unittest
from unittest import TestCase, mock
from unittest.mock import patch, mock_open, MagicMock
from enum import Enum

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

class State(Enum):
    CLOSED = 0
    BANNER = 1
    INTERACTIVE = 2

class MockSocket(_socket_class):
    def __init__(self, *args, **kwargs):
        super(MockSocket, self).__init__(*args, **kwargs)
        self.prompt_hostname = (MockGetHostname() + '> ').encode()
        self.state = State.CLOSED

    def connect(self, *args, **kwargs):
        self.state = State.BANNER
        self._string_sent = b''

    def send(self, *args, **kwargs):
        string = args[0]
        self._string_sent = string
        pass

    def recv(self, *args, **kwargs):
        if self.state == State.CLOSED:
            raise OSError("Transport endpoint is not connected")

        if self.state == State.BANNER:
            self.state = State.INTERACTIVE
            return b'\r\nHello, this is Quagga (version 0.99.24.1).\r\nCopyright 1996-2005 Kunihiro Ishiguro, et al.\r\n\r\n\r\nUser Access Verification\r\n\r\n\xff\xfb\x01\xff\xfb\x03\xff\xfe"\xff\xfd\x1fPassword: '

        if not self._string_sent or b'\n' not in self._string_sent:
            raise socket.timeout

        try:
            if self._string_sent == b'zebra\n':
                return self.prompt_hostname
            elif b'show ip bgp summary\n' in self._string_sent:
                filename = INPUT_DIR + '/bgpsummary_ipv4.txt'
            elif b'show ipv6 bgp summary\n' in self._string_sent:
                filename = INPUT_DIR + '/bgpsummary_ipv6.txt'
            else:
                return self.prompt_hostname

            with open(filename, 'rb') as f:
                ret = f.read()
            return ret + b'\r\n' + self.prompt_hostname
        finally:
            self._string_sent = b''

# Replace the function with mocked one
socket.socket = MockSocket
socket.gethostname = MockGetHostname

