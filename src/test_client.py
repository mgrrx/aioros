#!/usr/bin/python3
import asyncio

import random
from aioros.node_handle import NodeHandle
from rospy_tutorials.srv import AddTwoInts
from rospy_tutorials.srv import AddTwoIntsRequest


loop = asyncio.get_event_loop()


async def main(n):
    await n.init()

    c = await n.create_client('add_two_ints', AddTwoInts, persistent=True)
    while True:
        result = await c.call(AddTwoIntsRequest(random.randint(1, 1000),
                                                random.randint(1, 1000)))
        print(result.sum)


if __name__ == "__main__":
    n = NodeHandle('test_client')
    try:
        loop.run_until_complete(main(n))
    except KeyboardInterrupt as e:
        print("Received KeyboardInterrupt, shutting down...")
        loop.run_until_complete(n.close())
        loop.stop()
        loop.run_until_complete(loop.shutdown_asyncgens())
    else:
        loop.run_until_complete(n.close())
