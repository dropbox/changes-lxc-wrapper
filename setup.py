#!/usr/bin/env python3
"""
changes-lxc-wrapper
===================

:copyright: (c) 2014 Dropbox, Inc.
"""

from setuptools import setup, find_packages

tests_require = [
    'coverage',
    'mock>=1.0.1,<1.1.0',
    'pytest>=2.6.1,<2.7.0',
]

install_requires = [
    'raven>=5.0.0,<5.1.0',
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
            'changes-lxc = changes_lxc_wrapper.cli.helper:main',
            'changes-lxc-wrapper = changes_lxc_wrapper.cli.wrapper:main',
            'changes-snapshot-manager = changes_lxc_wrapper.cli.manager:main',
        ],
    },
    include_package_data=True,
    classifiers=[
        '__DO NOT UPLOAD__',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
)
