#!/usr/bin/env python3

import argparse
import logging
import sys
import traceback

from raven.handlers.logging import SentryHandler
from threading import Thread
from time import sleep
from uuid import UUID

from ..api import ChangesApi
from ..container import Container
from ..heartbeat import Heartbeater
from ..log_reporter import LogReporter


DESCRIPTION = "LXC Wrapper for running Changes jobs"

DEFAULT_RELEASE = 'precise'


class CommandError(Exception):
    pass


class WrappedOutput(object):
    def __init__(self, stream, reporter):
        self.stream = stream
        self.reporter = reporter

    def write(self, chunk):
        self.stream.write(chunk)
        self.reporter.write(chunk)

    def flush(self):
        self.stream.flush()
        self.reporter.flush()


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

        if args.jobstep_id:
            return self.run_remote(args)
        return self.run_local(args)

    def run_local(self, args):
        """
        Run a local-only build (i.e. for testing).
        """
        snapshot = str(args.snapshot) if args.snapshot else None
        release = args.release or DEFAULT_RELEASE

        self.run_build_script(
            snapshot=snapshot,
            release=release,
            validate=args.validate,
            s3_bucket=args.s3_bucket,
            pre_launch=args.pre_launch,
            post_launch=args.post_launch,
            clean=args.clean,
            flush_cache=args.flush_cache,
            save_snapshot=args.save_snapshot,
            user=args.user,
            cmd=args.cmd,
            script=args.script,
            keep=args.keep,
        )

    def run_remote(self, args):
        """
        Run a build script from upstream (Changes), pulling any required
        information from the remote server, as well as pushing up status
        changes and log information.
        """
        if not args.api_url:
            raise CommandError('jobstep_id passed, but missing api_url')

        # we wrap the actual run routine to make it easier to catch
        # top level exceptions and report them via the log
        def inner_run(api, jobstep_id):
            try:
                # fetch build information to set defaults for things like snapshot
                # TODO(dcramer): make this support a small amount of downtime
                # TODO(dcramer): make this verify the snapshot
                resp = api.get_jobstep(jobstep_id)
                if resp['status']['id'] == 'finished':
                    raise Exception('JobStep already marked as finished, aborting.')

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

                api.update_jobstep(jobstep_id, {"status": "in_progress"})

                cmd = ['changes-client', '--server', args.api_url,
                       '--jobstep_id', jobstep_id]

                self.run_build_script(
                    snapshot=snapshot,
                    release=release,
                    validate=args.validate,
                    s3_bucket=args.s3_bucket,
                    pre_launch=args.pre_launch,
                    post_launch=args.post_launch,
                    clean=clean,
                    flush_cache=args.flush_cache,
                    save_snapshot=save_snapshot,
                    user=args.user,
                    cmd=cmd,
                    keep=args.keep,
                )

            except Exception:
                reporter.write(traceback.format_exc())

                api.update_jobstep(jobstep_id, {"status": "finished", "result": "failed"})
                if args.save_snapshot:
                    api.update_snapshot_image(snapshot, {"status": "failed"})

                raise

            else:
                api.update_jobstep(jobstep_id, {"status": "finished"})
                if args.save_snapshot:
                    api.update_snapshot_image(snapshot, {"status": "active"})

        api = ChangesApi(args.api_url)
        jobstep_id = args.jobstep_id

        reporter = LogReporter(api, jobstep_id)
        reporter_thread = Thread(target=reporter.process)
        reporter_thread.start()
        self.patch_system_logging(reporter)

        heartbeater = Heartbeater(api, jobstep_id)
        heartbeat_thread = Thread(target=heartbeater.wait)
        heartbeat_thread.start()

        run_thread = Thread(target=inner_run, args=[api, jobstep_id])
        run_thread.daemon = True
        run_thread.start()
        while run_thread.is_alive() and heartbeat_thread.is_alive():
            try:
                run_thread.join(10)
            except Exception:
                reporter.write(traceback.format_exc())
                break
            sleep(1)

        if run_thread.is_alive():
            reporter.write('==> Signal received from upstream, terminating.\n')
            # give it a second chance in case there was a race between the heartbeat
            # and the builder
            run_thread.join(5)

        reporter.close()
        heartbeater.close()

        reporter_thread.join(60)
        heartbeat_thread.join(1)

    def run_build_script(self, snapshot, release, validate, s3_bucket, pre_launch,
                         post_launch, clean, flush_cache, save_snapshot,
                         user, cmd=None, script=None, keep=False):
        """
        Run the given build script inside of the LXC container.
        """
        assert clean or not (save_snapshot and snapshot), \
            "You cannot create a snapshot from an existing snapshot"

        assert not (cmd and script), \
            'Only one of cmd or script can be specified'

        assert cmd or script, \
            'Missing build command'

        container = Container(
            snapshot=snapshot,
            release=release,
            validate=validate,
            s3_bucket=s3_bucket,
        )

        try:
            container.launch(pre_launch, post_launch, clean, flush_cache)

            # TODO(dcramer): we should assert only one type of command arg is set
            if cmd:
                container.run(cmd, user=user)
            elif script:
                container.run_script(script, user=user)

            if save_snapshot:
                snapshot = container.create_image()
                print("==> Snapshot saved: {}".format(snapshot))
                if s3_bucket:
                    container.upload_image(snapshot=snapshot)
        except Exception as e:
            logging.exception(e)
            raise e
        finally:
            if not keep:
                container.destroy()
            else:
                print("==> Container kept at {}".format(container.rootfs))
                print("==> SSH available via:")
                print("==>   $ sudo lxc-attach --name={}".format(container.name))


def main():
    command = WrapperCommand()
    command.run()


if __name__ == '__main__':
    main()
