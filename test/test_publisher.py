#!/usr/bin/python3

import asyncio
import aioros
from std_msgs.msg import String


def on_peer_connect(node_name):
    print("node", node_name, "connected")
    return String(data=f'Hi {node_name}')


def on_peer_disconnect(node_name):
    print("node", node_name, "disconnected")


async def main(n: aioros.NodeHandle):
    pub: aioros.Publisher = await n.create_publisher(
        'blubb',
        String,
        on_peer_connect=on_peer_connect,
        on_peer_disconnect=on_peer_disconnect)
    pub2: aioros.Publisher = await n.create_publisher(
        'blubb',
        String,
        latch=True)
    await pub2.publish(String(data="latch"))
    while True:
        print("pub")
        await pub.publish(String(data="test"))
        await asyncio.sleep(0.1)
    return 0


if __name__ == "__main__":
    aioros.run_until_complete(main, "test_server")
