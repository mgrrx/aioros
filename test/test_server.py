#!/usr/bin/python3

import aioros

from rospy_tutorials.srv import AddTwoInts
from rospy_tutorials.srv import AddTwoIntsResponse


async def setup(nh: aioros.NodeHandle):
    await nh.create_service(
        'add_two_ints',
        AddTwoInts,
        lambda request: AddTwoIntsResponse(request.a + request.b))


if __name__ == '__main__':
    aioros.run_forever(setup, 'add_two_ints_server')
