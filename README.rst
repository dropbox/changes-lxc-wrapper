Changes LXC Wrapper
-------------------

Handles automating launching containers for running Changes builds.

Requirements
============

- LXC 1.0
- AWS CLI Tools (for snapshot integration)

Run Changes Build
=================

Provision and use ubuntu minimal install::

    $ changes-lxc-wrapper --project foo --api-url changes.example.com/api/0 --jobstep-id 46a8ed3da0174eb0ba5522aab8595d89

.. note:: You will likely need to run these commands as root, and assuming you're
          passing AWS credentials via environment variables you'll want to run
          everything with `sudo -E`.

Use a snapshot rather than bootstrapping a fresh container, add ``--snapshot``::

    $ changes-lxc-wrapper --project foo --snapshot 0001 --api-url changes.example.com/api/0 --jobstep-id 46a8ed3da0174eb0ba5522aab8595d89

Or if you want to use a snapshot from another project, use ``--variant`` instead::

    $ changes-lxc-wrapper --project foo --variant bar-1000 --api-url changes.example.com/api/0 --jobstep-id 46a8ed3da0174eb0ba5522aab8595d89

Creating a snapshot
===================

This will create a ``meta.tar.xz`` and a ``rootfs.tar.xz``::

    $ changes-lxc-wrapper --project foo --variant 0002 --save-snapshot

To rebuild the cached Ubuntu minimal install base rootfs, pass ``--flush-cache``

Run Command
===========

Simply launch a container and run a command::

    $ changes-lxc-wrapper --project foo -- echo "hello world"
