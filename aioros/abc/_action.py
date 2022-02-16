from abc import ABCMeta, abstractmethod
from enum import IntEnum, unique
from typing import AsyncIterator, FrozenSet, Generic, Optional, Protocol, TypeVar

from actionlib_msgs.msg import GoalID, GoalStatus
from anyio.abc import AsyncResource
from genpy import Message, Time
from std_msgs.msg import Header

GoalT = TypeVar("GoalT", bound=Message)
FeedbackT = TypeVar("FeedbackT", bound=Message)
ResultT = TypeVar("ResultT", bound=Message)


class ActionGoal(Protocol[GoalT]):
    header: Header
    goal_id: GoalID
    goal: GoalT


class ActionResult(Protocol[ResultT]):
    header: Header
    status: GoalStatus
    result: ResultT


class ActionFeedback(Protocol[FeedbackT]):
    header: Header
    status: GoalStatus
    feedback: FeedbackT


class Action(Protocol[GoalT, FeedbackT, ResultT]):
    action_goal: ActionGoal[GoalT]
    action_result: ActionResult[ResultT]
    action_feedback: ActionFeedback[FeedbackT]


@unique
class CommState(IntEnum):
    WAITING_FOR_GOAL_ACK = 0
    PENDING = 1
    ACTIVE = 2
    WAITING_FOR_RESULT = 3
    WAITING_FOR_CANCEL_ACK = 4
    RECALLING = 5
    PREEMPTING = 6
    DONE = 7
    LOST = 8

    @property
    def terminal(self) -> FrozenSet[int]:
        return frozenset((self.DONE, self.LOST))

    @property
    def is_terminal(self) -> bool:
        return self in self.terminal


@unique
class GoalState(IntEnum):
    PENDING = GoalStatus.PENDING
    ACTIVE = GoalStatus.ACTIVE
    PREEMPTED = GoalStatus.PREEMPTED
    SUCCEEDED = GoalStatus.SUCCEEDED
    ABORTED = GoalStatus.ABORTED
    REJECTED = GoalStatus.REJECTED
    PREEMPTING = GoalStatus.PREEMPTING
    RECALLING = GoalStatus.RECALLING
    RECALLED = GoalStatus.RECALLED
    LOST = GoalStatus.LOST

    @property
    def terminal(self) -> FrozenSet[int]:
        return frozenset(
            (
                self.RECALLED,
                self.REJECTED,
                self.PREEMPTED,
                self.ABORTED,
                self.SUCCEEDED,
                self.LOST,
            )
        )

    @property
    def is_terminal(self) -> bool:
        return self in self.terminal


class ActionCall(Generic[FeedbackT, ResultT], metaclass=ABCMeta):
    @abstractmethod
    async def cancel(self) -> None:
        ...

    @abstractmethod
    def feedback(self) -> AsyncIterator[FeedbackT]:
        ...

    @abstractmethod
    def get_goal_state(self) -> GoalState:
        ...

    @abstractmethod
    def get_comm_state(self) -> CommState:
        ...

    @abstractmethod
    async def wait_for_result(self) -> Optional[ResultT]:
        ...


class ActionClient(
    AsyncResource, Generic[GoalT, FeedbackT, ResultT], metaclass=ABCMeta
):
    @abstractmethod
    async def send_goal(self, goal: GoalT) -> ActionCall[FeedbackT, ResultT]:
        ...

    @abstractmethod
    async def wait_for_server(self) -> None:
        ...

    @abstractmethod
    async def cancel_all_goals(self) -> None:
        ...

    @abstractmethod
    async def cancel_all_goals_until(self, time: Time) -> None:
        ...
