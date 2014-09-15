import threading

from mock import patch
from uuid import uuid4

from changes_lxc_wrapper.cli.wrapper import WrapperCommand


def generate_jobstep_data():
    # this must generic a *valid* dataset that should result in a full
    # run
    return {
        'status': {'id': 'queued'},
        'data': {},
        'expectedSnapshot': None,
        'snapshot': {
            'id': 'a1028849e8cf4ff0a7d7fdfe3c4fe925',
        },
    }


def setup_function(function):
    assert threading.activeCount() == 1


def teardown_function(function):
    assert threading.activeCount() == 1


@patch.object(WrapperCommand, 'run_build_script')
def test_local_run(mock_run):
    command = WrapperCommand([
        '--', 'echo 1',
    ])
    command.run()

    mock_run.assert_called_once_with(
        release='precise',
        post_launch=None,
        snapshot=None,
        save_snapshot=False,
        s3_bucket=None,
        pre_launch=None,
        validate=True,
        user='ubuntu',
        cmd=['echo 1'],
        script=None,
        flush_cache=False,
        clean=False,
        keep=False,
    )


@patch('changes_lxc_wrapper.cli.wrapper.ChangesApi')
@patch.object(WrapperCommand, 'run_build_script')
def test_remote_run(mock_run, mock_api_cls):
    jobstep_id = uuid4()

    jobstep_data = generate_jobstep_data()

    mock_api = mock_api_cls.return_value
    mock_api.get_jobstep.return_value = jobstep_data

    command = WrapperCommand([
        '--jobstep-id', jobstep_id.hex,
        '--api-url', 'http://changes.example.com',
    ])
    command.run()

    mock_run.assert_called_once_with(
        release='precise',
        post_launch=None,
        snapshot='a1028849-e8cf-4ff0-a7d7-fdfe3c4fe925',
        save_snapshot=False,
        s3_bucket=None,
        pre_launch=None,
        validate=True,
        user='ubuntu',
        cmd=['changes-client', '--server', 'http://changes.example.com', '--jobstep_id', jobstep_id.hex],
        flush_cache=False,
        clean=False,
        keep=False,
    )


@patch('changes_lxc_wrapper.cli.wrapper.ChangesApi')
@patch.object(WrapperCommand, 'run_build_script')
def test_already_finished_job(mock_run, mock_api_cls):
    jobstep_id = uuid4()

    jobstep_data = generate_jobstep_data()
    jobstep_data['status']['id'] = 'finished'

    mock_api = mock_api_cls.return_value
    mock_api.get_jobstep.return_value = jobstep_data

    command = WrapperCommand([
        '--jobstep-id', jobstep_id.hex,
        '--api-url', 'http://changes.example.com',
    ])
    command.run()

    assert not mock_run.called


@patch('changes_lxc_wrapper.cli.wrapper.ChangesApi')
@patch.object(WrapperCommand, 'run_build_script')
def test_non_default_release(mock_run, mock_api_cls):
    jobstep_id = uuid4()

    jobstep_data = generate_jobstep_data()
    jobstep_data['data']['release'] = 'fakerelease'

    mock_api = mock_api_cls.return_value
    mock_api.get_jobstep.return_value = jobstep_data

    command = WrapperCommand([
        '--jobstep-id', jobstep_id.hex,
        '--api-url', 'http://changes.example.com',
    ])
    command.run()

    mock_run.assert_called_once_with(
        release='fakerelease',
        post_launch=None,
        snapshot='a1028849-e8cf-4ff0-a7d7-fdfe3c4fe925',
        save_snapshot=False,
        s3_bucket=None,
        pre_launch=None,
        validate=True,
        user='ubuntu',
        cmd=['changes-client', '--server', 'http://changes.example.com', '--jobstep_id', jobstep_id.hex],
        flush_cache=False,
        clean=False,
        keep=False,
    )
