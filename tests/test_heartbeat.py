from mock import call, Mock
from time import sleep
from threading import Thread
from uuid import uuid4

from changes_lxc_wrapper.heartbeat import Heartbeater


def test_simple():
    mock_api = Mock()
    jobstep_id = uuid4()

    mock_api.get_jobstep.return_value = {
        'status': {'id': 'in_progress'}
    }

    heartbeater = Heartbeater(mock_api, jobstep_id)
    heartbeat_thread = Thread(target=heartbeater.wait)
    heartbeat_thread.start()

    sleep(0.001)

    assert heartbeat_thread.is_alive()
    mock_api.get_jobstep.assert_called_once_with(jobstep_id)

    mock_api.get_jobstep.return_value = {
        'status': {'id': 'finished'}
    }

    sleep(0.001)

    # XXX(dcramer): we really shouldnt call this internal API
    with heartbeater.cv:
        heartbeater.cv.notifyAll()

    sleep(0.001)

    assert mock_api.mock_calls == [
        call.get_jobstep(jobstep_id),
        call.get_jobstep(jobstep_id),
    ]

    assert not heartbeat_thread.is_alive()

    heartbeater.close()
    heartbeat_thread.join()
