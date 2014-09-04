Changes LXC Wrapper
-------------------

Handles automating launching containers for running Changes builds.

Requirements
============

- LXC 1.0
- AWS CLI Tools (for snapshot integration)

Development
===========

Provision the Vagrant VM:

    $ vagrant up --provision

This will install various system dependencies as well as setting up a symlink
for the ``changes-lxc-wrapper`` package.

Run a Build
===========

Provision and use ubuntu minimal install::

    $ changes-lxc-wrapper

.. note:: You will likely need to run these commands as root, and assuming you're
          passing AWS credentials via environment variables you'll want to run
          everything with `sudo -E`.

Use a snapshot rather than bootstrapping a fresh container, add ``--snapshot``::

    $ changes-lxc-wrapper \
    	--snapshot 65072990854348a1a80c94bb0b6089e5

When running in production, you'll be passing two values which will automatically
specify the project and snapshot for you::

    $ changes-lxc-wrapper \
        --api-url https://changes.example.com/api/0/ \
        --jobstep-id 65072990854348a1a80c94bb0b6089e5


Creating a snapshot
===================

This will create a ``meta.tar.xz`` and a ``rootfs.tar.xz``::

    $ changes-lxc-wrapper \
    	--snapshot 65072990854348a1a80c94bb0b6089e5 \
    	--save-snapshot \
    	--clean

To rebuild the cached Ubuntu minimal install base rootfs, pass ``--flush-cache``

.. note:: You **must** use --clean if you're passing a --snapshot (explicit snapshot name)

Run Command
===========

Simply launch a container and run a command::

    $ changes-lxc-wrapper \
    	-- echo "hello world"


Running the Sample Build
========================

Assuming you're using the VM, login and jump into /vagrant/. Once there, you can run the following:

    $ sudo ./changes-lxc-wrapper --script examples/changes
