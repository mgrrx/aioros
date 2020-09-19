#!/usr/bin/python3

import asyncio
import aioros
from std_msgs.msg import String


def on_peer_connect(node_name):
    print('node', node_name, 'connected')
    return String(data=f'Hi {node_name}')


def on_peer_disconnect(node_name):
    print('node', node_name, 'disconnected')


async def setup(nh: aioros.NodeHandle):
    pub: aioros.Publisher = await nh.create_publisher(
        'chatter',
        String,
        on_peer_connect=on_peer_connect,
        on_peer_disconnect=on_peer_disconnect)
    nh.create_timer(1.0, partial(pub.publish, String(data='test')))


if __name__ == '__main__':
    aioros.run_forever(setup, 'test_publisher')
