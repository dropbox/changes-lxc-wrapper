from collections import deque
from functools import wraps
from threading import Condition, Event, Lock
import sys


def chunked(buffer, chunk_size=4096):
    """
    Given a deque, chunk it up into ~chunk_size, but be aware of newline
    termination as an intended goal.
    """
    result = ''
    while buffer:
        result += buffer.popleft()
        while '\n' in result:
            newline_pos = result.rfind('\n', 0, chunk_size)
            if newline_pos == -1:
                newline_pos = chunk_size
            else:
                newline_pos += 1
            yield result[:newline_pos]
            result = result[newline_pos:]

    if result:
        yield result


def _locked(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        with self.lock:
            return func(self, *args, **kwargs)
    return wrapped


class ThreadSafeDeque(deque):
    def __init__(self, *args, **kwargs):
        self.lock = Lock()
        super().__init__(*args, **kwargs)

    append = _locked(deque.append)
    appendleft = _locked(deque.appendleft)
    clear = _locked(deque.clear)
    extend = _locked(deque.extend)
    extendleft = _locked(deque.extendleft)
    pop = _locked(deque.pop)
    popleft = _locked(deque.popleft)
    remove = _locked(deque.remove)
    reverse = _locked(deque.reverse)
    rotate = _locked(deque.rotate)


class LogReporter(object):
    source = 'console'

    def __init__(self, api, jobstep_id, source=None):
        self.api = api
        self.jobstep_id = jobstep_id
        if source is not None:
            self.source = source

        self.buffer = ThreadSafeDeque()
        self.done = Event()
        self.cv = Condition()

    def process(self):
        with self.cv:
            self.done.clear()
            while not self.done.is_set() or self.buffer:
                for chunk in chunked(self.buffer):
                    self.api.append_log(self.jobstep_id, {
                        'text': chunk,
                        'source': self.source,
                    })
                if not self.done.is_set():
                    self.cv.wait(5)

    def write(self, chunk):
        with self.cv:
            self.buffer.append(chunk)
            self.cv.notifyAll()

    def close(self):
        with self.cv:
            self.done.set()
            self.cv.notifyAll()
