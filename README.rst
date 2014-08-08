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

    $ changes-lxc-wrapper \
    	--project foo

.. note:: You will likely need to run these commands as root, and assuming you're
          passing AWS credentials via environment variables you'll want to run
          everything with `sudo -E`.

Use a snapshot rather than bootstrapping a fresh container, add ``--snapshot``::

    $ changes-lxc-wrapper \
    	--project foo \
    	--snapshot 65072990854348a1a80c94bb0b6089e5

Creating a snapshot
===================

This will create a ``meta.tar.xz`` and a ``rootfs.tar.xz``::

    $ changes-lxc-wrapper \
    	--project foo \
    	--snapshot 65072990854348a1a80c94bb0b6089e5 \
    	--save-snapshot \
    	--clean

To rebuild the cached Ubuntu minimal install base rootfs, pass ``--flush-cache``

.. note:: You **must** use --clean if you're passing a --snapshot (explicit snapshot name)

Run Command
===========

Simply launch a container and run a command::

    $ changes-lxc-wrapper \
    	--project foo \
    	-- echo "hello world"
