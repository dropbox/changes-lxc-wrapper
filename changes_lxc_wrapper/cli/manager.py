#!/usr/bin/env python3

import argparse
import os.path

from collections import namedtuple

from changes_lxc_wrapper.container import SNAPSHOT_CACHE


DESCRIPTION = "LXC snapshot manager"

SnapshotInfo = namedtuple('SnapshotInfo', ['id', 'path', 'size'])


class ManagerCommand(object):
    """
    Bound image cache to:

    - ttl
    - max-disk usage
    - max-disk per class

    Treat it as a semi-LRU:

    - always keep 'active' snapshots
    - clear out ttl'd snapshots first
    - next find projects exceeding max-disk per class and clear out any up
      to the active
    - finally sort remainder by size and clear out biggest first
    """
    def __init__(self, argv=None):
        self.argv = argv

    def get_arg_parser(self):
        parser = argparse.ArgumentParser(description=DESCRIPTION)
        parser.add_argument('--max-disk')
        parser.add_argument('--max-disk-per-class')
        parser.add_argument('--ttl')
        parser.add_argument('--cache-path', default=SNAPSHOT_CACHE)
        return parser

    def run(self):
        parser = self.get_arg_parser()
        args = parser.parse_args(self.argv)

        # find all valid snapshot paths
        path_list = self.collect_files(args.cache_path)

        # collect size information for each path
        snapshots = []
        for path in path_list:
            snapshots.append(
                SnapshotInfo(
                    path.rsplit('/', 1)[-1],
                    path,
                    self.get_directory_size(path),
                )
            )
        print(snapshots)

    def get_directory_size(self, path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size

    def collect_files(self, root):
        # The root will consist of three subdirs, depicting the dist, release,
        # and arch. i.e. ubuntu/precise/amd64/
        # We need to collect all children that are three levels deep
        if not os.path.exists(root):
            return []

        def _collect_files(path, _stack=None, _depth=1):
            if _stack is None:
                _stack = []
            for name in os.listdir(path):
                name_path = os.path.join(path, name)
                if not os.path.isdir(name_path):
                    continue
                if _depth <= 3:
                    _collect_files(name_path, _stack, _depth + 1)
                else:
                    _stack.append(name_path)
            return _stack

        return _collect_files(root)


def main():
    command = ManagerCommand()
    command.run()


if __name__ == '__main__':
    main()
