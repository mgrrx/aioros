from asyncio import AbstractEventLoop
from typing import Callable
from typing import Dict
from typing import Optional
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
        loop: AbstractEventLoop
    ) -> None:
        self._loop = loop
        self._master_api_client = master_api_client
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
        unregister_publisher = await topic.unregister_publisher(publisher)
        if unregister_publisher:
            await self._master_api_client.unregister_publisher(
                topic.name,
                topic.type_name)
        if not topic.has_subscriptions and not topic.has_publishers:
            del self._topics[publisher.topic_name]

    async def unregister_subscription(
        self,
        subscription: Subscription
    ) -> bool:
        if subscription.topic_name not in self._topics:
            return

        topic = self._topics[subscription.topic_name]
        unregister_subscription = await topic.unregister_subscription(
            subscription)
        if unregister_subscription:
            await self._master_api_client.unregister_subscriber(
                topic.name,
                topic.type_name)
        if not topic.has_subscriptions and not topic.has_publishers:
            del self._topics[subscription.topic_name]

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
            topic = Topic(self._loop, node_name, topic_name, msg_type)
            await self._master_api_client.register_publisher(
                topic.name,
                topic.type_name)
            self._topics[topic_name] = topic
        publisher = Publisher(
            self,
            topic,
            on_peer_connect=on_peer_connect,
            on_peer_disconnect=on_peer_disconnect,
            latch=latch)
        topic.register_publisher(publisher)
        return publisher

    async def create_subscription(
        self,
        node_name: str,
        topic_name: str,
        msg_type: Type[Message],
        callback: Callable[[Message], None]
    ) -> Subscription:
        topic = self.get(topic_name)
        if not topic:
            topic = Topic(self._loop, node_name, topic_name, msg_type)
            publishers = await self._master_api_client.register_subscriber(
                topic.name,
                topic.type_name)
            self._topics[topic_name] = topic
            topic.connect_to_publishers(publishers)
        subscription = Subscription(self, topic, callback)
        topic.register_subscription(subscription)
        return subscription
