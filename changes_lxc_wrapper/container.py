import lxc
import os
import shutil
import socket
import subprocess

from time import time
from uuid import uuid4

SNAPSHOT_CACHE = '/var/cache/lxc/download'


class Container(lxc.Container):
    def __init__(self, name, release=None, snapshot=None, validate=True,
                 s3_bucket=None, *args, **kwargs):
        self.snapshot = snapshot
        self.release = release
        self.s3_bucket = s3_bucket

        # This will be the hostname inside the container
        self.utsname = snapshot or str(uuid4())

        self.validate = validate

        # Randomize container name to prevent clobbering
        super().__init__(name, *args, **kwargs)

    @property
    def rootfs(self):
        """ May be real path or overlayfs:base-dir:delta-dir """
        return self.get_config_item('lxc.rootfs').split(':')[-1]

    def get_home_dir(self, user):
        return '/root' if user == 'root' else '/home/{}'.format(user)

    def get_image_path(self, snapshot):
        return "{dist}/{release}/{arch}/{snapshot}".format(
            dist='ubuntu',
            arch='amd64',
            release=self.release,
            snapshot=snapshot,
        )

    def ensure_image_cached(self, snapshot):
        """
        To avoid complexity of having a sort-of public host, and to ensure we
        can just instead easily store images on S3 (or similar) we attempt to
        sync images in a similar fashion to the LXC image downloader. This means
        that when we attempt to run the image, the download will look for our
        existing cache (that we've correctly populated) and just reference the
        image from there.
        """
        path = self.get_image_path(snapshot)

        local_path = "/var/cache/lxc/download/{}".format(path)
        # list of files required to avoid network hit
        file_list = [
            'rootfs.tar.xz',
            'config',
            'snapshot_id',
        ]
        if all(os.path.exists(os.path.join(local_path, f)) for f in file_list):
            return

        assert self.s3_bucket, 'Missing S3 bucket configuration'

        if not os.path.exists(local_path):
            os.makedirs(local_path)

        remote_path = "s3://{}/{}".format(self.s3_bucket, path)

        print("==> Downloading image {}".format(snapshot))
        start = time()
        assert not subprocess.call(
            ["aws", "s3", "sync", remote_path, local_path],
            env=os.environ.copy(),
        ), "Failed to download image {}".format(remote_path)
        stop = time()
        print("==> Image {} downloaded in {}s".format(
            snapshot, int((stop - start) * 100) / 100))

    def upload_image(self, snapshot):
        assert self.s3_bucket, 'Missing S3 bucket configuration'

        path = self.get_image_path(snapshot)
        local_path = "{}/{}".format(SNAPSHOT_CACHE, path)
        remote_path = "s3://{}/{}".format(self.s3_bucket, path)

        start = time()
        print("==> Uploading image {}".format(snapshot))
        assert not subprocess.call(
            ["aws", "s3", "sync", local_path, remote_path],
            env=os.environ.copy(),
        ), "Failed to upload image {}".format(remote_path)
        stop = time()
        print("==> Image {} uploaded in {}s".format(
            snapshot, int((stop - start) * 100) / 100))

    def run_script(self, script_path, **kwargs):
        """
        Runs a local script within the container.
        """
        assert os.path.isfile(script_path), "Cannot find local script {}".format(script_path)
        new_name = os.path.join("tmp", "script-{}".format(uuid4().hex))
        print("==> Writing local script {} as /{}".format(script_path, new_name))
        shutil.copy(script_path, os.path.join(self.rootfs, new_name))
        script_path = '/' + new_name
        assert self.run(['chmod', '0755', script_path], quiet=True) == 0
        assert self.run([script_path], **kwargs) == 0

    def run(self, cmd, cwd=None, env=None, user='root', quiet=False):
        assert self.running, "Cannot run cmd in non-RUNNING container"

        home_dir = self.get_home_dir(user)
        if cwd is None:
            cwd = home_dir
        else:
            cwd = '/'

        def run(args):
            cmd, cwd, env = args

            new_env = {
                # TODO(dcramer): HOME is pretty hacky here
                'USER': user,
                'HOME': home_dir,
                'PWD': cwd,
                'DEBIAN_FRONTEND': 'noninteractive',
                'LXC_NAME': self.name,
                'HOST_HOSTNAME': socket.gethostname(),
                'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
            }
            if env:
                new_env.update(env)

            if user != 'root':
                cmd = ['sudo', '-EHu', user] + cmd

            return subprocess.call(cmd, cwd=cwd, env=new_env)

        if not quiet:
            print("==> Running: {}".format(cmd))

        ret_code = self.attach_wait(run, (cmd, cwd, env), env_policy=lxc.LXC_ATTACH_CLEAR_ENV)

        if not quiet:
            print("==> Command exited: {}".format(ret_code))

        return ret_code

    def install(self, pkgs):
        assert self.run(["apt-get", "update", "-y", "--fix-missing"]) == 0, \
            "Failed updating apt resources"
        return self.run(["apt-get", "install", "-y", "--force-yes"] + pkgs)

    def setup_sudoers(self, user='ubuntu'):
        sudoers_path = os.path.join(self.rootfs, 'etc', 'sudoers')

        with open(sudoers_path, 'w') as fp:
            fp.write('Defaults    env_reset\n')
            fp.write('Defaults    !requiretty\n\n')
            fp.write('# Allow all sudoers.\n')
            fp.write('ALL  ALL=(ALL) NOPASSWD:ALL'.format(user))

        subprocess.call(['chmod', '0440', sudoers_path])

        return True

    def launch(self, pre=None, post=None, clean=False, flush_cache=False):
        """ Launch a container

        If we have a snapshot, attempt to download and extract the image to clone.
        Without a snapshot, generate a container from ubuntu minimal install.
        """

        if self.snapshot and not clean:
            if self.snapshot not in lxc.list_containers():
                self.ensure_image_cached(snapshot=self.snapshot)

                create_args = [
                    '--dist', 'ubuntu',
                    '--release', self.release,
                    '--arch', 'amd64',
                    '--variant', self.snapshot,
                ]
                if not self.validate:
                    create_args.extend(['--no-validate'])

                base = lxc.Container(self.snapshot)
                assert base.create('download', args=create_args), (
                    "Failed to load cached image: {}".format(self.snapshot))
            else:
                base = lxc.Container(self.snapshot)

            print("==> Overlaying container: {}".format(self.snapshot))
            assert base.clone(self.name, flags=lxc.LXC_CLONE_KEEPNAME | lxc.LXC_CLONE_SNAPSHOT), (
                "Failed to clone: {}".format(self.snapshot))
            assert self.load_config(), "Unable to reload container config"
        else:
            create_args = [
                '--release', self.release,
                '--arch', 'amd64',
            ]
            if flush_cache:
                create_args.extend(['--flush-cache'])

            print("==> Creating container")
            assert self.create('ubuntu', args=create_args), \
                "Failed to create container. Try running this command as root."

        if pre:
            pre_env = dict(os.environ, LXC_ROOTFS=self.rootfs, LXC_NAME=self.name)
            subprocess.check_call(pre, cwd=self.rootfs, env=pre_env)

        # XXX: More or less disable apparmor
        assert self.set_config_item("lxc.aa_profile", "unconfined")
        # Allow loop/squashfs in container
        assert self.append_config_item('lxc.cgroup.devices.allow', 'c 10:137 rwm')
        assert self.append_config_item('lxc.cgroup.devices.allow', 'b 6:* rwm')

        print("==> Starting container")
        assert self.start(), "Failed to start base container"

        print("==> Waiting for container to startup networking")
        assert self.get_ips(family='inet', timeout=30), "Failed to connect to container"

        print("==> Install ca-certificates")
        assert self.install(["ca-certificates"]) == 0

        print("==> Setting up sudoers")
        assert self.setup_sudoers(), "Failed to setup sudoers"

        if post:
            # Naively check if trying to run a file that exists outside the container
            self.run_script(post)

    def create_image(self):
        snapshot = self.snapshot or str(uuid4())
        dest = "/var/cache/lxc/download/{}".format(
            self.get_image_path(snapshot))

        print("==> Stopping container")
        self.stop()

        assert self.wait('STOPPED', timeout=30)

        print("==> Saving snapshot to {}".format(dest))
        if not os.path.exists(dest):
            os.makedirs(dest)

        print("==> Creating metadata")
        with open(os.path.join(dest, "config"), "w") as fp:
            fp.write("lxc.include = LXC_TEMPLATE_CONFIG/ubuntu.common.conf\n")
            fp.write("lxc.arch = x86_64\n")

        rootfs_txz = os.path.join(dest, "rootfs.tar.xz")

        print("==> Creating rootfs.tar.xz")
        subprocess.check_call(["tar", "-Jcf", rootfs_txz,
                               "-C", self.get_config_item('lxc.rootfs'),
                               "."])

        with open(os.path.join(dest, "snapshot_id"), 'w') as fp:
            fp.write(self.utsname)

        return snapshot

    def destroy(self, timeout=-1):
        if not self.defined:
            print("==> No container to destroy")
            return

        if self.running:
            print("==> Container is running, stop it first")
            self.stop()
            print("==> Wait for container to stop")
            self.wait('STOPPED', timeout=timeout)

        print("==> Destroying container")
        super().destroy()
