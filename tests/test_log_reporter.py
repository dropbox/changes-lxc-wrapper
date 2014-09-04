from mock import call, Mock
from threading import Thread
from uuid import uuid4

from changes_lxc_wrapper.log_reporter import LogReporter


def test_line_buffering():
    mock_api = Mock()
    jobstep_id = uuid4()

    reporter = LogReporter(mock_api, jobstep_id)
    reporter_thread = Thread(target=reporter.process)
    reporter_thread.start()

    reporter.write('hello ')
    reporter.write('world\n')
    reporter.write('foo bar')

    reporter.close()
    reporter_thread.join()

    assert mock_api.mock_calls == [
        call.append_log(jobstep_id, {
            'text': 'hello world\n',
            'source': 'console',
        }),
        call.append_log(jobstep_id, {
            'text': 'foo bar',
            'source': 'console',
        }),
    ]
