#!/usr/bin/env python3

import logging

import anyio
from actionlib_tutorials.msg import FibonacciAction, FibonacciGoal

import aioros

logger = logging.getLogger("aioros")


async def main() -> None:
    async with aioros.init_node("test_action_client"):
        async with aioros.create_action_client("fibonacci", FibonacciAction) as client:
            await client.wait_for_server()
            call = await client.send_goal(FibonacciGoal(order=5))
            async for feedback in call.feedback():
                print("Feedback", feedback)
            print("Result", await call.wait_for_result())


if __name__ == "__main__":
    anyio.run(main)
