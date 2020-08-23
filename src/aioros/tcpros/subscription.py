class Subscription:

    __slots__ = ('_manager', '_topic', 'callback')

    def __init__(self, manager, topic, callback):
        self._manager = manager
        self._topic = topic
        self.callback = callback

    @property
    def topic_name(self):
        return self._topic.name

    async def close(self) -> None:
        self._manager.unregister_subscription(self)
