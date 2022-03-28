#!/usr/bin/env python

from distutils.core import setup

from catkin_pkg.python_setup import generate_distutils_setup

setup(
    **generate_distutils_setup(
        packages=[
            "aioros",
            "aioros._node",
            "aioros._node._action",
            "aioros._node._tcpros",
            "aioros._utils",
            "aioros.abc",
            "aioros.master",
            "aioros.tf2",
            "aioros.xmlrpc",
            "aioros.xmlrpc._protocol",
        ],
        package_data={
            "aioros": ["py.typed"],
            "aioros.tf2": ["_buffer_core.pyi", "_linear_math.pyi"],
            "aioros.xmlrpc._protocol": ["xmlrpc.rng"],
        },
    )
)
