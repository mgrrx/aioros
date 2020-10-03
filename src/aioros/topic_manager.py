from asyncio import AbstractEventLoop
from asyncio import Queue
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Type

from genpy import Message

from .api.master_api_client import MasterApiClient
from .tcpros.publisher import Publisher
from .tcpros.subscription import Subscription
from .tcpros.topic import Topic


class TopicManager:

    def __init__(
        self,
        master_api_client: MasterApiClient,
        node_name: str,
        loop: AbstractEventLoop
    ) -> None:
        self._master_api_client = master_api_client
        self._node_name = node_name
        self._loop = loop
        self._topics: Dict[str, Topic] = {}

    @property
    def topics(self) -> Dict[str, Topic]:
        return self._topics

    def get(self, topic_name: str) -> Optional[Topic]:
        return self._topics.get(topic_name)

    async def close(self) -> None:
        for topic in self._topics.values():
            if topic.has_publishers:
                await self._master_api_client.unregister_publisher(
                    topic.name,
                    topic.type_name)
            if topic.has_subscriptions:
                await self._master_api_client.unregister_subscriber(
                    topic.name,
                    topic.type_name)
        self._topics.clear()

    async def unregister_publisher(
        self,
        publisher: Publisher
    ) -> None:
        if publisher.topic_name not in self._topics:
            return

        topic = self._topics[publisher.topic_name]
        await topic.unregister_publisher(publisher)
        if not topic.has_subscriptions and not topic.has_publishers:
            del self._topics[publisher.topic_name]

    async def create_publisher(
        self,
        node_name: str,
        topic_name: str,
        msg_type: Type[Message],
        *,
        on_peer_connect: Optional[Callable[[str], Optional[Message]]] = None,
        on_peer_disconnect: Optional[Callable[[str], None]] = None,
        latch: bool = False
    ) -> Publisher:
        topic = self.get(topic_name)
        if not topic:
            topic = Topic(
                self._loop,
                self._master_api_client,
                node_name,
                topic_name,
                msg_type)
            self._topics[topic_name] = topic
        publisher = Publisher(
            self,
            topic,
            on_peer_connect=on_peer_connect,
            on_peer_disconnect=on_peer_disconnect,
            latch=latch)
        await topic.register_publisher(publisher)
        return publisher

    def create_subscription(
        self,
        topic_name: str,
        msg_type: Type[Message]
    ) -> Subscription:
        return Subscription(self, topic_name, msg_type)

    async def register_subscription(
        self,
        subscription: Subscription
    ) -> Tuple[Topic, Queue]:
        topic = self.get(subscription.topic_name)
        if not topic:
            topic = Topic(
                self._loop,
                self._master_api_client,
                self._node_name,
                subscription.topic_name,
                subscription.msg_type)
            self._topics[subscription.topic_name] = topic
        queue = Queue()
        await topic.register_subscription(subscription, queue)
        return topic, queue

    async def unregister_subscription(
        self,
        subscription: Subscription
    ) -> None:
        topic = self.get(subscription.topic_name)
        if not topic:
            return
        if await topic.unregister_subscription(subscription):
            del self._topics[subscription.topic_name]
