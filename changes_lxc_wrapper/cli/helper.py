#!/usr/bin/env python3

import argparse
import logging

from raven.handlers.logging import SentryHandler
from uuid import UUID

from ..container import Container


DESCRIPTION = "LXC helper for running Changes jobs"

DEFAULT_RELEASE = 'precise'

DEFAULT_USER = 'ubuntu'


class CommandError(Exception):
    pass


class HelperCommand(object):
    def __init__(self, argv=None):
        self.argv = argv

    def get_arg_parser(self):
        parser = argparse.ArgumentParser(description=DESCRIPTION)
        parser.add_argument('--log-level', default='WARN')

        subparsers = parser.add_subparsers(dest='command')
        launch_parser = subparsers.add_parser('launch', help='Launch a new container')
        launch_parser.add_argument(
            'name', nargs='?', type=str,
            help="Container name")
        launch_parser.add_argument(
            '--snapshot', '-s', type=UUID,
            help="Snapshot ID of the container")
        launch_parser.add_argument(
            '--release', '-r', default=DEFAULT_RELEASE,
            help="Release")
        launch_parser.add_argument(
            '--no-validate', action='store_false', default=True, dest='validate',
            help="Don't validate downloaded images")
        launch_parser.add_argument(
            '--clean', action='store_true', default=False,
            help="Use a fresh container from Ubuntu minimal install")
        launch_parser.add_argument(
            '--flush-cache', action='store_true', default=False,
            help="Rebuild Ubuntu minimal install cache")
        launch_parser.add_argument(
            '--s3-bucket',
            help="S3 Bucket to store/fetch images from")
        launch_parser.add_argument(
            '--pre-launch',
            help="Command to run before container is launched")
        launch_parser.add_argument(
            '--post-launch',
            help="Command to run after container is launched")

        exec_parser = subparsers.add_parser('exec', help='Execute a command within a container')
        exec_parser.add_argument(
            '--user', '-u', default=DEFAULT_USER,
            help="User to run command as")
        exec_parser.add_argument(
            'name', nargs='?', type=str,
            help="Container name")
        exec_parser.add_argument(
            'cmd', nargs=argparse.REMAINDER,
            help="Command to run inside the container")

        exec_script_parser = subparsers.add_parser('exec-script', help='Execute a command within a container')
        exec_script_parser.add_argument(
            '--user', '-u', default=DEFAULT_USER,
            help="User to run command as")
        exec_script_parser.add_argument(
            'name', nargs='?', type=str,
            help="Container name")
        exec_script_parser.add_argument(
            'path', nargs=argparse.REMAINDER,
            help="Local script to run inside the container")

        destroy_parser = subparsers.add_parser('destroy', help='Destroy a running container')
        destroy_parser.add_argument(
            'name', nargs='?', type=str,
            help="Container name")

        return parser

    def configure_logging(self, level):
        logging.basicConfig(level=level)

        root = logging.getLogger()
        root.addHandler(SentryHandler())

    def run(self):
        parser = self.get_arg_parser()
        args = parser.parse_args(self.argv)

        try:
            args.cmd.remove('--')
        except (AttributeError, ValueError):
            pass

        self.configure_logging(args.log_level)

        if args.command == 'launch':
            self.run_launch(**vars(args))
        elif args.command == 'exec':
            self.run_exec(**vars(args))
        elif args.command == 'exec-script':
            self.run_exec_script(**vars(args))
        elif args.command == 'destroy':
            self.run_destroy(**vars(args))

    def run_launch(self, name, snapshot=None, release=DEFAULT_RELEASE,
                   validate=True, s3_bucket=None, clean=False,
                   flush_cache=False, pre_launch=None, post_launch=None,
                   **kwargs):

        container = Container(
            name=name,
            snapshot=snapshot,
            release=release,
            validate=validate,
            s3_bucket=s3_bucket,
        )

        container.launch(
            pre=pre_launch,
            post=post_launch,
            clean=clean,
            flush_cache=flush_cache,
        )
        print("==> Instance successfully launched as {}".format(name))

    def run_exec(self, name, cmd, user=DEFAULT_USER, **kwargs):
        container = Container(
            name=name,
        )

        container.run(cmd, user=user)

    def run_exec_script(self, name, path, user=DEFAULT_USER, **kwargs):
        container = Container(
            name=name,
        )

        container.run_script(path, user=user)

    def run_destroy(self, name, **kwargs):
        container = Container(
            name=name,
        )

        container.destroy()


def main():
    command = HelperCommand()
    command.run()


if __name__ == '__main__':
    main()
