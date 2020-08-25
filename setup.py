#!/usr/bin/env python

from distutils.core import setup
from catkin_pkg.python_setup import generate_distutils_setup


setup(**generate_distutils_setup(
    packages=[
        'aioros',
        'aioros.api',
        'aioros.tcpros',
    ],
    package_dir={'': 'src/'}
))
