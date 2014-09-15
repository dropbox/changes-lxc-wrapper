import os.path
import shutil

from datetime import datetime
from uuid import UUID


DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


def get_directory_size(path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


def convert_date(value):
    return datetime.strptime(value, DATETIME_FORMAT)


class SnapshotImage(object):
    def __init__(self, id, path, date_created=None, is_active=None,
                 is_valid=True, project=None):
        self.id = id
        self.path = path
        self.size = get_directory_size(path)
        self.date_created = date_created
        self.is_active = is_active
        self.is_valid = is_valid
        self.project = project


class SnapshotCache(object):
    def __init__(self, root, api):
        self.api = api
        self.root = root
        self.snapshots = []

    def initialize(self):
        print("==> Initializing snapshot cache")
        # find all valid snapshot paths
        path_list = self._collect_files(self.root)

        upstream_data = {}
        if path_list:
            # get upstream metadata
            print("==> Fetching upstream metadata")
            for snapshot in self.api.list_snapshots():
                for image in snapshot['images']:
                    upstream_data[UUID(image['id'])] = {
                        'project': UUID(snapshot['project']['id']),
                        'date_created': convert_date(snapshot['dateCreated']),
                        'is_active': snapshot['isActive'],
                    }

        # collect size information for each path
        snapshot_list = []
        for path in path_list:
            id_ = UUID(path.rsplit('/', 1)[-1])
            path_data = upstream_data.get(id_, {})
            snapshot_list.append(SnapshotImage(
                id=id_,
                path=path,
                is_active=path_data.get('is_active', False),
                date_created=path_data.get('date_created'),
                is_valid=bool(path_data),
                project=path_data.get('project'),
            ))

        self.snapshots = snapshot_list

        print("==> {} items found in cache ({} bytes)".format(len(self.snapshots), self.total_size))

    @property
    def total_size(self):
        return sum(s.size for s in self.snapshots)

    def remove(self, snapshot, on_disk=True):
        assert not snapshot.is_active
        print("==> Removing snapshot: {}".format(snapshot.id))
        if on_disk:
            shutil.rmtree(snapshot.path)
        self.snapshots.remove(snapshot)

    def _collect_files(self, root):
        # The root will consist of three subdirs, depicting the dist, release,
        # and arch. i.e. ubuntu/precise/amd64/
        # We need to collect all children that are three levels deep
        if not os.path.exists(root):
            return []

        def _r_collect_files(path, _stack=None, _depth=1):
            if _stack is None:
                _stack = []
            for name in os.listdir(path):
                name_path = os.path.join(path, name)
                if not os.path.isdir(name_path):
                    continue
                if _depth <= 3:
                    _r_collect_files(name_path, _stack, _depth + 1)
                else:
                    _stack.append(name_path)
            return _stack

        return _r_collect_files(root)
