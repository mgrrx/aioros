import logging
import signal
from contextlib import asynccontextmanager
from functools import partial
from typing import AsyncIterator, Optional

import anyio

from .._utils._logging import ColoredFormatter, init_logging
from .._utils._resolve import get_local_address
from .._utils._sockets import create_tcp_listener
from ..xmlrpc import handle as handle_xmlrpc
from ._api import MasterApiHandle
from ._master import Master

logger = logging.getLogger(__name__)


@asynccontextmanager
async def init_master(
    xmlrpc_port: int = 0,
    local_address: Optional[str] = None,
) -> AsyncIterator[Master]:
    local_address = local_address or get_local_address()
    async with anyio.create_task_group() as task_group:
        xmlrpc_listener, xmlrpc_uri = await create_tcp_listener(
            local_address, xmlrpc_port, "http://{local_host}:{local_port}/"
        )
        logger.debug("Starting master on %s", xmlrpc_uri)
        master = Master(xmlrpc_uri, task_group)
        task_group.start_soon(
            xmlrpc_listener.serve,
            partial(
                handle_xmlrpc,
                MasterApiHandle(master),
            ),
        )

        yield master

        # Main terminated, clean up
        task_group.cancel_scope.cancel()

        await master.aclose()


async def run(
    xmlrpc_port: int = 0,
    local_address: Optional[str] = None,
    debug: bool = False,
) -> None:
    init_logging(
        ColoredFormatter(
            "%(asctime)s master[%(process)d] %(message)s",
            "%b %d %H:%M:%S",
        ),
        logging.DEBUG if debug else logging.INFO,
    )
    async with init_master(xmlrpc_port, local_address):
        async with anyio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
            async for signum in signals:
                if signum == signal.SIGINT:
                    print("Ctrl+C pressed!")
                else:
                    print("Terminated!")
                break
