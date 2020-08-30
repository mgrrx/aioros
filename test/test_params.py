#!/usr/bin/python3

import asyncio

import aioros


def sync_cb(key, value):
    print("sync", key, value)


async def async_cb(key, value):
    print("async", key, value)


async def main(node_handle: aioros.NodeHandle):
    try:
        print("delete")
        print(await node_handle.delete_param("/test"))
    except KeyError:
        pass

    print("set")
    print(await node_handle.set_param("/test", 1))
    print("get")
    print(await node_handle.get_param("/test"))

    print(await node_handle.has_param("/rosdistro"))
    print(await node_handle.has_param("foo"))
    print(await node_handle.get_param_names())
    value1, c1 = await node_handle.subscribe_param("/bla", sync_cb)
    value2, c2 = await node_handle.subscribe_param("/bla", async_cb)
    print("initial value1", value1)
    print("initial value2", value2)
    print(node_handle.get_time())
    await asyncio.sleep(30)


if __name__ == "__main__":
    aioros.run_until_complete(main, 'test_params')
