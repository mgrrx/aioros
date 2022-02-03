#!/usr/bin/env python3

import logging

import anyio
from std_msgs.msg import String

import aioros

logger = logging.getLogger("aioros")


async def main() -> None:
    async with aioros.init_node("test_subscriber"):
        async with aioros.create_subscription("/chatter", String) as subscription:
            async for msg in subscription:
                logger.info("Received %s", msg)


if __name__ == "__main__":
    anyio.run(main)
