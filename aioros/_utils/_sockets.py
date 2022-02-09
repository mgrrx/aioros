from pathlib import Path
from tempfile import mkdtemp
from typing import Optional, Tuple, cast

import anyio
from anyio.abc import SocketAttribute, SocketListener


async def create_tcp_listener(
    local_host: str, local_port: int, fmt: str
) -> Tuple[SocketListener, str]:
    multi_listener = await anyio.create_tcp_listener(
        local_host=local_host, local_port=local_port
    )
    local_port = multi_listener.listeners[0].extra(SocketAttribute.local_port)
    return (
        cast(SocketListener, multi_listener.listeners[0]),
        fmt.format(local_host=local_host, local_port=local_port),
    )


async def create_unix_listener(
    local_host: str, node_name: str, path: Optional[Path], fmt: str
) -> Tuple[SocketListener, str]:
    path = path or Path(mkdtemp(), node_name[1:], "socket")

    path.parent.mkdir(parents=True, exist_ok=True)

    path.unlink(True)

    listener = await anyio.create_unix_listener(path)
    return (listener, fmt.format(local_host=local_host, path=path.absolute()))
