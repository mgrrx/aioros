from asyncio import AbstractEventLoop
from asyncio import Event
from asyncio import IncompleteReadError
from asyncio import Queue
from asyncio import open_connection
from asyncio import open_unix_connection
from asyncio import wait
from asyncio import FIRST_COMPLETED
from typing import Dict
from typing import List
from typing import Set
from typing import Tuple
from typing import Type

from genpy import Message

from ..api.node_api_client import NodeApiClient
from .protocol import Serializer
from .protocol import encode_header
from .protocol import read_data
from .protocol import read_header
from .publisher import Publisher
from .subscription import Subscription


class SubscriberInitError(Exception):
    pass


class Subscriber:

    __slots__ = ('queue', 'close')

    def __init__(self):
        self.queue: Queue = Queue()
        self.close: Event = Event()


class Topic:

    def __init__(
        self,
        loop: AbstractEventLoop,
        master_api_client,
        node_name: str,
        topic_name: str,
        msg_type: Type[Message]
    ) -> None:
        self._loop = loop
        self._master_api_client = master_api_client
        self._node_name = node_name
        self._topic_name = topic_name
        self._msg_type = msg_type
        self._connected_subscribers: Dict[str, Subscriber] = {}
        self._connected_publishers: Dict[str, Event] = {}
        self._has_connected_subscribers: Event = Event()
        self._has_connected_publishers: Event = Event()
        self._internal_subscriptions: Dict[Subscription, Queue] = {}
        self._internal_publishers: Set[Publisher] = set()
        self._latched_msgs: Dict[Publisher, bytes] = {}
        self._serializer: Serializer = Serializer()

    @property
    def name(self) -> str:
        return self._topic_name

    @property
    def type(self) -> Type[Message]:
        return self._msg_type

    @property
    def type_name(self) -> str:
        return self._msg_type._type

    @property
    def md5sum(self) -> str:
        return self._msg_type._md5sum

    @property
    def nr_connected_subscribers(self) -> int:
        return len(self._connected_subscribers)

    @property
    def nr_connected_publishers(self) -> int:
        return len(self._connected_publishers)

    async def wait_for_connected_subscribers(self) -> None:
        await self._has_connected_subscribers.wait()

    async def wait_for_connected_publishers(self) -> None:
        await self._has_connected_publishers.wait()

    @property
    def has_subscriptions(self) -> bool:
        return bool(self._internal_subscriptions)

    @property
    def has_publishers(self) -> bool:
        return bool(self._internal_publishers)

    @property
    def is_latching(self) -> bool:
        return any(pub.latch for pub in self._internal_publishers)

    def get_publisher_header(self) -> Dict[str, str]:
        return dict(
            topic=self.name,
            type=self.type_name,
            latching='1' if self.is_latching else '0',
            message_definition=self.type._full_text,
            md5sum=self.md5sum,
            callerid=self._node_name)

    async def register_publisher(
        self,
        publisher: Publisher
    ) -> None:
        if not self._internal_publishers:
            await self._master_api_client.register_publisher(
                self.name,
                self.type_name)
        self._internal_publishers.add(publisher)

    async def unregister_publisher(
        self,
        publisher: Publisher
    ) -> bool:
        self._latched_msgs.pop(publisher, None)
        self._internal_publishers.discard(publisher)
        if not self.has_publishers:
            self._close_subscriptions()
            await self._master_api_client.unregister_publisher(
                self.name,
                self.type_name)

    async def register_subscription(
        self,
        subscription: Subscription,
        queue: Queue
    ) -> None:
        if not self._internal_subscriptions:
            publishers = await self._master_api_client.register_subscriber(
                self.name,
                self.type_name)
            self.connect_to_publishers(publishers)
        self._internal_subscriptions[subscription] = queue

    async def unregister_subscription(
        self,
        subscription: Subscription
    ) -> bool:
        del self._internal_subscriptions[subscription]
        if not self.has_subscriptions:
            await self._master_api_client.unregister_subscriber(
                self.name,
                self.type_name)
            for event in self._connected_publishers.values():
                event.set()
        return self.has_subscriptions

    def _close_subscriptions(self):
        for subscriber in self._connected_subscribers.values():
            subscriber.close.set()

    def publish(
        self,
        publisher: Publisher,
        msg: Message
    ) -> None:
        if not self._connected_subscribers and not self.is_latching:
            return

        with self._serializer.serialize(msg) as serialized_msg:
            for subscriber in self._connected_subscribers.values():
                subscriber.queue.put_nowait(serialized_msg)
            if publisher.latch:
                self._latched_msgs[publisher] = serialized_msg

    async def connect_subscriber(
        self,
        node_name: str,
        subscriber: Subscriber
    ) -> None:
        for publisher in self._internal_publishers:
            if publisher.on_peer_connect:
                msg = publisher.on_peer_connect(node_name)
                if msg:
                    with self._serializer.serialize(msg) as serialized_msg:
                        await subscriber.queue.put(serialized_msg)

            serialized_msg = self._latched_msgs.get(publisher)
            if serialized_msg is not None:
                await subscriber.queue.put(serialized_msg)
        self._connected_subscribers[node_name] = subscriber
        self._has_connected_subscribers.set()

    def disconnect_subscriber(
        self,
        node_name: str
    ) -> None:
        for publisher in self._internal_publishers:
            if publisher.on_peer_disconnect:
                publisher.on_peer_disconnect(node_name)
        self._connected_subscribers[node_name].close.set()
        del self._connected_subscribers[node_name]
        if not self._connected_subscribers:
            self._has_connected_subscribers.clear()

    def connect_to_publishers(
        self,
        publishers: List[str]
    ) -> None:
        publishers_set = set(publishers)
        for publisher_uri in publishers:
            if publisher_uri in self._connected_publishers:
                continue
            self._connected_publishers[publisher_uri] = Event()
            self._loop.create_task(
                self._subscribe(publisher_uri))
        for publisher_uri in self._connected_publishers:
            if publisher_uri not in publishers_set:
                self._connected_publishers[publisher_uri].set()

    async def _subscribe(
        self,
        publisher_uri: str
    ) -> None:
        connection_params = await self._get_publisher_connection_params(
            publisher_uri)

        writer = None
        should_terminate = None
        try:
            if connection_params[0] == 'UNIXROS':
                reader, writer = await open_unix_connection(
                    connection_params[1])
            elif connection_params[0] == 'TCPROS':
                reader, writer = await open_connection(
                    connection_params[1],
                    int(connection_params[2]))
            else:
                return
            header = dict(
                topic=self.name,
                message_definition=self.type._full_text,
                tcp_nodelay='1',
                md5sum=self.md5sum,
                type=self.type_name,
                callerid=self._node_name)

            writer.write(encode_header(header))
            await writer.drain()

            header_dict = await read_header(reader)
            if 'error' in header_dict:
                raise SubscriberInitError(header_dict['error'])

            self._has_connected_publishers.set()

            should_terminate = self._loop.create_task(
                self._connected_publishers[publisher_uri].wait())

            while True:
                read_task = self._loop.create_task(read_data(reader))
                done, _ = await wait(
                    {should_terminate, read_task},
                    return_when=FIRST_COMPLETED)
                if should_terminate in done:
                    read_task.cancel()
                    break
                msg = self.type()
                msg.deserialize(read_task.result())
                for queue in self._internal_subscriptions.values():
                    queue.put_nowait(msg)
        except (ConnectionResetError, IncompleteReadError):
            if should_terminate:
                should_terminate.cancel()
        finally:
            if writer:
                writer.close()
                if hasattr(writer, 'wait_closed'):
                    await writer.wait_closed()
            self._connected_publishers.pop(publisher_uri)
            if not self._connected_publishers:
                self._has_connected_publishers.clear()

    async def _get_publisher_connection_params(
        self,
        publisher_uri: str
    ) -> Tuple[str, int]:
        client = NodeApiClient(self._node_name, publisher_uri)
        topic = await client.request_topic(
            self.name,
            [['UNIXROS'], ['TCPROS']])
        await client.close()
        if topic[0] not in ('UNIXROS', 'TCPROS'):
            raise ValueError('protocol is not supported')
        return topic
