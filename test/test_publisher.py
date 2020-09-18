#!/usr/bin/python3

import asyncio
import aioros
from std_msgs.msg import String


def on_peer_connect(node_name):
    print('node', node_name, 'connected')
    return String(data=f'Hi {node_name}')


def on_peer_disconnect(node_name):
    print('node', node_name, 'disconnected')


async def main(nh: aioros.NodeHandle):
    pub: aioros.Publisher = await nh.create_publisher(
        'chatter',
        String,
        on_peer_connect=on_peer_connect,
        on_peer_disconnect=on_peer_disconnect)
    msg = String(data='test')

    while True:
        print(msg)
        pub.publish(msg)
        await asyncio.sleep(1)
    return 0


if __name__ == '__main__':
    aioros.run_until_complete(main, 'test_publisher')
