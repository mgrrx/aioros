from asyncio import Queue
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager


class AsyncMessageStream(AsyncIterator):

    def __init__(self, topic, queue):
        self._topic = topic
        self._queue = queue

    async def wait_for_publishers(self):
        await self._topic.wait_for_connected_publishers()

    def __aiter__(self):
        return self

    async def  __anext__(self):
        msg = await self._queue.get()
        self._queue.task_done()
        return msg


class Subscription(AbstractAsyncContextManager):

    __slots__ = (
        '_manager',
        '_topic_name',
        '_msg_type',
        '_active_subscription')

    def __init__(self, manager, topic_name, msg_type):
        self._manager = manager
        self._topic_name = topic_name
        self._msg_type = msg_type
        self._active_subscription = None

    @property
    def topic_name(self):
        return self._topic_name

    @property
    def msg_type(self):
        return self._msg_type

    async def __aenter__(self) -> AsyncMessageStream:
        topic, queue = await self._manager.register_subscription(self)
        self._active_subscription = AsyncMessageStream(topic, queue)
        return self._active_subscription

    async def __aexit__(self, exc_type, exc, tb):
        await self._manager.unregister_subscription(self)
        self._active_subscription = None
