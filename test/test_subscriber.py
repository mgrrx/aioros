#!/usr/bin/python3

import aioros

from std_msgs.msg import String


async def setup(nh: aioros.NodeHandle):
    await nh.create_subscription('chatter', String, print)


if __name__ == '__main__':
    aioros.run_forever(setup, 'test_subscriber')
