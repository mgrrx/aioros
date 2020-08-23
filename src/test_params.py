#!/usr/bin/python3
import asyncio

from aioros.node_handle import NodeHandle


async def main(n):
    await n.init(xmlrpc_port=40000, tcpros_port=50000)
    try:
        print("delete")
        print(await n.delete_param("/test"))
    except KeyError:
        pass

    print("set")
    print(await n.set_param("/test", 1))
    print("get")
    print(await n.get_param("/test"))

    print(await n.has_param("/rosdistro"))
    print(await n.has_param("foo"))
    print(await n.get_param_names())


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    n = NodeHandle('test')
    try:
        loop.run_until_complete(main(n))
    except KeyboardInterrupt as e:
        print("Received KeyboardInterrupt, shutting down...")
        loop.run_until_complete(n.close())
        loop.stop()
        loop.run_until_complete(loop.shutdown_asyncgens())
    else:
        loop.run_until_complete(n.close())
