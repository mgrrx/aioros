#!/usr/bin/env python3

import logging
from typing import Optional

import anyio
from actionlib_tutorials.msg import (
    FibonacciAction,
    FibonacciFeedback,
    FibonacciGoal,
    FibonacciResult,
)

import aioros
from aioros.abc import ActionServerGoalHandle

logger = logging.getLogger("aioros")


async def server_cb(
    goal_handle: ActionServerGoalHandle[FibonacciGoal, FibonacciFeedback],
) -> Optional[FibonacciResult]:
    # Task
    result = FibonacciResult()
    result.sequence = [0, 1]
    try:
        for i in range(1, goal_handle.goal.order):
            result.sequence.append(result.sequence[i] + result.sequence[i - 1])
            await goal_handle.send_feedback(FibonacciFeedback(result.sequence))
            await anyio.sleep(1.0)
        return result
    except anyio.get_cancelled_exc_class():
        # goal got preempted
        await goal_handle.confirm_preemption()
        raise


async def main() -> None:
    async with aioros.init_node("test_action_server"):
        await aioros.create_action_server(
            "fibonacci", FibonacciAction, server_cb
        ).serve()


if __name__ == "__main__":
    anyio.run(main)
