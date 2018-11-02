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
        pattern = re.compile("^agentxsocket\s+(.*)$", re.IGNORECASE)
        try :
            with open(constants.SNMPD_CONFIG_FILE,'rt') as config_file:
                for line in config_file:
                    match = pattern.search(line)
                    if match:
                        self.ax_socket_path = match.group(1)
        except:
            logger.warning("SNMPD config file not found, using default agentx file socket")

        logger.info("Using agentx socket " + self.ax_socket_path)

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
                # either open a tcp socket or a Unix domain socket
                if '/' in self.ax_socket_path:
                    # This looks like a filesystem path so lets open it as a domain socket
                    # but first lets remove 'unix' if it's in the spec
                    if self.ax_socket_path.startswith('unix'):
                        self.ax_socket_path = self.ax_socket_path.split(':')[1]
                    connection_routine = self.loop.create_unix_connection(
                        protocol_factory=lambda: AgentX(self.mib_table, self.loop),
                        path=self.ax_socket_path,
                        sock=self.ax_socket)
                elif self.ax_socket_path.startswith('tcp'):
                    # This looks like a tcp connection
                    myhost = self.ax_socket_path.split(':')[1]
                    myport = self.ax_socket_path.split(':')[2]
                    connection_routine = self.loop.create_connection(
                        protocol_factory=lambda: AgentX(self.mib_table, self.loop),
                        host=myhost,
                        port=myport,
                        sock=self.ax_socket)
                elif self.ax_socket_path.startswith('udp'):
                    # This looks like a udp connection
                    myhost = self.ax_socket_path.split(':')[1]
                    myport = self.ax_socket_path.split(':')[2]
                    connection_routine = self.loop.create_datagram_endpoint(
                        protocol_factory=lambda: AgentX(self.mib_table, self.loop),
                        host=myhost,
                        port=myport,
                        sock=self.ax_socket)
                elif self.ax_socket_path.isdigit():
                    # if the socket path is just a number then it is treated as a udp port on localhost
                    myhost = 'localhost'
                    myport = self.ax_socket_path
                    connection_routine = self.loop.create_datagram_endpoint(
                        protocol_factory=lambda: AgentX(self.mib_table, self.loop),
                        host=myhost,
                        port=myport,
                        sock=self.ax_socket)
                else:
                    # We do not support 'ssh', 'dtlsudp', 'ipx', or 'aal5pvc' (ATM lol...) methods
                    # default to the snmp default /var/agentx/master and log a warning
                    logger.warning("Socket type " + self.ax_socket_path + " not supported, using default agentx file socket")
                    connection_routine = self.loop.create_unix_connection(
                        protocol_factory=lambda: AgentX(self.mib_table, self.loop),
                        path=constants.AGENTX_SOCKET_PATH,
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
