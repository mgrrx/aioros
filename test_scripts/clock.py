#!/usr/bin/env python3

import logging

import anyio
from genpy.rostime import Time
from rosgraph_msgs.msg import Clock

import aioros

logger = logging.getLogger("aioros")


async def main() -> None:
    async with aioros.init_node("clock", initialize_time=False):
        await aioros.set_param("/use_sim_time", True)
        async with aioros.create_publication("/clock", Clock) as publisher:
            clock = Clock()
            ts = anyio.current_time()
            while aioros.is_running():
                for _ in range(10):
                    print(clock)
                    publisher.publish_soon(clock)
                    clock.clock.nsecs += 100000000
                    ts += 0.1
                    await anyio.sleep_until(ts)
                clock.clock.secs += 1
                clock.clock.nsecs = 0


if __name__ == "__main__":
    anyio.run(main)
