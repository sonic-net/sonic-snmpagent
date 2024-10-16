"""
SNMP subagent entrypoint.
"""

import asyncio
import functools
import os
import signal
import sys

import ax_interface
from sonic_ax_impl.mibs import ieee802_1ab, Namespace
from . import logger
from .mibs.ietf import rfc1213, rfc2737, rfc2863, rfc3433, rfc4292, rfc4363
from .mibs.vendor import dell, cisco

# Background task update frequency ( in seconds )
DEFAULT_UPDATE_FREQUENCY = 5

event_loop = asyncio.get_event_loop()
shutdown_task = None


class SonicMIB(
    rfc1213.InterfacesMIB,
    rfc1213.IpMib,
    rfc1213.SysNameMIB,
    rfc2737.PhysicalTableMIB,
    rfc3433.PhysicalSensorTableMIB,
    rfc2863.InterfaceMIBObjects,
    rfc4363.QBridgeMIBObjects,
    rfc4292.IpCidrRouteTable,
    ieee802_1ab.LLDPLocalSystemData,
    ieee802_1ab.LLDPLocalSystemData.LLDPLocPortTable,
    ieee802_1ab.LLDPLocalSystemData.LLDPLocManAddrTable,
    ieee802_1ab.LLDPRemTable,
    ieee802_1ab.LLDPRemManAddrTable,
    dell.force10.SSeriesMIB,
    cisco.bgp4.CiscoBgp4MIB,
    cisco.ciscoPfcExtMIB.cpfcIfTable,
    cisco.ciscoPfcExtMIB.cpfcIfPriorityTable,
    cisco.ciscoSwitchQosMIB.csqIfQosGroupStatsTable,
    cisco.ciscoEntityFruControlMIB.cefcFruPowerStatusTable,
    cisco.ciscoEntitySensorMIB.CiscoPhysicalSensorThresholdMIB,
    cisco.ciscoEntitySensorMIB.CiscoPhysicalSensorValueTableMIB,
):
    """
    If SONiC was to create custom MIBEntries, they may be specified here.
    """


def shutdown(signame, agent):
    # FIXME: If the Agent dies, the background tasks will zombie.
    global event_loop, shutdown_task
    logger.info("Recieved '{}' signal, shutting down...".format(signame))
    shutdown_task = event_loop.create_task(agent.shutdown())


def main(update_frequency=None):
    global event_loop

    try:
        Namespace.init_sonic_db_config()

        # initialize handler and set update frequency (or use the default)
        agent = ax_interface.Agent(SonicMIB, update_frequency or DEFAULT_UPDATE_FREQUENCY, event_loop)

        # add "shutdown" signal handlers
        # https://docs.python.org/3.5/library/asyncio-eventloop.html#set-signal-handlers-for-sigint-and-sigterm
        for signame in ('SIGINT', 'SIGTERM'):
            event_loop.add_signal_handler(getattr(signal, signame),
                                          functools.partial(shutdown, signame, agent))

        # start the agent, wait for it to come back.
        logger.info("Starting agent with PID: {}".format(os.getpid()))
        event_loop.run_until_complete(agent.run_in_event_loop())

    except Exception:
        logger.exception("Uncaught exception in {}".format(__name__))
        sys.exit(1)
    finally:
        if shutdown_task is not None:
            # make sure shutdown has completed completely before closing the loop
            event_loop.run_until_complete(shutdown_task)

        # the agent runtime has exited, close the event loop and exit.
        event_loop.close()
        logger.info("Goodbye!")
        sys.exit(0)
