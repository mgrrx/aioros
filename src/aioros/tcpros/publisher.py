from typing import Callable
from typing import Optional


class Publisher:

    def __init__(
        self,
        manager,
        topic,
        *,
        on_peer_connect: Optional[Callable] = None,
        on_peer_disconnect: Optional[Callable] = None,
        latch: bool = False
    ) -> None:
        self._manager = manager
        self._topic = topic
        self.on_peer_connect = on_peer_connect
        self.on_peer_disconnect = on_peer_disconnect
        self._latch: bool = latch

    @property
    def latch(self):
        return self._latch

    @property
    def topic_name(self) -> str:
        return self._topic.name

    async def close(self) -> None:
        self._manager.unregister_publisher(self)

    async def publish(self, msg):
        await self._topic.publish(self, msg)
