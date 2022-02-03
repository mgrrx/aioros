#!/usr/bin/env python3

import logging

import anyio

import aioros
from aioros._node._auto_msg import AutoMessage

logger = logging.getLogger("aioros")


async def main() -> None:
    async with aioros.init_node("test_subscriber"):
        async with aioros.create_subscription("/foo", AutoMessage) as subscription:
            async for msg in subscription:
                logger.info("Received %s", msg)


if __name__ == "__main__":
    anyio.run(main)
