#!/usr/bin/python3
import asyncio
from asyncio.queues import Queue
import aioros

from std_msgs.msg import String


async def main(nh: aioros.NodeHandle):
    loop = asyncio.get_running_loop()
    async with nh.create_subscription('chatter', String) as subscription1:
        async with nh.create_subscription('chatter2', String) as subscription2:
            while True:
                sub1_task = loop.create_task(subscription1.__anext__(), name="sub1")
                sub2_task = loop.create_task(subscription2.__anext__(), name="sub2")
                done, pending = await asyncio.wait(
                    {sub1_task, sub2_task},
                    timeout=1.0)
                print({task.get_name(): task.result() for task in done})
                for t in pending:
                    t.cancel()


if __name__ == '__main__':
    aioros.run_until_complete(main, 'test_subscriber')
