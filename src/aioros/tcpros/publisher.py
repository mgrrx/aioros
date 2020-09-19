from typing import Callable
from typing import Optional

from genpy import Message


class Publisher:

    def __init__(
        self,
        manager,
        topic,
        *,
        on_peer_connect: Optional[Callable[[str], Optional[Message]]] = None,
        on_peer_disconnect: Optional[Callable[[str], None]] = None,
        latch: bool = False
    ) -> None:
        self._manager = manager
        self._topic = topic
        self.on_peer_connect = on_peer_connect
        self.on_peer_disconnect = on_peer_disconnect
        self._latch = latch

    @property
    def latch(self):
        return self._latch

    @property
    def topic_name(self) -> str:
        return self._topic.name

    async def wait_for_subscribers(self):
        await self._topic.wait_for_connected_subscribers()

    async def close(self) -> None:
        await self._manager.unregister_publisher(self)

    def publish(self, msg):
        self._topic.publish(self, msg)
