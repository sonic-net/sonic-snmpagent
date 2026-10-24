"""
Agent-X implementation using Async-IO. Based on:
https://docs.python.org/3/library/asyncio-protocol.html#register-an-open-socket-to-wait-for-data-using-a-protocol
and
https://github.com/rayed/pyagentx
"""
import asyncio
import logging
import re

from . import logger, constants
from .protocol import AgentX


class SocketManager:
    # TODO: parameterize
    SOCKET_CONNECT_TIMEOUT = 1  # seconds
    TRY_RETRY_INTERVAL = 3  # seconds
    RETRY_ERROR_THRESHOLD = 10  # seconds

    def __init__(self, mib_table, run_event, loop):

        self.mib_table = mib_table
        self.run_event = run_event
        self.loop = loop

        self.transport = self.ax_socket = None

        self.ax_socket_path = constants.AGENTX_SOCKET_PATH

        # The following code reads the snmp config file to see if the Agentx Socket path has been redefined
        # from the default RFC value '/var/agentx/master'. We do not implement reading the SNMP daemon's
        # command line to check if it has been redefined there, this should be an effort for the future
        # perhaps via a psutil().cmdline() call

        # open the snmpd config file and search for a agentx socket redefinition. Exceptions will be raised
        # if the constants.SNMPD_CONFIG_FILE or the file in itself do not exist
        pattern = re.compile(r"^agentxsocket\s+(.*)$", re.IGNORECASE)
        try :
            with open(constants.SNMPD_CONFIG_FILE,'rt') as config_file:
                for line in config_file:
                    match = pattern.search(line)
                    if match:
                        self.ax_socket_path = match.group(1)
        except:
            logger.warning("SNMPD config file not found, using default agentx file socket")

        self.parse_socket()
        logger.info("Using agentx socket type " + self.ax_socket_type + " with path " + self.ax_socket_path)

    def parse_socket(self):
        # Determine wether the socket method is supported
        # extract the type and connection data

        # lets get the unsuported methods out of the way first
        unsuported_list = ['ssh', 'dtlsudp', 'ipx', 'aal5pvc', 'udp']
        for method in unsuported_list:
            if self.ax_socket_path.startswith(method):
                # This is not a supported method
                self.unsuported_method()
                return
        # Now the stuff that we are interested in
        # First case: we have a simple number then its a local UDP port
        # udp has been added to the unsuported_list because asyncio throws a not implemented error with udp
        # we leave the code here for when it will be implemented
        if self.ax_socket_path.isdigit():
            self.unsuported_method()
            return
        # if we have an explicit udp socket 
        if self.ax_socket_path.startswith('udp'):
            self.unsuported_method()
            return
        # if we have an explicit tcp socket
        if self.ax_socket_path.startswith('tcp'):
            self.ax_socket_type = 'tcp'
            self.host, self.port = self.get_ip_port(self.ax_socket_path.split(':',1)[1])
            return
        # if we have an explicit unix domain socket
        if self.ax_socket_path.startswith('unix'):
            self.ax_socket_type = 'unix'
            self.ax_socket_path = self.ax_socket_path.split(':',1)[1]
            return
        # unix is not compulsory so you can also have a plain path
        if '/' in self.ax_socket_path:
            self.ax_socket_type = 'unix'
            return
        # if at this point we haven't matched anything yet its that we are most likely left with a host:port pair so UDP
        if ':' in self.ax_socket_path:
            self.unsuported_method()
            return
        # we should never get here but if we do it's that there is garbage so lets revert to the default of snmp
        logger.warning("There's something weird with " + self.ax_socket_path + " , using default agentx file socket")
        self.ax_socket_path = constants.AGENTX_SOCKET_PATH
        self.ax_socket_type = 'unix'
        return

    def get_ip_port(self,address):
        # determine if we only have a port or a ip:port tuple, must work with IPv6
        address_list = address.split(':')
        if len(address_list) == 1:
            # we only have a port
            return 'localhost', address_list[0]
        else:
            # if we get here then either: we've got garbage, an ip:port or ipv6:port or hostname:port
            # an IP or IPv6 only is illegal
            address_list = address.rsplit(':',1)
            return address_list[0], address_list[1]

    def unsuported_method(self):
        logger.warning("Socket type " + self.ax_socket_path + " not supported, using default agentx file socket")
        self.ax_socket_path = constants.AGENTX_SOCKET_PATH
        self.ax_socket_type = 'unix'

    async def connection_loop(self):
        """
        Try/Retry connection coroutine to attach the socket.
        """
        failed_connections = 0

        logger.info("Connection loop starting...")
        # keep the connection alive while the agent is running
        while self.run_event.is_set():
            try:
                logger.info("Attempting AgentX socket bind...".format())

                # Open the connection to the Agentx socket, we check the socket string to 
                # lets open our socket according to its detected type
                if self.ax_socket_type == 'unix':
                    connection_routine = self.loop.create_unix_connection(
                        protocol_factory=lambda: AgentX(self.mib_table, self.loop),
                        path=self.ax_socket_path,
                        sock=self.ax_socket)
                elif self.ax_socket_type == 'udp':
                    # we should not land here as the udp method is in the unsuported list
                    # testing shows that async_io throws a NotImplementedError when udp is used
                    # the code remains for when asyncio will implement it
                    connection_routine = self.loop.create_datagram_endpoint(
                        protocol_factory=lambda: AgentX(self.mib_table, self.loop),
                        remote_addr=(self.host,self.port),
                        sock=self.ax_socket)
                elif self.ax_socket_type == 'tcp':
                    connection_routine = self.loop.create_connection(
                        protocol_factory=lambda: AgentX(self.mib_table, self.loop),
                        host=self.host,
                        port=self.port,
                        sock=self.ax_socket)

                # Initiate the socket connection
                self.transport, protocol = await connection_routine
                logger.info("AgentX socket connection established. Initiating opening handshake...")

                # prime a callback to execute the Opening handshake
                self.loop.call_later(1, protocol.opening_handshake)
                # connection established, wait until the transport closes (or loses connection)
                await protocol.closed.wait()
            except OSError:
                # We couldn't open the socket.
                failed_connections += 1
                # adjust the log level based on how long we've been waiting.
                log_level = logging.WARNING if failed_connections <= SocketManager.RETRY_ERROR_THRESHOLD \
                    else logging.ERROR

                logger.log(log_level, "Socket bind failed. \"Is 'snmpd' running?\". Retrying in {} seconds..." \
                           .format(SocketManager.TRY_RETRY_INTERVAL))
                # try again soon
                await asyncio.sleep(SocketManager.TRY_RETRY_INTERVAL)

        logger.info("Run disabled. Connection loop stopping...")

    def close(self):
        if self.transport is not None:
            # close the transport (it will call connection_lost() and stop the attach_socket routine)
            self.transport.close()
