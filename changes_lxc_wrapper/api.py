import logging
import json
import time

from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen


class ChangesApi(object):
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')

    def request(self, path, data=None, max_retries=5):
        if isinstance(data, dict):
            data = urlencode(data).encode('utf-8')

        url = '{}/{}'.format(self.base_url, path.lstrip('/'))
        logging.info('Making request to {}'.format(url))
        for retry_num in range(max_retries):
            try:
                fp = urlopen(url, data=data, timeout=5)

                body = fp.read().decode('utf-8')
                return json.loads(body)
            except URLError as e:
                if retry_num < max_retries - 1:
                    retry_delay = retry_num ** 2
                    print(" ==> API request failed ({}), retrying in {}s".format(
                        getattr(e, 'code', type(e)), retry_delay))
                    time.sleep(retry_delay)
        print(" ==> Failed request to {}".format(path))
        raise

    def update_jobstep(self, jobstep_id, data):
        return self.request('/jobsteps/{}/'.format(jobstep_id), data)

    def get_jobstep(self, jobstep_id):
        return self.request('/jobsteps/{}/'.format(jobstep_id))

    def update_snapshot_image(self, snapshot_id, data):
        return self.request('/snapshotimages/{}/'.format(snapshot_id), data)

    def append_log(self, jobstep_id, data):
        return self.request('/jobsteps/{}/logappend/'.format(jobstep_id), data)
