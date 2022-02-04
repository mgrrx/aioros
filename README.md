# aioros
**aioros** is a anyio-based Python implementation of a [ROS](http://www.ros.org/) client library.

## Supported features

### Creating a Service Server

Creating a service is the easiest out of all the options. Just define a callback for each service call.
Let's use the std_srvs/SetBool service on the topic /set_bool.

```python
import anyio
from std_srvs.srv import SetBool, SetBoolRequest, SetBoolResponse

import aioros


async def service_cb(request: SetBoolRequest) -> SetBoolResponse:
    return SetBoolResponse(message=str(request.data), success=True)


async def main() -> None:
    async with aioros.init_node("some_server"):
        await aioros.create_server("/set_bool", SetBool, service_cb).serve()


if __name__ == "__main__":
    anyio.run(main)
```

### Service Client
Service clients can be created straight forward. Typing support for request and
response values is provided.

```python
import anyio
from std_srvs.srv import SetBool, SetBoolRequest

import aioros


async def main() -> None:
    async with aioros.init_node("set_bool_client"):
        async with aioros.create_client("/set_bool", SetBool) as client:
            result = await client.call(SetBoolRequest(True))
            print(result)

if __name__ == "__main__":
    anyio.run(main)
```

### Publisher
Publishing on a topic is also simple:
```python
from itertools import count

import anyio
from std_msgs.msg import String

import aioros


async def main() -> None:
    async with aioros.init_node("test_publisher"):
        async with aioros.create_publication("/chatter", String) as publisher:
            counter = count()
            while aioros.is_running():
                msg = String(f"Message {next(counter)}")
                await publisher.publish(msg)
                await anyio.sleep(1.)


if __name__ == "__main__":
    anyio.run(main)
```
### Subscriber
Subscriptions look a bit different than typical callback-based APIs as we use
async iterators instead:
```python
import anyio
from std_msgs.msg import String

import aioros


async def main() -> None:
    async with aioros.init_node("test_subscriber"):
        async with aioros.create_subscription("/chatter", String) as subscription:
            async for msg in subscription:
                print("Received", msg)


if __name__ == "__main__":
    anyio.run(main)
```
### Support for sim_time
Time as well as the ROS simulation time from /clock topic is supported out of the box.
```python
import anyio

import aioros


async def main() -> None:
    async with aioros.init_node("test_node"):
        while aioros.is_running():
            print(aioros.get_time())
            await anyio.sleep(1.)


if __name__ == "__main__":
    anyio.run(main)
```

### Own ROS Master implementation
aioros comes with its own ROS Master implementation. The goal was to have something
handy for testing. Let's look at the example below. Creating a pytest involving
the ROS Master and two nodes is as simple as this:

```python
async def test_pubsub() -> None:
    async with init_master() as master:
        async with init_node(
            "test_publisher",
            master_uri=master.xmlrpc_uri,
            register_signal_handler=False,
            configure_logging=False,
        ) as publisher_node, init_node(
            "test_subscriber",
            master_uri=master.xmlrpc_uri,
            register_signal_handler=False,
            configure_logging=False,
        ) as subscriber_node:
            async with publisher_node.create_publication(
                "/topic", String, latched=True
            ) as publisher, subscriber_node.create_subscription(
                "/topic", String
            ) as subscription:
                await publisher.publish(String("Test"))
                async for msg in subscription:
                    assert msg.data == "Test"
```

## Features which go beyond rospy
- Fully typed
- Unix Domain Socket transport as an optional feature (only works between aioros nodes)
- Multiple nodes within one executable

## TODO
- [ ] ROS-style logging via /rosout
- [ ] Expose buffer sizes of publisher and subscriber
- [ ] Rate and Timer
- [ ] More tests
- [ ] Documentation
- [ ] actionlib client
- [ ] actionlib server
- [ ] tf2 buffer client
- [ ] tf2 buffer support via own pybind11 wrapper due to https://github.com/ros/geometry2/blob/noetic-devel/tf2_py/src/tf2_py.cpp#L98-L102)
- [ ] GitHub actions
