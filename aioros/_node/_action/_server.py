from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Generic, Optional, Set, Type

import anyio
from actionlib_msgs.msg import GoalID, GoalStatus, GoalStatusArray
from anyio.abc import TaskStatus
from genpy import Time
from std_msgs.msg import Header

from aioros import abc


class ActionServerGoalHandle(abc.ActionServerGoalHandle[abc.GoalT]):
    def __init__(
        self,
        node: abc.Node,
        action_goal: abc.ActionGoal[abc.GoalT],
    ) -> None:
        self._node = node
        self._action_goal = action_goal
        self._state: abc.GoalState = abc.GoalState.PENDING

    @property
    def state(self) -> abc.GoalState:
        return self._state

    @state.setter
    def state(self, state: abc.GoalState) -> None:
        self._state = state

    @property
    def goal(self) -> abc.GoalT:
        return self._action_goal.goal

    @property
    def goal_id(self) -> GoalID:
        return self._action_goal.goal_id

    def on_cancel_request(self) -> None:
        if self.state == abc.GoalState.PENDING:
            self.state = abc.GoalState.RECALLING
        elif self.state == abc.GoalState.ACTIVE:
            self.state = abc.GoalState.PREEMPTING

    def accept(self) -> None:
        if self.state == abc.GoalState.PENDING:
            self.state = abc.GoalState.ACTIVE
        elif self.state == abc.GoalState.RECALLING:
            self.state = abc.GoalState.PREEMPTING

    # async def send_feedback(self, feedback: abc.FeedbackT) -> None:
    #    await self._pub_feedback.publish(
    #        self._pub_feedback.topic_type(
    #            header=Header(stamp=self._node.get_time()),
    #            status=GoalStatus(status=self.state),
    #            feedback=feedback,
    #        )
    #    )


