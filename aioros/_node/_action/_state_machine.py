from dataclasses import dataclass
from typing import NoReturn, cast

from actionlib_msgs.msg import GoalID, GoalStatus, GoalStatusArray

from aioros.abc import CommState, GoalState


@dataclass
class CommStateMachine:
    goal_id: GoalID
    goal_state: GoalState = GoalState.PENDING
    comm_state: CommState = CommState.WAITING_FOR_GOAL_ACK

    def update_status(self, status_array: GoalStatusArray) -> None:
        try:
            self.goal_state = GoalState(
                next(
                    cast(GoalStatus, status).status
                    for status in status_array.status_list
                    if cast(GoalStatus, status).goal_id.id == self.goal_id.id
                )
            )
        except ValueError:
            return
        except StopIteration:
            if self.comm_state not in (
                CommState.WAITING_FOR_GOAL_ACK,
                CommState.WAITING_FOR_RESULT,
                CommState.DONE,
            ):
                self.goal_state = GoalState.LOST
                self.comm_state = CommState.DONE
            return

        for state in TRANSITIONS[self.comm_state][self.goal_state]:
            try:
                self.comm_state = state
            except InvalidTransitionError:
                pass

    def update_on_result_status(self, goal_status: GoalStatus) -> bool:
        self.goal_state = GoalState(goal_status.status)
        if not self.comm_state.is_terminal:
            self.update_status(GoalStatusArray(status_list=[goal_status]))
            self.comm_state = CommState.DONE
            return True
        return False


class InvalidTransitionError(Exception):
    pass


class InvalidTransition(tuple):
    def __iter__(self) -> NoReturn:
        raise InvalidTransitionError()


TRANSITIONS = {
    CommState.WAITING_FOR_GOAL_ACK: {
        GoalState.PENDING: (CommState.PENDING,),
        GoalState.ACTIVE: (CommState.ACTIVE,),
        GoalState.REJECTED: (CommState.PENDING, CommState.WAITING_FOR_RESULT),
        GoalState.RECALLING: (CommState.PENDING, CommState.RECALLING),
        GoalState.RECALLED: (CommState.PENDING, CommState.WAITING_FOR_RESULT),
        GoalState.PREEMPTED: (
            CommState.ACTIVE,
            CommState.PREEMPTING,
            CommState.WAITING_FOR_RESULT,
        ),
        GoalState.SUCCEEDED: (CommState.ACTIVE, CommState.WAITING_FOR_RESULT),
        GoalState.ABORTED: (CommState.ACTIVE, CommState.WAITING_FOR_RESULT),
        GoalState.PREEMPTING: (CommState.ACTIVE, CommState.PREEMPTING),
    },
    CommState.PENDING: {
        GoalState.PENDING: (),
        GoalState.ACTIVE: (CommState.ACTIVE,),
        GoalState.REJECTED: (CommState.WAITING_FOR_RESULT,),
        GoalState.RECALLING: (CommState.RECALLING,),
        GoalState.RECALLED: (CommState.RECALLING, CommState.WAITING_FOR_RESULT),
        GoalState.PREEMPTED: (
            CommState.ACTIVE,
            CommState.PREEMPTING,
            CommState.WAITING_FOR_RESULT,
        ),
        GoalState.SUCCEEDED: (CommState.ACTIVE, CommState.WAITING_FOR_RESULT),
        GoalState.ABORTED: (CommState.ACTIVE, CommState.WAITING_FOR_RESULT),
        GoalState.PREEMPTING: (CommState.ACTIVE, CommState.PREEMPTING),
    },
    CommState.ACTIVE: {
        GoalState.PENDING: InvalidTransition(),
        GoalState.ACTIVE: (),
        GoalState.REJECTED: InvalidTransition(),
        GoalState.RECALLING: InvalidTransition(),
        GoalState.RECALLED: InvalidTransition(),
        GoalState.PREEMPTED: (CommState.PREEMPTING, CommState.WAITING_FOR_RESULT),
        GoalState.SUCCEEDED: (CommState.WAITING_FOR_RESULT,),
        GoalState.ABORTED: (CommState.WAITING_FOR_RESULT,),
        GoalState.PREEMPTING: (CommState.PREEMPTING,),
    },
    CommState.WAITING_FOR_RESULT: {
        GoalState.PENDING: InvalidTransition(),
        GoalState.ACTIVE: (),
        GoalState.REJECTED: (),
        GoalState.RECALLING: InvalidTransition(),
        GoalState.RECALLED: (),
        GoalState.PREEMPTED: (),
        GoalState.SUCCEEDED: (),
        GoalState.ABORTED: (),
        GoalState.PREEMPTING: InvalidTransition(),
    },
    CommState.WAITING_FOR_CANCEL_ACK: {
        GoalState.PENDING: (),
        GoalState.ACTIVE: (),
        GoalState.REJECTED: (CommState.WAITING_FOR_RESULT,),
        GoalState.RECALLING: (CommState.RECALLING,),
        GoalState.RECALLED: (CommState.RECALLING, CommState.WAITING_FOR_RESULT),
        GoalState.PREEMPTED: (CommState.PREEMPTING, CommState.WAITING_FOR_RESULT),
        GoalState.SUCCEEDED: (CommState.PREEMPTING, CommState.WAITING_FOR_RESULT),
        GoalState.ABORTED: (CommState.PREEMPTING, CommState.WAITING_FOR_RESULT),
        GoalState.PREEMPTING: (CommState.PREEMPTING,),
    },
    CommState.RECALLING: {
        GoalState.PENDING: InvalidTransition(),
        GoalState.ACTIVE: InvalidTransition(),
        GoalState.REJECTED: (CommState.WAITING_FOR_RESULT,),
        GoalState.RECALLING: (),
        GoalState.RECALLED: (CommState.WAITING_FOR_RESULT,),
        GoalState.PREEMPTED: (CommState.PREEMPTING, CommState.WAITING_FOR_RESULT),
        GoalState.SUCCEEDED: (CommState.PREEMPTING, CommState.WAITING_FOR_RESULT),
        GoalState.ABORTED: (CommState.PREEMPTING, CommState.WAITING_FOR_RESULT),
        GoalState.PREEMPTING: (CommState.PREEMPTING,),
    },
    CommState.PREEMPTING: {
        GoalState.PENDING: InvalidTransition(),
        GoalState.ACTIVE: InvalidTransition(),
        GoalState.REJECTED: InvalidTransition(),
        GoalState.RECALLING: InvalidTransition(),
        GoalState.RECALLED: InvalidTransition(),
        GoalState.PREEMPTED: (CommState.WAITING_FOR_RESULT,),
        GoalState.SUCCEEDED: (CommState.WAITING_FOR_RESULT,),
        GoalState.ABORTED: (CommState.WAITING_FOR_RESULT,),
        GoalState.PREEMPTING: (),
    },
    CommState.DONE: {
        GoalState.PENDING: InvalidTransition(),
        GoalState.ACTIVE: InvalidTransition(),
        GoalState.REJECTED: (),
        GoalState.RECALLING: InvalidTransition(),
        GoalState.RECALLED: (),
        GoalState.PREEMPTED: (),
        GoalState.SUCCEEDED: (),
        GoalState.ABORTED: (),
        GoalState.PREEMPTING: InvalidTransition(),
    },
}
