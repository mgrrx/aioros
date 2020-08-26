#!/usr/bin/python3

import aioros

from rospy_tutorials.srv import AddTwoInts
from rospy_tutorials.srv import AddTwoIntsRequest
from rospy_tutorials.srv import AddTwoIntsResponse


def cb(request: AddTwoIntsRequest) -> AddTwoIntsResponse:
    return AddTwoIntsResponse(request.a + request.b)


async def setup(n):
    await n.create_service('add_two_ints', AddTwoInts, cb)


if __name__ == "__main__":
    aioros.run_forever(setup, "test_server")