class ActionServer(abc.ActionServer[abc.GoalT, abc.FeedbackT, abc.ResultT]):
    def __init__(
        self,
        node: abc.Node,
        namespace: str,
        action: Type[abc.Action[abc.GoalT, abc.FeedbackT, abc.ResultT]],
        handler: Callable[
            [abc.ActionServerGoalHandle[abc.GoalT]],
            Awaitable[Optional[abc.ResultT]],
        ],
    ) -> None:
        self._node = node
        self._handler = handler
        self._sub_goal: abc.Subscription[
            abc.ActionGoal[abc.GoalT]
        ] = self._node.create_subscription(
            f"{namespace}/goal", type(action().action_goal)
        )
        self._sub_cancel: abc.Subscription[GoalID] = self._node.create_subscription(
            f"{namespace}/cancel", GoalID
        )
        self._pub_feedback: abc.Publication[
            abc.ActionFeedback[abc.FeedbackT]
        ] = self._node.create_publication(
            f"{namespace}/feedback",
            type(action().action_feedback),
        )
        self._pub_result: abc.Publication[
            abc.ActionResult[abc.ResultT]
        ] = self._node.create_publication(
            f"{namespace}/result", type(action().action_result)
        )
        self._pub_status: abc.Publication[
            GoalStatusArray
        ] = self._node.create_publication(f"{namespace}/status", GoalStatusArray)

        self._goal_handles: Dict[
            str, ActionServerGoalHandle[abc.GoalT, abc.FeedbackT]
        ] = {}
        self._cancelled_goals: Set[str] = set()
        self._last_cancel_request = Time()

    async def serve(self) -> None:
        async with self._sub_goal, self._pub_feedback, self._pub_result:
            async with anyio.create_task_group() as task_group:
                await task_group.start(self._periodically_publish_status)
                await task_group.start(self._manage_out_of_order_cancel)
                async for goal in self._sub_goal:
                    await task_group.start(self._execute_goal, goal)

    async def _manage_out_of_order_cancel(
        self, *, task_status: TaskStatus = anyio.TASK_STATUS_IGNORED
    ) -> None:
        # TODO one task for cancel cb
        # cancel might come before actual goal
        async def remove_cancelled_goal(goal_id: GoalID) -> None:
            await anyio.sleep(5.0)
            self._cancelled_goals.discard(goal_id.id)

        async with self._sub_cancel:
            async with anyio.create_task_group() as task_group:
                task_status.started()
                async for goal_id in self._sub_cancel:
                    if goal_id.id != "" and not any(
                        cancel_requested(goal_handle, goal_id)
                        for goal_handle in self._goal_handles.values()
                    ):
                        # goal_id was not found and it is not empty => we need to store this
                        # cancellation request and consider it when accepting the next goal
                        self._cancelled_goals.add(goal_id.id)
                        task_group.start(remove_cancelled_goal, goal_id)

                    if self._last_cancel_request < goal_id.stamp:
                        self._last_cancel_request = goal_id.stamp

    async def _periodically_publish_status(
        self, *, task_status: TaskStatus = anyio.TASK_STATUS_IGNORED
    ) -> None:
        async with self._pub_status:
            task_status.started()
            await self._publish_status()
            # TODO parameterize
            await anyio.sleep(1.0)

    async def _publish_status(self) -> None:
        await self._pub_status.publish(
            GoalStatusArray(
                header=Header(stamp=self._node.get_time()),
                status_list=[
                    GoalStatus(status=goal_handle.state)
                    for goal_handle in self._goal_handles.values()
                ],
            )
        )

    async def _publish_result(
        self,
        goal_handle: ActionServerGoalHandle[abc.GoalT],
        result: abc.ResultT,
    ) -> None:
        await self._pub_result.publish(
            self._pub_result.topic_type(
                header=Header(stamp=self._node.get_time()),
                status=GoalStatus(status=goal_handle.state),
                result=result,
            )
        )

    async def _execute_goal(
        self,
        goal: abc.ActionGoal[abc.GoalT],
        *,
        task_status: TaskStatus = anyio.TASK_STATUS_IGNORED,
    ) -> None:
        async with anyio.create_task_group() as task_group:
            cancel_scope = anyio.CancelScope()
            terminated = anyio.Event()
            goal_handle = ActionServerGoalHandle(
                self._node,
                goal,
                self._pub_feedback,
            )

            async def track_cancel(
                *,
                task_status: TaskStatus = anyio.TASK_STATUS_IGNORED,
            ) -> None:
                async with self._sub_cancel.clone() as cancel_subscription:
                    task_status.started()
                    async for goal_id in cancel_subscription:
                        if cancel_requested(goal_handle, goal_id):
                            goal_handle.on_cancel_request()
                            cancel_scope.cancel()
                            break

            async def run() -> None:
                # evtl am besten durch ein callable das übergeben werden kann. falls leer akzeptieren wir immer
                # TODO goal_handle.accept()
                async with cancel_scope:
                    result = await self._handler(goal_handle)

                goal_handle.state = abc.GoalState.SUCCEEDED
                if result:
                    # TODO else?
                    await self._publish_result(goal_handle, result)
                terminated.set()

            self._goal_handles[goal.goal_id.id] = goal_handle

            if (
                (
                    goal.goal_id.stamp != Time()
                    and goal.goal_id.stamp <= self._last_cancel_request
                )
                or (goal.goal_id.id in self._cancelled_goals)
                or (goal.goal_id.id in self._goal_handles)
            ):
                # Goal is older than the latest cancel request
                print("publish cancel")
                task_status.started()
                goal_handle.state = abc.GoalState.RECALLED
                await self._publish_result(
                    goal_handle, self._pub_result.topic_type().result
                )
            else:
                await task_group.start(track_cancel)
                task_status.started()
                task_group.start_soon(run)

                await terminated.wait()

                task_group.cancel_scope.cancel()

            # yield back
            await anyio.sleep(0.0)

            await self._publish_status()

            # sleep for status_list_timeout seconds
            await anyio.sleep(5.0)
            del self._goal_handles[goal.goal_id.id]


def cancel_requested(goal_handle: ActionServerGoalHandle, goal_id: GoalID) -> bool:
    return (
        (goal_id.id == "" and goal_id.stamp == Time())
        or (goal_id.id == goal_handle.goal_id.id)
        or (goal_id.stamp != Time() and goal_handle.goal_id.stamp <= goal_id.stamp)
    )
