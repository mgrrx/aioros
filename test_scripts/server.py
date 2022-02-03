#!/usr/bin/env python3
import logging

import anyio
from std_srvs.srv import SetBool, SetBoolRequest, SetBoolResponse

import aioros

logger = logging.getLogger("aioros")


async def service_cb(request: SetBoolRequest) -> SetBoolResponse:
    logger.info("Handling Request %s", request)
    return SetBoolResponse(message=str(request.data), success=True)


async def main() -> None:
    async with aioros.init_node("some_server"):
        await aioros.create_server("/set_bool", SetBool, service_cb).serve()


if __name__ == "__main__":
    anyio.run(main)
