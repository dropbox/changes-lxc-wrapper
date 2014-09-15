import os.path

from mock import Mock
from subprocess import check_call
from uuid import UUID

from changes_lxc_wrapper.snapshot_cache import SnapshotCache


CACHE_PATH = '/tmp/changes-lxc-wrapper-snapshot-cache-test'


def setup_dummy_cache(path):
    snapshot_1_id = '311a862b-dd15-4c44-90f1-fa95a7621860'
    snapshot_2_id = 'af986ceb-6640-4b69-b722-42df633ed0b7'

    check_call(['rm', '-rf', path])
    check_call(['mkdir', '-p', '{}/ubuntu/precise/i386'.format(path)])
    check_call(['mkdir', '-p', '{}/ubuntu/precise/i386/{}'.format(path, snapshot_1_id)])
    check_call(['mkdir', '-p', '{}/ubuntu/precise/i386/{}'.format(path, snapshot_2_id)])
    with open('{}/ubuntu/precise/i386/{}/foo'.format(path, snapshot_2_id), 'w') as fp:
        fp.write('12345')


def test_simple():
    mock_api = Mock()
    mock_api.list_snapshots.return_value = []

    setup_dummy_cache(CACHE_PATH)

    cache = SnapshotCache(CACHE_PATH, mock_api)
    cache.initialize()

    assert len(cache.snapshots) == 2
    assert cache.snapshots[0].id == UUID('311a862b-dd15-4c44-90f1-fa95a7621860')
    assert cache.snapshots[0].path == '{}/ubuntu/precise/i386/311a862b-dd15-4c44-90f1-fa95a7621860'.format(CACHE_PATH)
    assert cache.snapshots[0].size == 0
    assert cache.snapshots[1].id == UUID('af986ceb-6640-4b69-b722-42df633ed0b7')
    assert cache.snapshots[1].path == '{}/ubuntu/precise/i386/af986ceb-6640-4b69-b722-42df633ed0b7'.format(CACHE_PATH)
    assert cache.snapshots[1].size == 5
    assert cache.total_size == 5

    cache.remove(cache.snapshots[1])

    assert len(cache.snapshots) == 1
    assert cache.snapshots[0].id == UUID('311a862b-dd15-4c44-90f1-fa95a7621860')
    assert cache.total_size == 0

    assert not os.path.exists('{}/ubuntu/precise/i386/af986ceb-6640-4b69-b722-42df633ed0b7'.format(CACHE_PATH))
