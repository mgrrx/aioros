#!/usr/bin/env python3

import logging

import anyio
from genpy import Duration

import aioros

logger = logging.getLogger("aioros")


async def main() -> None:
    async with aioros.init_node("test_rate"):
        async for time in aioros.every(Duration(1.0)):
            logger.info("tick %s", time.to_sec())


if __name__ == "__main__":
    anyio.run(main)
