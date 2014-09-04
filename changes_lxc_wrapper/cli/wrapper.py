#!/usr/bin/env python3

import argparse
import logging
import sys

from raven.handlers.logging import SentryHandler
from threading import Thread
from uuid import UUID

from ..api import ChangesApi
from ..container import Container
from ..log_reporter import LogReporter


DESCRIPTION = "LXC Wrapper for running Changes jobs"

DEFAULT_RELEASE = 'precise'


class WrappedOutput(object):
    def __init__(self, stream, reporter):
        self.stream = stream
        self.reporter = reporter

    def write(self, chunk):
        self.stream.write(chunk)
        self.reporter.write(chunk)


class WrapperCommand(object):
    def __init__(self, argv=None):
        self.argv = argv
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def get_arg_parser(self):
        parser = argparse.ArgumentParser(description=DESCRIPTION)
        parser.add_argument('--snapshot', '-s', type=UUID,
                            help="Snapshot ID of the container")
        parser.add_argument('--release', '-r',
                            help="Ubuntu release (default: {})".format(DEFAULT_RELEASE))
        parser.add_argument('--keep', action='store_true', default=False,
                            help="Don't destroy the container after running cmd/build")
        parser.add_argument('--no-validate', action='store_false', default=True, dest='validate',
                            help="Don't validate downloaded images")
        parser.add_argument('--save-snapshot', action='store_true', default=False,
                            help="Create an image from this container")
        parser.add_argument('--clean', action='store_true', default=False,
                            help="Use a fresh container from Ubuntu minimal install")
        parser.add_argument('--flush-cache', action='store_true', default=False,
                            help="Rebuild Ubuntu minimal install cache")
        parser.add_argument('--api-url',
                            help="API URL to Changes (i.e. https://changes.example.com/api/0/)")
        parser.add_argument('--jobstep-id',
                            help="Jobstep ID for Changes")
        parser.add_argument('--pre-launch',
                            help="Command to run before container is launched")
        parser.add_argument('--post-launch',
                            help="Command to run after container is launched")
        parser.add_argument('--user', '-u', default='ubuntu',
                            help="User to run command (or script) as")
        parser.add_argument('--script',
                            help="Script to execute as command")
        parser.add_argument('--s3-bucket',
                            help="S3 Bucket to store/fetch images from")
        parser.add_argument('--log-level', default='WARN')
        parser.add_argument('cmd', nargs=argparse.REMAINDER,
                            help="Command to run inside the container")
        return parser

    def configure_logging(self, level):
        logging.basicConfig(level=level)

        root = logging.getLogger()
        root.addHandler(SentryHandler())

    def patch_system_logging(self, reporter):
        sys.stdout = WrappedOutput(sys.stdout, reporter)
        sys.stderr = WrappedOutput(sys.stderr, reporter)

    def run(self):
        parser = self.get_arg_parser()
        args = parser.parse_args(self.argv)

        try:
            args.cmd.remove('--')
        except ValueError:
            pass

        self.configure_logging(args.log_level)

        if args.api_url:
            api = ChangesApi(args.api_url)
        else:
            assert not args.jobstep_id, "jobstep_id passed without api_url"
            api = None

        jobstep_id = args.jobstep_id

        # setup log capturing
        if jobstep_id:
            reporter = LogReporter(api, args.jobstep_id)
            reporter_thread = Thread(target=reporter.process)
            reporter_thread.start()
            self.patch_system_logging(reporter)
        else:
            reporter_thread = None

        if jobstep_id:
            # fetch build information to set defaults for things like snapshot
            # TODO(dcramer): make this support a small amount of downtime
            # TODO(dcramer): make this verify the snapshot
            resp = api.get_jobstep(args.jobstep_id)
            assert resp['status']['id'] != 'finished', \
                'JobStep already marked as finished, aborting.'

            release = resp['data'].get('release') or DEFAULT_RELEASE

            # If we're expected a snapshot output we need to override
            # any snapshot parameters, and also ensure we're creating a clean
            # image
            if resp['expectedSnapshot']:
                snapshot = str(UUID(resp['expectedSnapshot']['id']))
                save_snapshot = True
                clean = True

            else:
                if resp['snapshot']:
                    snapshot = str(UUID(resp['snapshot']['id']))
                else:
                    snapshot = None
                save_snapshot = False
                clean = False

        else:
            clean = args.clean
            snapshot = str(args.snapshot) if args.snapshot else None
            save_snapshot = args.save_snapshot
            release = args.release or DEFAULT_RELEASE

        assert clean or not (save_snapshot and snapshot), \
            "You cannot create a snapshot from an existing snapshot"

        container = Container(
            snapshot=snapshot,
            release=release,
            validate=args.validate,
            s3_bucket=args.s3_bucket,
        )

        try:
            if args.jobstep_id:
                api.update_jobstep(args.jobstep_id, {"status": "in_progress"})

            container.launch(args.pre_launch, args.post_launch, clean, args.flush_cache)

            # TODO(dcramer): we should assert only one type of command arg is set
            if args.cmd:
                container.run(args.cmd, user=args.user)
            if args.script:
                container.run_script(args.script, user=args.user)
            if args.api_url and args.jobstep_id:
                container.run(['changes-client',
                               '--server', args.api_url,
                               '--jobstep_id', args.jobstep_id], user=args.user)
            if save_snapshot:
                snapshot = container.create_image()
                print("==> Snapshot saved: {}".format(snapshot))
                container.upload_image(snapshot=snapshot)

                api.update_snapshot_image(snapshot, {"status": "active"})
        except Exception as e:
            if args.jobstep_id:
                api.update_jobstep(args.jobstep_id, {"status": "finished", "result": "failed"})

                if save_snapshot:
                    api.update_snapshot_image(snapshot, {"status": "failed"})

            logging.exception(e)
            raise e
        finally:
            if args.jobstep_id:
                api.update_jobstep(args.jobstep_id, {"status": "finished"})

            if not args.keep:
                container.destroy()
            else:
                print("==> Container kept at {}".format(container.rootfs))
                print("==> SSH available via:")
                print("==>   $ sudo lxc-attach --name={}".format(container.name))

            if reporter_thread:
                reporter.close()
                reporter_thread.join()


def main():
    command = WrapperCommand()
    command.run()


if __name__ == '__main__':
    main()
