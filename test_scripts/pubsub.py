#!/usr/bin/env python3

import logging
from itertools import count

import anyio
from std_msgs.msg import String

import aioros
from aioros._node._logging import init_logging

logger = logging.getLogger("aioros")


async def main() -> None:
    init_logging()
    async with anyio.create_task_group() as task_group:
        task_group.start_soon(pub)
        task_group.start_soon(sub)
        await anyio.sleep_forever()


async def pub() -> None:
    async with aioros.init_node("test_publisher", configure_logging=False):
        async with aioros.create_publication("/foo", String, latched=True) as publisher:
            counter = count()
            while aioros.is_running():
                msg = String(f"Message {next(counter)}")
                logger.info("Publish %s", msg)
                await publisher.publish(msg)
                await anyio.sleep(1.0)


async def sub() -> None:
    async with aioros.init_node("test_subscriber", configure_logging=False):
        async with aioros.create_subscription("/foo", String) as subscription:
            async for msg in subscription:
                logger.info("Received %s", msg)


if __name__ == "__main__":
    anyio.run(main)
