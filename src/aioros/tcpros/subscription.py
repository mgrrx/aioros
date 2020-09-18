class Subscription:

    __slots__ = ('_manager', 'topic', 'callback')

    def __init__(self, manager, topic, callback):
        self._manager = manager
        self.topic = topic
        self.callback = callback

    @property
    def topic_name(self):
        return self.topic.name

    async def close(self) -> None:
        await self._manager.unregister_subscription(self)
