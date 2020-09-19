from asyncio import AbstractEventLoop
from asyncio import get_event_loop
from asyncio import iscoroutinefunction
from asyncio import sleep
from typing import Callable
from typing import Optional


class Timer:

    def __init__(
        self,
        period: float,
        callback: Callable,
        *,
        loop: Optional[AbstractEventLoop] = None
    ) -> None:
        self._period = period
        self._callback = callback
        self._loop = loop or get_event_loop()
        loop.create_task(self._run())

    def stop(self):
        self._running = False

    async def _run(self):
        self._running = True
        while self._running:
            if iscoroutinefunction(self._callback):
                self._loop.create_task(self._callback())
            else:
                self._loop.call_soon(self._callback)
            await sleep(self._period)
