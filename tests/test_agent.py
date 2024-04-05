import asyncio
import os
import sys
import time
from unittest import TestCase

modules_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(modules_path, 'src'))

import ax_interface

class SonicMIB(metaclass=ax_interface.mib.MIBMeta):
    """
    Test
    """

class TestAgentLoop(TestCase):

    async def delayed_shutdown(self, agent):
        await asyncio.sleep(5)
        await agent.shutdown()

    def test_agent_loop(self):
        event_loop = asyncio.get_event_loop()
        agent = ax_interface.Agent(SonicMIB, 5, event_loop)
        event_loop.create_task(self.delayed_shutdown(agent))
        event_loop.run_until_complete(agent.run_in_event_loop())
