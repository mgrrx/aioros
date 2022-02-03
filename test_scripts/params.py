#!/usr/bin/python3

"""
from aioros import NodeHandle


async def main(nh: NodeHandle):
    try:
        print("delete")
        print(await nh.delete_param("/test"))
    except KeyError:
        pass

    print("set")
    print(await nh.set_param("/test", 1))
    print("get")
    print(await nh.get_param("/test"))

    print(await nh.has_param("/rosdistro"))
    print(await nh.has_param("foo"))
    print(await nh.get_param_names())


if __name__ == "__main__":
    NodeHandle.run("test_params", main)

"""
