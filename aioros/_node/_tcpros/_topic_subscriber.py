import logging
import math
from dataclasses import dataclass, field
from itertools import count
from typing import Any, Dict, Generic, Iterator, List, Optional, Set, Tuple, Type, cast

import anyio
import httpx
from anyio.abc import CancelScope, SocketStream, TaskGroup
from anyio.streams.buffered import BufferedByteReceiveStream
from anyio.streams.memory import MemoryObjectSendStream

from ... import abc
from ..._utils._resolve import get_local_address
from .._api import MasterApiClient, NodeApiClient
from ._protocol import encode_header, read_data, read_header

logger = logging.getLogger(__name__)


@dataclass(eq=False)
class ConnectedPublisher:
    id: int
    xmlrpc_uri: str
    cancel_scope: CancelScope = field(default_factory=CancelScope)
    connected: bool = False
    protocol: str = ""
    connection_parameter: List[str] = field(default_factory=list)


@dataclass(eq=False)
class SubscriptionManager(Generic[abc.MessageT]):
    task_group: TaskGroup
    topic_name: str
    topic_type: Type[abc.MessageT]
    master: MasterApiClient
    node_name: str
    subscriptions: Set[MemoryObjectSendStream[abc.MessageT]] = field(
        init=False, default_factory=set
    )
    connected_publishers: Dict[str, ConnectedPublisher] = field(
        init=False, default_factory=dict
    )
    lock: anyio.Lock = field(init=False, default_factory=anyio.Lock)
    registered: bool = field(init=False, default=False)
    id_generator: Iterator[int] = field(init=False, default_factory=count)
    condition: anyio.Condition = field(init=False, default_factory=anyio.Condition)

    @property
    def header(self) -> Dict[str, str]:
        return dict(
            topic=self.topic_name,
            message_definition=getattr(self.topic_type, "_full_text"),
            tcp_nodelay="1",
            md5sum=getattr(self.topic_type, "_md5sum"),
            type=getattr(self.topic_type, "_type"),
            callerid=self.node_name,
        )

    async def register(
        self,
        send_stream: MemoryObjectSendStream[abc.MessageT],
    ) -> None:
        async with self.lock:
            if not self.registered:
                with anyio.CancelScope(shield=True), anyio.move_on_after(1):
                    publisher_uris = await self.master.register_subscriber(
                        self.topic_name, getattr(self.topic_type, "_type")
                    )
                self.registered = True
                self.update_publishers(publisher_uris)
            self.subscriptions.add(send_stream)

    async def unregister(
        self,
        send_stream: MemoryObjectSendStream[abc.MessageT],
    ) -> None:
        async with self.lock:
            self.subscriptions.discard(send_stream)
            if not self.subscriptions:
                try:
                    await self.master.unregister_subscriber(self.topic_name)
                except httpx.ConnectError:
                    pass
                self.registered = False
                self.update_publishers([])

    def update_publishers(self, publisher_uris: List[str]) -> None:
        current_publishers = set(self.connected_publishers.keys())
        new_publishers = set(publisher_uris)
        to_discard = current_publishers - new_publishers
        to_connect = new_publishers - current_publishers
        for publisher_uri in to_discard:
            self.connected_publishers.pop(publisher_uri).cancel_scope.cancel()

        for publisher_uri in to_connect:
            publisher = ConnectedPublisher(next(self.id_generator), publisher_uri)
            self.connected_publishers[publisher_uri] = publisher

            self.task_group.start_soon(self._subscribe_task, publisher)

    async def wait_for_peers(self) -> None:
        while True:
            if any(pub.connected for pub in self.connected_publishers.values()):
                return
            async with self.condition:
                await self.condition.wait()

    async def _subscribe_task(self, publisher: ConnectedPublisher) -> None:
        with publisher.cancel_scope:
            protocol, params = await self._get_publisher_connection_params(
                publisher.xmlrpc_uri, ["UDSROS", "TCPROS"]
            )
            client: Optional[SocketStream] = None

            if protocol == "UDSROS":
                if params[0] == get_local_address():
                    logger.debug("Connecting via %s", params[1])
                    client = await anyio.connect_unix(params[1])
                else:
                    # non-local connection => switch to TCPROS
                    protocol, params = await self._get_publisher_connection_params(
                        publisher.xmlrpc_uri, ["TCPROS"]
                    )

            if client is None:
                logger.debug("Connecting via %s:%s", params[0], params[1])
                client = await anyio.connect_tcp(params[0], int(params[1]))

            publisher.protocol = protocol
            publisher.connection_parameter = params

            try:
                async with client:
                    publisher.connected = True
                    async with self.condition:
                        self.condition.notify_all()
                    await client.send(encode_header(self.header))
                    buffered_client = BufferedByteReceiveStream(client)

                    header_dict = await read_header(buffered_client)
                    if "error" in header_dict:
                        # TODO proper exception
                        # raise SubscriberInitError(header_dict["error"])
                        raise RuntimeError()

                    while not publisher.cancel_scope.cancel_called:
                        msg = self.topic_type()
                        msg.deserialize(await read_data(buffered_client))
                        for stream in self.subscriptions:
                            stream.send_nowait(msg)
            except anyio.IncompleteRead:
                pass
            finally:
                self.connected_publishers.pop(publisher.xmlrpc_uri, None)

    async def _get_publisher_connection_params(
        self, publisher_uri: str, protocols: List[str]
    ) -> Tuple[str, List[Any]]:
        async with NodeApiClient(publisher_uri, self.node_name) as client:
            topic = await client.request_topic(
                self.topic_name, [[protocol] for protocol in protocols]
            )
        return cast(str, topic[0]), topic[1:]


class Subscription(abc.Subscription[abc.MessageT]):
    def __init__(
        self,
        subscription_manager: SubscriptionManager[abc.MessageT],
    ) -> None:
        self._subscription_manager = subscription_manager
        self._send_stream, self._receive_stream = anyio.create_memory_object_stream(
            math.inf, subscription_manager.topic_type
        )

    def clone(self) -> "abc.Subscription[abc.MessageT]":
        return Subscription(self._subscription_manager)

    @property
    def topic_type(self) -> Type[abc.MessageT]:
        return self._subscription_manager.topic_type

    @property
    def topic_name(self) -> str:
        return self._subscription_manager.topic_name

    async def wait_for_peers(self) -> None:
        await self._subscription_manager.wait_for_peers()

    async def __anext__(self) -> abc.MessageT:
        return await self._receive_stream.__anext__()

    async def __aenter__(self) -> "Subscription[abc.MessageT]":
        await self._subscription_manager.register(self._send_stream)
        await self._receive_stream.__aenter__()

        return self

    async def aclose(self) -> None:
        await self._receive_stream.aclose()
        with anyio.CancelScope(shield=True), anyio.move_on_after(1):
            await self._subscription_manager.unregister(self._send_stream)
