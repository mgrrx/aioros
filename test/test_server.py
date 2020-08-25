#!/usr/bin/python3
import asyncio

from aioros.node_handle import NodeHandle
from rospy_tutorials.srv import AddTwoInts
from rospy_tutorials.srv import AddTwoIntsRequest
from rospy_tutorials.srv import AddTwoIntsResponse


loop = asyncio.get_event_loop()


def cb(request: AddTwoIntsRequest) -> AddTwoIntsResponse:
    return AddTwoIntsResponse(request.a + request.b)


async def main(n):
    await n.init()
    await n.create_service('add_two_ints', AddTwoInts, cb)


if __name__ == "__main__":
    n = NodeHandle('test_server')
    try:
        loop.run_until_complete(main(n))
        loop.run_forever()
    except KeyboardInterrupt as e:
        print("Received KeyboardInterrupt, shutting down...")
        loop.run_until_complete(n.close())
        loop.stop()
        loop.run_until_complete(loop.shutdown_asyncgens())
    else:
        loop.run_until_complete(n.close())
