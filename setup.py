#!/usr/bin/env python

from distutils.core import setup

from catkin_pkg.python_setup import generate_distutils_setup

setup(
    **generate_distutils_setup(
        packages=[
            "aioros",
            "aioros._node",
            "aioros._node._tcpros",
            "aioros._utils",
            "aioros.abc",
            "aioros.master",
            "aioros.xmlrpc",
            "aioros.xmlrpc._protocol",
        ],
        package_dir={"": "src/"},
        package_data={
            "aioros": ["py.typed"],
            "aioros.xmlrpc._protocol": ["xmlrpc.rng"],
        },
    )
)
