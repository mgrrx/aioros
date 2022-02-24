import math
from dataclasses import dataclass
from itertools import count
from typing import Generic, Optional, Set, Type

import anyio
from anyio.abc import SocketStream
from anyio.streams.memory import MemoryObjectSendStream

from ... import abc
from .._api import MasterApiClient
from ._protocol import encode_header, serialize
from ._utils import check_md5sum, require_fields


@dataclass(eq=False)
class ConnectedSubscriber(Generic[abc.MessageT]):
    protocol: str
    node_name: str
    stream: MemoryObjectSendStream[bytes]


class Publication(abc.Publication[abc.MessageT]):
    def __init__(
        self,
        topic_name: str,
        topic_type: Type[abc.MessageT],
        master: MasterApiClient,
        node_name: str,
    ):
        self._topic_name = topic_name
        self._topic_type = topic_type
        self._master = master
        self._node_name = node_name
        self._instances = 0
        self._seq = count(1)
        self._subscribers: Set[ConnectedSubscriber[abc.MessageT]] = set()
        self._condition = anyio.Condition()

    def clone(self) -> "abc.Publication[abc.MessageT]":
        return self

    async def __aenter__(self) -> "Publication[abc.MessageT]":
        # TODO handle cancellation properly
        # TODO mutex
        if self._instances == 0:
            self._instances = 1
            await self._master.register_publisher(
                self.topic_name, self.topic_type._type
            )
        else:
            self._instances += 1
        return self

    async def aclose(self) -> None:
        # TODO mutex
        if self._instances == 1:
            self._instances -= 1
            with anyio.CancelScope(shield=True), anyio.move_on_after(1):
                await self._master.unregister_publisher(self.topic_name)

            for subscriber in self._subscribers:
                await subscriber.stream.aclose()
            self._subscribers.clear()

    async def wait_for_peers(self) -> None:
        while True:
            if self._subscribers:
                return
            async with self._condition:
                await self._condition.wait()

    @property
    def topic_type(self) -> Type[abc.MessageT]:
        return self._topic_type

    @property
    def topic_name(self) -> str:
        return self._topic_name

    @property
    def header(self) -> abc.Header:
        return dict(
            callerid=self._node_name,
            latching="0",
            md5sum=getattr(self.topic_type, "_md5sum"),
            message_definition=getattr(self.topic_type, "_full_text"),
            topic=self.topic_name,
            type=getattr(self.topic_type, "_type"),
        )

    def _message_serialization_needed(self) -> bool:
        return bool(self._subscribers)

    async def publish(self, message: abc.MessageT) -> None:
        if not self._message_serialization_needed():
            return
        if getattr(message.__class__, "_has_header", False):
            if message.header.seq is None:
                message.header.seq = next(self._seq)
        data = await anyio.to_thread.run_sync(serialize, message)
        self._internal_publish(data)

    def _internal_publish(self, data: bytes) -> None:
        for subscriber in self._subscribers:
            subscriber.stream.send_nowait(data)

    async def _on_new_subscriber(
        self,
        subscriber: ConnectedSubscriber[abc.MessageT],
    ) -> None:
        async with self._condition:
            self._condition.notify_all()

    async def handle_tcpros(
        self,
        protocol: str,
        header: abc.Header,
        client: SocketStream,
    ) -> None:
        """Handle topic subscription from external. We are publisher, client is
        subscriber."""
        require_fields(header, "topic", "md5sum", "callerid")

        check_md5sum(header, getattr(self.topic_type, "_md5sum"))

        await client.send(encode_header(self.header))

        # TODO fix capacity
        send_stream, receive_stream = anyio.create_memory_object_stream(math.inf, bytes)

        async with receive_stream:
            subscriber = ConnectedSubscriber(
                protocol,
                header["callerid"],
                send_stream,
            )
            self._subscribers.add(subscriber)
            await self._on_new_subscriber(subscriber)
            async for data in receive_stream:
                try:
                    await client.send(data)
                except anyio.BrokenResourceError:
                    break
            self._subscribers.discard(subscriber)


class LatchedPublication(Publication):
    def __init__(
        self,
        topic_name: str,
        topic_type: Type[abc.MessageT],
        master: MasterApiClient,
        node_name: str,
    ):
        super().__init__(topic_name, topic_type, master, node_name)
        self._latch: Optional[bytes] = None

    def _message_serialization_needed(self) -> bool:
        return True

    @property
    def header(self) -> abc.Header:
        return dict(super().header, latching="1")

    def _internal_publish(self, data: bytes) -> None:
        self._latch = data
        super()._internal_publish(data)

    async def _on_new_subscriber(
        self,
        subscriber: ConnectedSubscriber[abc.MessageT],
    ) -> None:
        await super()._on_new_subscriber(subscriber)
        if self._latch is not None:
            await subscriber.stream.send(self._latch)
