import socket

class PerseverantSocket:
    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, fileno=None, address_tuple=None, *args, **kwargs):
        self._connected = False
        self.address_tuple = address_tuple
        self.family = family
        self.type = type
        self.sock = socket.socket(family=self.family, type=self.type, proto=proto, fileno=fileno, *args, **kwargs)
        self.sock.settimeout(10)

    @property
    def connected(self):
        return self._connected

    def connect(self, address_tuple):
        self.address_tuple = address_tuple
        self.sock.connect(self.address_tuple)

    def reconnect(self):
        assert self.address_tuple is not None
        self.sock.connect(self.address_tuple)
        self._connected = True

    def close(self):
        self._connected = False
        self.sock.close()
        self.sock = socket.socket(self.family, self.type)

    ## TODO: override __getattr__ to implement auto function call forwarding if not implemented
    def send(self, *args, **kwargs):
        return self.sock.send(*args, **kwargs)

    def recv(self, *args, **kwargs):
        return self.sock.recv(*args, **kwargs)
