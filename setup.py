#!/usr/bin/env python3
"""
changes-lxc-wrapper
===================

:copyright: (c) 2014 Dropbox, Inc.
"""

from setuptools import setup, find_packages

tests_require = [
    'mock>=1.0.1,<1.1.0',
    'pytest>=2.6.1,<2.7.0',
]

install_requires = [
    'raven>=4.0.4,<4.1.0',
]

setup(
    name='changes-lxc-wrapper',
    version='0.1.0',
    author='Dropbox, Inc',
    description='',
    long_description=__doc__,
    packages=find_packages(),
    zip_safe=False,
    install_requires=install_requires,
    extras_require={'tests': tests_require},
    tests_require=tests_require,
    entry_points={
        'console_scripts': [
            'changes-lxc-wrapper = changes_lxc_wrapper.cli.wrapper:main',
        ],
    },
    include_package_data=True,
    classifiers=[
        '__DO NOT UPLOAD__',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
)