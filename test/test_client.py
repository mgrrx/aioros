#!/usr/bin/python3

import random

import aioros

from rospy_tutorials.srv import AddTwoInts
from rospy_tutorials.srv import AddTwoIntsRequest
from rospy_tutorials.srv import AddTwoIntsResponse


async def main(nh: aioros.NodeHandle):
    client: aioros.Client = await nh.create_client(
        'add_two_ints',
        AddTwoInts,
        persistent=True)
    while True:
        result: AddTwoIntsResponse = await client.call(
            AddTwoIntsRequest(random.randint(1, 1000),
                              random.randint(1, 1000)))
        print(result.sum)


if __name__ == '__main__':
    aioros.run_until_complete(main, 'add_two_ints_client')
