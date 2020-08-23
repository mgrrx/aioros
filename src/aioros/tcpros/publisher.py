class Publisher:

    def __init__(
        self,
        manager,
        topic,
        *,
        latch: bool = False
    ) -> None:
        self._manager = manager
        self._topic = topic
        self._latch = latch

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
