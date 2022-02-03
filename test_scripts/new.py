import time

import aioros
import anyio
from aioros.abc import Node
from std_msgs.msg import String
from std_srvs.srv import SetBool, SetBoolRequest, SetBoolResponse


async def service_cb(request: SetBoolRequest) -> SetBoolResponse:
    msg = SetBoolResponse(message=str(request.data), success=True)
    return msg


async def publish(node: Node):
    async with node.create_publication("/foo", String, latched=True) as publisher:
        foo = 1
        while node.is_running():
            publisher.publish_soon(String(f"Some crap {foo}"))
            foo += 1
            await anyio.sleep(10.0)


async def subscribe(node: Node):
    async with node.create_subscription("/foo", String) as subscription:
        async for msg in subscription:
            print(msg)


async def main():
    async with aioros.init_node("some_node") as node:
        async with anyio.create_task_group() as tg:
            try:
                print(await node.get_param("foo"))
            except KeyError:
                print("no such param")
            print(await node.has_param("foo"))
            await node.set_param("bar", 123)
            print(await node.get_param("bar"))
            await node.delete_param("bar")
            print(await node.get_param_names())
            tg.start_soon(node.create_server("/foo", SetBool, service_cb).serve)
            tg.start_soon(publish, node)
            # tg.start_soon(subscribe, node)
            # async with node.create_client("/set_bool", SetBool) as client:
            #    result = await client.call(SetBoolRequest(data=True))
            #    print(result.success)
            #    print(result)
            print(aioros.get_time())
            await anyio.sleep(1000)


if __name__ == "__main__":
    anyio.run(main)
