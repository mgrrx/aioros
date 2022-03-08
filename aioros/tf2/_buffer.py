from typing import Callable, Optional

from anyio.to_thread import run_sync
from genpy import Duration, Time
from geometry_msgs.msg import TransformStamped

from .._node._context import get_time, sleep
from ._buffer_core import BufferCore
from ._buffer_interface import BufferInterface


async def run_sync_with_timeout(
    func: Callable[..., bool], *args: object, timeout: Optional[Duration] = None
) -> bool:
    if timeout is None:
        return await run_sync(func, *args)
    until = get_time() + timeout
    while get_time() < until:
        if await run_sync(func, *args):
            return True
        await sleep(Duration.from_sec(0.05))
    return False


class Buffer(BufferInterface):
    def __init__(self, cache_time: float = 10.0) -> None:
        self._buffer = BufferCore(cache_time)

    def clear(self) -> None:
        self._buffer.clear()

    def all_frames_as_string(self) -> str:
        return self._buffer.all_frames_as_string()

    def all_frames_as_yaml(self, current_time: float = 0.0) -> str:
        return self._buffer.all_frames_as_yaml(current_time)

    def set_transform(
        self, transform: TransformStamped, authority: str, is_static: bool = False
    ) -> None:
        self._buffer.set_transform(transform, authority, is_static)

    async def lookup_transform(
        self,
        target_frame: str,
        source_frame: str,
        time: Time,
        timeout: Optional[Duration] = None,
    ) -> TransformStamped:
        await self.can_transform(target_frame, source_frame, time, timeout)
        return await run_sync(
            self._buffer.lookup_transform,
            target_frame,
            source_frame,
            time,
        )

    async def lookup_transform_full(
        self,
        target_frame: str,
        target_time: Time,
        source_frame: str,
        source_time: Time,
        fixed_frame: str,
        timeout: Optional[Duration] = None,
    ) -> TransformStamped:
        await self.can_transform_full(
            target_frame, target_time, source_frame, source_time, fixed_frame, timeout
        )
        return await run_sync(
            self._buffer.lookup_transform_full,
            target_frame,
            target_time,
            source_frame,
            source_time,
            fixed_frame,
        )

    async def can_transform(
        self,
        target_frame: str,
        source_frame: str,
        time: Time,
        timeout: Optional[Duration] = None,
    ) -> bool:
        return await run_sync_with_timeout(
            self._buffer.can_transform,
            target_frame,
            source_frame,
            time,
            timeout=timeout,
        )

    async def can_transform_full(
        self,
        target_frame: str,
        target_time: Time,
        source_frame: str,
        source_time: Time,
        fixed_frame: str,
        timeout: Optional[Duration] = None,
    ) -> bool:
        return await run_sync_with_timeout(
            self._buffer.can_transform_full,
            target_frame,
            target_time,
            source_frame,
            source_time,
            fixed_frame,
            timeout=timeout,
        )
