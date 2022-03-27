import time
from abc import ABCMeta, abstractmethod

import anyio
from anyio.abc import TaskStatus
from genpy import Duration, Time
from rosgraph_msgs.msg import Clock

from .. import abc


class TimeManager(metaclass=ABCMeta):
    @abstractmethod
    def get_time(self) -> Time:
        ...

    @abstractmethod
    async def sleep(self, duration: Duration) -> None:
        ...


class WallTimeManager(TimeManager):
    def get_time(self) -> Time:
        return Time.from_sec(time.time())

    async def sleep(self, duration: Duration) -> None:
        await anyio.sleep(duration.to_sec())


class SimTimeManager(TimeManager):
    def __init__(self) -> None:
        self._time = Time(0, 0)
        self._cond = anyio.Condition()

    def get_time(self) -> Time:
        return self._time

    async def sleep(self, duration: Duration) -> None:
        end = self.get_time() + duration
        while end > self.get_time():
            async with self._cond:
                if end < self.get_time():
                    # we need to check again since time could have elapsed while
                    # entering __aenter__
                    break
                await self._cond.wait()

    async def run(
        self, ros_node: abc.Node, *, task_status: TaskStatus = anyio.TASK_STATUS_IGNORED
    ) -> None:
        async with ros_node.create_subscription("/clock", Clock) as subscription:
            self._time = (await subscription.__anext__()).clock
            task_status.started()
            async for clock in subscription:
                self._time = clock.clock
                async with self._cond:
                    self._cond.notify_all()
