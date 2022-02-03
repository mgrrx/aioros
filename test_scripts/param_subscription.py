#!/usr/bin/env python3

import logging

import anyio

import aioros

logger = logging.getLogger("aioros")


async def main() -> None:
    async with aioros.init_node("test_param_subscriber"):
        print(await aioros.get_param_cached("/foo"))
        await anyio.sleep_forever()


if __name__ == "__main__":
    anyio.run(main)
