from abc import ABC
from abc import abstractmethod
from asyncio import Event
from time import time
from typing import Optional

from genpy import Time
from rosgraph_msgs.msg import Clock

from .tcpros.subscription import Subscription


class TimeManager(ABC):

    @abstractmethod
    def get_time(self) -> Time:
        pass

    async def close(self) -> None:
        pass


class WallTimeManager(TimeManager):

    def get_time(self) -> Time:
        return Time.from_sec(time())


class SimTimeManager(TimeManager):

    def __init__(self):
        self._time: Optional[Time] = None
        self._subscription: Optional[Subscription] = None
        self._time_initialized: Event = Event()

    async def init(self, node_handle):
        self._subscription = await node_handle.create_subscription(
            '/clock', Clock, self._set_time)
        await self._time_initialized.wait()

    async def close(self) -> None:
        await self._subscription.close()

    def _set_time(self, msg: Clock) -> None:
        self._time = msg.clock
        if not self._time_initialized.is_set():
            self._time_initialized.set()

    def get_time(self) -> Time:
        return self._time


async def start_time_manager(node_handle) -> TimeManager:
    try:
        use_sim_time = await node_handle.get_param('/use_sim_time')
    except KeyError:
        use_sim_time = False

    if use_sim_time:
        manager = SimTimeManager()
        await manager.init(node_handle)
        return manager
    return WallTimeManager()
