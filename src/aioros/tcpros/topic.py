from asyncio import Event
from asyncio import IncompleteReadError
from asyncio import Queue
from asyncio import gather
from asyncio import get_event_loop
from asyncio import open_connection
from typing import Dict
from typing import List
from typing import Set
from typing import Tuple

from ..api.node_api_client import NodeApiClient
from .protocol import Serializer
from .protocol import encode_header
from .protocol import read_data
from .protocol import read_header
from .publisher import Publisher
from .subscription import Subscription


class SubscriberInitError(Exception):
    pass


class Topic:

    def __init__(self, manager, node_name, topic_name, msg_type):
        self._manager = manager
        self._node_name: str = node_name
        self._topic_name: str = topic_name
        self._msg_type = msg_type
        self._serializer: Serializer = Serializer()

        self._connected_subscribers: Set[Queue] = set()
        self._connected_publishers: Dict[str, Event] = {}
        self._internal_subscriptions: Set[Subscription] = set()
        self._internal_publishers: Set[Publisher] = set()
        self._latched_msgs = {}

    @property
    def name(self) -> str:
        return self._topic_name

    @property
    def type(self):
        return self._msg_type

    @property
    def type_name(self) -> str:
        return self._msg_type._type

    @property
    def md5sum(self) -> str:
        return self._msg_type._md5sum

    @property
    def has_subscriptions(self) -> bool:
        return bool(self._internal_subscriptions)

    @property
    def has_publishers(self) -> bool:
        return bool(self._internal_publishers)

    def get_publisher_header(self) -> Dict[str, str]:
        latching = any(pub.latch for pub in self._internal_publishers)
        return dict(
            topic=self.name,
            type=self.type_name,
            latching='1' if latching else '0',
            message_definition=self.type._full_text,
            md5sum=self.md5sum,
            callerid=self._node_name)

    def register_publisher(self, publisher: Publisher) -> None:
        self._internal_publishers.add(publisher)

    async def unregister_publisher(
        self,
        publisher: Publisher
    ) -> bool:
        self._latched_msgs.pop(publisher, None)
        self._internal_publishers.discard(publisher)
        return self.has_publishers

    def register_subscription(self, subscription: Subscription) -> None:
        self._internal_subscriptions.add(subscription)

    async def unregister_subscription(
        self,
        subscription: Subscription
    ) -> bool:
        self._internal_subscriptions.pop(subscription)
        if not self.has_subscriptions:
            print("Disconnecting from all publishers")
            for event in self._connected_publishers.values():
                event.set()
        return self.has_subscriptions

    async def publish(self, publisher: Publisher, msg):
        with self._serializer.serialize(msg) as serialized_msg:
            await gather(*[
                queue.put(serialized_msg)
                for queue in self._connected_subscribers])
            if publisher.latch:
                self._latched_msgs[publisher] = serialized_msg

    async def connect_subscriber(self, queue: Queue) -> None:
        for publisher in self._internal_publishers:
            serialized_msg = self._latched_msgs.get(publisher)
            if serialized_msg is not None:
                await queue.put(serialized_msg)
        self._connected_subscribers.add(queue)

    def connect_to_publishers(self, publishers: List[str]) -> None:
        loop = get_event_loop()
        _publishers = set(publishers)
        for publisher_uri in publishers:
            if publisher_uri in self._connected_publishers:
                continue
            self._connected_publishers[publisher_uri] = Event()
            loop.create_task(self._subscribe(publisher_uri, loop))
        for publisher_uri in self._connected_publishers:
            if publisher_uri not in _publishers:
                self._connected_publishers[publisher_uri].set()

    async def _subscribe(self, publisher_uri: str, loop):

        host, port = await self._get_publisher_host_port(publisher_uri)

        try:
            reader, writer = await open_connection(host, port)
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

            while not self._connected_publishers[publisher_uri].is_set():
                msg = self.type()
                msg.deserialize(await read_data(reader))
                for sub in self._internal_subscriptions:
                    loop.create_task(sub.callback(msg))
        except (ConnectionResetError, IncompleteReadError):
            pass
        finally:
            writer.close()
            if hasattr(writer, 'wait_closed'):
                await writer.wait_closed()
            self._connected_publishers.pop(publisher_uri)

    async def _get_publisher_host_port(
        self,
        publisher_uri: str
    ) -> Tuple[str, int]:
        client = NodeApiClient(publisher_uri)
        topic = await client.request_topic(
            self._node_name,
            self.name,
            [['TCPROS']])
        await client.close()
        if len(topic) != 3:
            raise ValueError('Expecting topic information of length 3')
        elif topic[0] != 'TCPROS':
            raise ValueError('only TCPROS is supported')
        return topic[1], topic[2]
