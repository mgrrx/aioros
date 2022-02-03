from functools import partial
from ipaddress import IPv4Address, IPv6Address
from socket import AddressFamily  # pylint: disable=no-name-in-module
from typing import (
    Any,
    Awaitable,
    Callable,
    List,
    Literal,
    Tuple,
    TypedDict,
    Union,
    cast,
)
from wsgiref.handlers import format_date_time

import h11
from anyio import BrokenResourceError, EndOfStream, create_tcp_listener, move_on_after
from anyio.abc import SocketStream, TaskGroup

from ._protocol._common import XmlRpcTypes
from ._protocol._server import build_xml, format_error, format_success, parse_request

AnyIPAddressFamily = Literal[
    AddressFamily.AF_UNSPEC, AddressFamily.AF_INET, AddressFamily.AF_INET6
]
Event = Union[
    h11.Request,
    h11.InformationalResponse,
    h11.Response,
    h11.Data,
    h11.EndOfMessage,
    h11.ConnectionClosed,
]


TIMEOUT = 10
MAX_RECV = 2 ** 16


class MultiCall(TypedDict):
    methodName: str
    params: List[Any]


class ServerHandle:
    async def multicall(self, call_list: List[MultiCall]) -> Any:
        results = []
        for call in call_list:
            method = lookup_method(self, call["methodName"])
            results.append(await method(*call["params"]))

        return results


class ClientWrapper:
    def __init__(self, stream: SocketStream) -> None:
        self.stream = stream
        self.conn = h11.Connection(h11.SERVER)

    async def send(self, event: Event) -> None:
        assert not isinstance(event, h11.ConnectionClosed)
        data = self.conn.send(event)
        await self.stream.send(data)

    async def _read_from_peer(self) -> None:
        if self.conn.they_are_waiting_for_100_continue:
            go_ahead = h11.InformationalResponse(
                status_code=100, headers=self.basic_headers()
            )
            await self.send(go_ahead)
        try:
            data = await self.stream.receive(MAX_RECV)
        except (ConnectionError, EndOfStream):
            data = b""
        self.conn.receive_data(data)

    async def next_event(self) -> Event:
        while True:
            event = self.conn.next_event()
            if event is h11.NEED_DATA:
                await self._read_from_peer()
                continue
            return event

    async def shutdown(self) -> None:
        try:
            await self.stream.send_eof()
        except (BrokenResourceError, EndOfStream):
            return
        with move_on_after(TIMEOUT):
            try:
                while True:
                    got = await self.stream.receive(MAX_RECV)
                    if not got:
                        break
            except (BrokenResourceError, EndOfStream):
                pass
            finally:
                await self.stream.aclose()

    def basic_headers(self) -> List[Tuple[bytes, bytes]]:
        return [
            (b"Date", format_date_time(None).encode("ascii")),
            (
                b"Server",
                f"aioros.xmlrpc/{h11.__version__} {h11.PRODUCT_ID}".encode("ascii"),
            ),
            (b"Content-Type", b"text/xml"),
        ]


async def handle(server_handle: ServerHandle, stream: SocketStream) -> None:
    wrapper = ClientWrapper(stream)
    while True:
        try:
            event = await wrapper.next_event()
        except BrokenResourceError:
            await wrapper.shutdown()
            return
        if isinstance(event, h11.Request):
            await handle_request(server_handle, wrapper, event)

        if wrapper.conn.our_state is h11.MUST_CLOSE:
            await wrapper.shutdown()
            return

        try:
            wrapper.conn.start_next_cycle()
        except h11.ProtocolError:
            await wrapper.shutdown()
            return


def lookup_method(
    server_handle: ServerHandle, method_name: str
) -> Callable[..., Awaitable[XmlRpcTypes]]:
    if method_name.startswith("_"):
        raise ValueError("Access to protected method is not allowed.")
    return getattr(server_handle, method_name)


async def handle_request(
    server_handle: ServerHandle,
    wrapper: ClientWrapper,
    request: h11.Request,
) -> None:
    body = b""
    while True:
        event = await wrapper.next_event()
        if isinstance(event, h11.EndOfMessage):
            break
        body += cast(h11.Data, event).data
    method_name, args = parse_request(body, dict(request.headers))
    try:
        method = lookup_method(server_handle, method_name)
        result = await method(*args)
        root = format_success(result)
        status_code = 200
    except Exception as exc:
        root = format_error(exc)
        status_code = 500

    data = build_xml(root)
    headers = wrapper.basic_headers()
    headers.append((b"Content-length", str(len(data)).encode()))
    response = h11.Response(status_code=status_code, headers=headers)
    await wrapper.send(response)
    await wrapper.send(h11.Data(data=data))
    await wrapper.send(h11.EndOfMessage())


async def start_server(
    server_handle: ServerHandle,
    *,
    local_host: Union[str, IPv4Address, IPv6Address] = None,
    local_port: int = 0,
    family: AnyIPAddressFamily = AddressFamily.AF_UNSPEC,
    backlog: int = 65536,
    reuse_port: bool = False,
    task_group: TaskGroup = None,
) -> None:
    listener = await create_tcp_listener(
        local_host=local_host,
        local_port=local_port,
        family=family,
        backlog=backlog,
        reuse_port=reuse_port,
    )
    await listener.serve(partial(handle, server_handle), task_group=task_group)
