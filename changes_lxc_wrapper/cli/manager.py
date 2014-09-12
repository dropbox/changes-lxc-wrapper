#!/usr/bin/env python3

import argparse
import re

from collections import defaultdict, namedtuple
from datetime import datetime, timedelta

from ..api import ChangesApi
from ..container import SNAPSHOT_CACHE
from ..snapshot_cache import SnapshotCache

DESCRIPTION = "LXC snapshot manager"

SnapshotInfo = namedtuple('SnapshotInfo', ['id', 'path', 'size'])


def parse_size_value(value):
    value = value.lower()
    match = re.match(r'(\d+)(gb|g|mb|m|kb|k|b)?', value)
    if not match:
        raise ValueError('Unable to parse size value')

    number = int(match.group(1))
    key = match.group(2)

    if key in ('gb', 'g'):
        return number / 1024 / 1024 / 1024
    elif key in ('mb', 'm'):
        return number / 1024 / 1024
    elif key in ('kb', 'k'):
        return number / 1024
    return number


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
        parser.add_argument('--max-disk', required=True, type=parse_size_value)
        parser.add_argument('--max-disk-per-class', type=parse_size_value)
        parser.add_argument('--ttl', required=True)
        parser.add_argument('--cache-path', default=SNAPSHOT_CACHE)
        parser.add_argument('--api-url', required=True,
                            help="API URL to Changes (i.e. https://changes.example.com/api/0/)")
        return parser

    def run(self):
        parser = self.get_arg_parser()
        args = parser.parse_args(self.argv)

        api = ChangesApi(args.api_url)

        cache = SnapshotCache(args.cache_path, api)
        cache.initialize()

        if args.ttl:
            ttl_date = datetime.utcnow() - timedelta(seconds=args.ttl)
        else:
            ttl_date = None

        # find snapshot data within Changes
        snapshots_by_class = defaultdict(list)
        used_space_by_class = defaultdict(int)

        for snapshot in sorted(cache.snapshots, key=lambda x: x.date_created):
            # this snapshot is unknown or has been invalidated
            if not snapshot.is_valid:
                cache.remove(snapshot)
                continue

            # check ttl to see if we can safely remove it
            elif ttl_date and snapshot.date_created < ttl_date:
                cache.remove(snapshot)
                continue

            # add size to class pool for later determination
            used_space_by_class[snapshot.project] += snapshot.size
            snapshots_by_class[snapshot.project].append(snapshot)

        if args.max_disk_per_class:
            for project_id, class_size in used_space_by_class.items():
                # keep removing old snapshots until we're under the threshold
                while class_size > args.max_disk_per_class:
                    snapshot = snapshots_by_class.pop(0)
                    cache.remove(snapshot)
                    class_size -= snapshot.size

        # finally, ensure we're under our disk threshold or remove snapshots
        # based on their size
        # TODO(dcramer): we could optimize this to more evenly remove snapshots
        snapshot_size_iter = iter(sorted(
            cache.snapshots, key=lambda x: x.size, reverse=True))

        while cache.size > args.max_disk:
            snapshot = snapshot_size_iter.next()
            cache.remove(snapshot)


def main():
    command = ManagerCommand()
    command.run()


if __name__ == '__main__':
    main()
