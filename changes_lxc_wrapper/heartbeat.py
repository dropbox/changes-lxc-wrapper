from threading import Condition, Event


class Heartbeater(object):
    interval = 5

    def __init__(self, api, jobstep_id, interval=None):
        self.api = api
        self.jobstep_id = jobstep_id
        self.cv = Condition()
        self.finished = Event()

        if interval is not None:
            self.interval = interval

    def wait(self):
        with self.cv:
            self.finished.clear()
            while not self.finished.is_set():
                data = self.api.get_jobstep(self.jobstep_id)
                if data['status']['id'] == 'finished':
                    self.finished.set()
                    break

                self.cv.wait(self.interval)

    def close(self):
        with self.cv:
            self.finished.set()
            self.cv.notifyAll()
