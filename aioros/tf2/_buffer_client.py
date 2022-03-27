from typing import Optional

from anyio.abc import AsyncResource
from genpy.message import Duration, Time
from geometry_msgs.msg import TransformStamped
from tf2_msgs.msg import (
    LookupTransformAction,
    LookupTransformGoal,
    LookupTransformResult,
    TF2Error,
)

from ..abc import Node
from ._buffer_core import (
    ConnectivityException,
    ExtrapolationException,
    InvalidArgumentException,
    LookupException,
    TimeoutException,
    TransformException,
)
from ._buffer_interface import BufferInterface


class BufferClient(BufferInterface, AsyncResource):
    def __init__(self, node: Node, namespace: str) -> None:
        self._action = node.create_action_client(namespace, LookupTransformAction)

    async def __aenter__(self) -> "BufferClient":
        await self._action.__aenter__()
        return self

    async def aclose(self) -> None:
        await self._action.aclose()

    async def _call_action(self, goal: LookupTransformGoal) -> TransformStamped:
        result: Optional[LookupTransformResult] = (
            await self._action.send_goal(goal)
        ).wait_for_result()

        if not result:
            raise TransformException("No result from server")

        if result.error.error != TF2Error.NO_ERROR:
            if result.error.error == TF2Error.LOOKUP_ERROR:
                raise LookupException(result.error.error_string)
            if result.error.error == TF2Error.CONNECTIVITY_ERROR:
                raise ConnectivityException(result.error.error_string)
            if result.error.error == TF2Error.EXTRAPOLATION_ERROR:
                raise ExtrapolationException(result.error.error_string)
            if result.error.error == TF2Error.INVALID_ARGUMENT_ERROR:
                raise InvalidArgumentException(result.error.error_string)
            if result.error.error == TF2Error.TIMEOUT_ERROR:
                raise TimeoutException(result.error.error_string)
            raise TransformException(result.error.error_string)

        return result.transform

    async def lookup_transform(
        self,
        target_frame: str,
        source_frame: str,
        time: Time,
        timeout: Optional[Duration] = None,
    ) -> TransformStamped:
        return await self._call_action(
            LookupTransformGoal(
                target_frame=target_frame,
                source_frame=source_frame,
                source_time=time,
                timeout=timeout or Duration(),
                advanced=False,
            )
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
        return await self._call_action(
            LookupTransformGoal(
                target_frame=target_frame,
                source_frame=source_frame,
                source_time=source_time,
                timeout=timeout or Duration(),
                target_time=target_time,
                fixed_frame=fixed_frame,
                advanced=True,
            )
        )

    async def can_transform(
        self,
        target_frame: str,
        source_frame: str,
        time: Time,
        timeout: Optional[Duration] = None,
    ) -> bool:
        try:
            self.lookup_transform(target_frame, source_frame, time, timeout)
            return True
        except TransformException:
            return False

    async def can_transform_full(
        self,
        target_frame: str,
        target_time: Time,
        source_frame: str,
        source_time: Time,
        fixed_frame: str,
        timeout: Optional[Duration] = None,
    ) -> bool:
        try:
            self.lookup_transform_full(
                target_frame,
                target_time,
                source_frame,
                source_time,
                fixed_frame,
                timeout,
            )
            return True
        except TransformException:
            return False
