#!/usr/bin/python3
import asyncio

from aioros.node_handle import NodeHandle
from std_msgs.msg import String


loop = asyncio.get_event_loop()


async def cb(msg):
    print("cb", msg)


async def cb2(msg):
    print("cb2", msg)


async def main(n):
    await n.init()
    await n.create_subscription('blubb', String, cb)
    await n.create_subscription('blubb', String, cb2)


if __name__ == "__main__":
    n = NodeHandle('test_subscriber')
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
