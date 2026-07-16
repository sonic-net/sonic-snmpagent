import asyncio
import time
from unittest import TestCase


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
        agent = ax_interface.Agent(SonicMIB, False, 5, event_loop)
        event_loop.create_task(self.delayed_shutdown(agent))
        event_loop.run_until_complete(agent.run_in_event_loop())
