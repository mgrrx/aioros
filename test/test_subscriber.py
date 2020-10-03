#!/usr/bin/python3
import aioros

from std_msgs.msg import String


async def main(nh: aioros.NodeHandle):
    async with nh.create_subscription('chatter', String) as subscription:
        async for msg in subscription:
            print(msg)


if __name__ == '__main__':
    aioros.run_until_complete(main, 'test_subscriber')
