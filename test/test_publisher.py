#!/usr/bin/python3
import asyncio

from aioros.node_handle import NodeHandle
from std_msgs.msg import String


loop = asyncio.get_event_loop()


def on_peer_connect(node_name):
    print("node", node_name, "connected")
    return String(data=f'Hi {node_name}')


def on_peer_disconnect(node_name):
    print("node", node_name, "disconnected")


async def main(n):
    await n.init()
    pub = await n.create_publisher(
        'blubb',
        String,
        on_peer_connect=on_peer_connect,
        on_peer_disconnect=on_peer_disconnect)
    pub2 = await n.create_publisher(
        'blubb',
        String,
        latch=True)
    await pub2.publish(String(data="latch"))
    while True:
        print("pub")
        await pub.publish(String(data="test"))
        await asyncio.sleep(0.1)


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
