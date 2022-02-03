#!/usr/bin/env python3

import logging
from itertools import count

import anyio
from std_msgs.msg import String

import aioros

logger = logging.getLogger("aioros")


async def main() -> None:
    async with aioros.init_node("test_publisher"):
        async with aioros.create_publication("/chatter", String) as publisher:
            counter = count()
            while aioros.is_running():
                msg = String(f"Message {next(counter)}")
                publisher.publish_soon(msg, copy=False)
                await anyio.sleep(0.00001)


if __name__ == "__main__":
    anyio.run(main)
