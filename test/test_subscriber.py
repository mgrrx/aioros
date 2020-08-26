#!/usr/bin/python3

import aioros

from std_msgs.msg import String


async def cb(msg):
    print("cb", msg)


async def cb2(msg):
    print("cb2", msg)


async def setup(n):
    await n.create_subscription('blubb', String, cb)
    await n.create_subscription('blubb', String, cb2)


if __name__ == "__main__":
    aioros.run_forever(setup, 'test_subscriber')
