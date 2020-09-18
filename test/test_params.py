#!/usr/bin/python3

import asyncio

import aioros


def sync_cb(key, value):
    print('sync', key, value)


async def async_cb(key, value):
    print('async', key, value)


async def main(nh: aioros.NodeHandle):
    try:
        print('delete')
        print(await nh.delete_param('/test'))
    except KeyError:
        pass

    print('set')
    print(await nh.set_param('/test', 1))
    print('get')
    print(await nh.get_param('/test'))

    print(await nh.has_param('/rosdistro'))
    print(await nh.has_param('foo'))
    print(await nh.get_param_names())
    value1, callback1 = await nh.subscribe_param('/bla', sync_cb)
    value2, callback2 = await nh.subscribe_param('/bla', async_cb)
    print('initial value1', value1)
    print('initial value2', value2)
    print(nh.get_time())
    await asyncio.sleep(30)


if __name__ == '__main__':
    aioros.run_until_complete(main, 'test_params')
