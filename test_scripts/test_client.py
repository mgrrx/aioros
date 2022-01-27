#!/usr/bin/env python3

import logging

import anyio
from std_srvs.srv import SetBool, SetBoolRequest

import aioros

logger = logging.getLogger("aioros")


async def main() -> None:
    async with aioros.init_node("set_bool_client"):
        async with aioros.create_client(
            "/set_bool", SetBool, persistent=True
        ) as client:
            request = SetBoolRequest(True)
            while True:
                result = await client.call(request)
                request.data = not request.data

                logger.info("Result: %s", result)
                await anyio.sleep(1)


if __name__ == "__main__":
    anyio.run(main)
