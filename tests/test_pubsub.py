from typing import cast

import pytest
from std_msgs.msg import String

from aioros import init_node
from aioros._node._node import Node
from aioros.master import init_master

pytestmark = pytest.mark.anyio


async def test_pubsub() -> None:
    async with init_master() as master:
        async with cast(
            Node,
            init_node(
                "test_publisher",
                master_uri=master.xmlrpc_uri,
                register_signal_handler=False,
                configure_logging=False,
            ),
        ) as publisher_node, cast(
            Node,
            init_node(
                "test_subscriber",
                master_uri=master.xmlrpc_uri,
                register_signal_handler=False,
                configure_logging=False,
            ),
        ) as subscriber_node:
            async with publisher_node.create_publication(
                "/topic", String, latched=True
            ) as publisher, subscriber_node.create_subscription(
                "/topic", String
            ) as subscription:
                pub_reg = next(iter(master.registry.publications["/topic"]))
                sub_reg = next(iter(master.registry.subscriptions["/topic"]))
                assert pub_reg.caller_id == publisher_node.full_name
                assert sub_reg.caller_id == subscriber_node.full_name
                assert pub_reg.api == publisher_node.xmlrpc_uri
                assert sub_reg.api == subscriber_node.xmlrpc_uri
                publisher.publish_soon(String("Test"))
                async for msg in subscription:
                    print(msg)
                    assert msg.data == "Test"
                    break
                for i in range(10):
                    publisher.publish_soon(String(f"Test {i}"))
                i = 0
                async for msg in subscription:
                    print(msg)
                    assert msg.data == f"Test {i}"
                    i += 1
                    if i == 10:
                        break

            assert not master.registry.publications
            assert not master.registry.subscriptions
            assert not master.registry.nodes
            assert not master.registry.topic_types
