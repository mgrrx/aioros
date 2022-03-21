from typing import AsyncIterator, Optional, Type
from uuid import uuid4

import anyio
from actionlib_msgs.msg import GoalID, GoalStatusArray
from anyio.abc import TaskGroup, TaskStatus
from genpy import Time
from std_msgs.msg import Header

from aioros import abc

from ._state_machine import CommStateMachine


class ActionCall(abc.ActionCall[abc.FeedbackT, abc.ResultT]):
    def __init__(
        self,
        pub_cancel: abc.Publication[GoalID],
        feedback_type: Type[abc.FeedbackT],
        goal_id: GoalID,
    ) -> None:
        self._pub_cancel = pub_cancel
        self._goal_id = goal_id
        self._sm = CommStateMachine(goal_id)
        self._terminated = anyio.Event()
        self._result: Optional[abc.ResultT] = None
        (
            self._feedback_send_stream,
            self._feedback_receive_stream,
        ) = anyio.create_memory_object_stream(float("inf"), feedback_type)

    async def track(
        self,
        sub_status: abc.Subscription[GoalStatusArray],
        sub_feedback: abc.Subscription[abc.ActionFeedback[abc.FeedbackT]],
        sub_result: abc.Subscription[abc.ActionResult[abc.ResultT]],
        *,
        task_status: TaskStatus = anyio.TASK_STATUS_IGNORED,
    ) -> None:
        async with anyio.create_task_group() as task_group:
            await task_group.start(self._track_status, sub_status)
            await task_group.start(self._track_feedback, sub_feedback)
            await task_group.start(self._track_result, sub_result)
            task_status.started()
            await self._terminated.wait()
            task_group.cancel_scope.cancel()

    async def _track_status(
        self,
        subscription: abc.Subscription[GoalStatusArray],
        *,
        task_status: TaskStatus = anyio.TASK_STATUS_IGNORED,
    ) -> None:
        async with subscription:
            task_status.started()
            async for msg in subscription:
                self._sm.update_status(msg)
                if self._sm.comm_state.is_terminal:
                    self._terminated.set()
                    break

    async def _track_feedback(
        self,
        subscription: abc.Subscription[abc.ActionFeedback[abc.FeedbackT]],
        *,
        task_status: TaskStatus = anyio.TASK_STATUS_IGNORED,
    ) -> None:
        async with subscription, self._feedback_send_stream:
            task_status.started()
            async for msg in subscription:
                if msg.status.goal_id.id == self._goal_id.id:
                    await self._feedback_send_stream.send(msg.feedback)

    async def _track_result(
        self,
        subscription: abc.Subscription[abc.ActionResult[abc.ResultT]],
        *,
        task_status: TaskStatus = anyio.TASK_STATUS_IGNORED,
    ) -> None:
        async with subscription:
            task_status.started()
            async for msg in subscription:
                if (
                    msg.status.goal_id.id == self._goal_id.id
                    and self._sm.update_on_result_status(msg.status)
                ):
                    self._result = msg.result
                    self._terminated.set()
                    break

    async def cancel(self) -> None:
        await self._pub_cancel.publish(self._goal_id)

    def feedback(self) -> AsyncIterator[abc.FeedbackT]:
        return self._provide_feedback()

    async def _provide_feedback(self) -> AsyncIterator[abc.FeedbackT]:
        try:
            async with self._feedback_receive_stream:
                async for msg in self._feedback_receive_stream:
                    yield msg
        except anyio.ClosedResourceError:
            pass

    def get_goal_state(self) -> abc.GoalState:
        return self._sm.goal_state

    def get_comm_state(self) -> abc.CommState:
        return self._sm.comm_state

    async def wait_for_result(self) -> Optional[abc.ResultT]:
        await self._terminated.wait()
        return self._result


class ActionClient(abc.ActionClient[abc.GoalT, abc.FeedbackT, abc.ResultT]):
    def __init__(
        self,
        node: abc.Node,
        task_group: TaskGroup,
        namespace: str,
        action: Type[abc.Action[abc.GoalT, abc.FeedbackT, abc.ResultT]],
    ) -> None:
        self._node = node
        self._task_group = task_group

        self._pub_goal = node.create_publication(
            f"{namespace}/goal", type(action().action_goal)
        )
        self._pub_cancel = node.create_publication(f"{namespace}/cancel", GoalID)
        self._sub_status = node.create_subscription(
            f"{namespace}/status", GoalStatusArray
        )
        self._sub_feedback = node.create_subscription(
            f"{namespace}/feedback", type(action().action_feedback)
        )
        self._sub_result = node.create_subscription(
            f"{namespace}/result", type(action().action_result)
        )

    async def __aenter__(
        self,
    ) -> "abc.ActionClient[abc.GoalT, abc.FeedbackT, abc.ResultT]":
        await self._pub_goal.__aenter__()
        await self._pub_cancel.__aenter__()
        await self._sub_status.__aenter__()
        await self._sub_feedback.__aenter__()
        await self._sub_result.__aenter__()
        return self

    async def aclose(self) -> None:
        await self._pub_goal.aclose()
        await self._pub_cancel.aclose()
        await self._sub_status.aclose()
        await self._sub_feedback.aclose()
        await self._sub_result.aclose()

    async def send_goal(
        self, goal: abc.GoalT
    ) -> abc.ActionCall[abc.FeedbackT, abc.ResultT]:
        goal_id = GoalID(id=str(uuid4()))
        action_goal = self._pub_goal.topic_type(
            goal_id=goal_id, goal=goal, header=Header(stamp=self._node.get_time())
        )
        call: ActionCall[abc.FeedbackT, abc.ResultT] = ActionCall(
            self._pub_cancel.clone(),
            type(self._sub_feedback.topic_type().feedback),
            goal_id,
        )
        await self._task_group.start(
            call.track,
            self._sub_status.clone(),
            self._sub_feedback.clone(),
            self._sub_result.clone(),
        )
        await self._pub_goal.publish(action_goal)
        return call

    async def wait_for_server(self) -> None:
        await self._pub_goal.wait_for_peers()
        await self._pub_cancel.wait_for_peers()
        await self._sub_status.wait_for_peers()
        await self._sub_feedback.wait_for_peers()
        await self._sub_result.wait_for_peers()

    async def cancel_all_goals(self) -> None:
        await self._pub_cancel.publish(GoalID())

    async def cancel_all_goals_until(self, time: Time) -> None:
        await self._pub_cancel.publish(GoalID(stamp=time))
