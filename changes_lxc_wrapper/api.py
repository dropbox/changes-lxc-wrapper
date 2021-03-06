import logging
import json
import time

from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen


class BuildCancelled(Exception):
    pass


class ChangesApi(object):
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')

    def request(self, path, data=None, max_retries=5):
        if isinstance(data, dict):
            data = urlencode(data).encode('utf-8')

        url = '{}/{}'.format(self.base_url, path.lstrip('/'))
        logging.info('Making request to %s', url)
        for retry_num in range(max_retries):
            try:
                fp = urlopen(url, data=data, timeout=5)

                body = fp.read().decode('utf-8')
                return json.loads(body)
            except URLError as e:
                code = getattr(e, 'code', None)
                if code == 404:
                    # this suggests that a primary key is wrong, or the
                    # base url is incorrect
                    raise

                if code == 410:
                    raise BuildCancelled

                if retry_num == max_retries - 1:
                    print("==> Failed request to {}".format(path))
                    raise

                retry_delay = (retry_num + 1) ** 2
                print("==> API request failed ({}), retrying in {}s".format(
                    code or e, retry_delay))
                time.sleep(retry_delay)

    def update_jobstep(self, jobstep_id, data):
        return self.request('/jobsteps/{}/'.format(jobstep_id), data)

    def get_jobstep(self, jobstep_id):
        return self.request('/jobsteps/{}/'.format(jobstep_id))

    def update_snapshot_image(self, snapshot_id, data):
        return self.request('/snapshotimages/{}/'.format(snapshot_id), data)

    def append_log(self, jobstep_id, data):
        return self.request('/jobsteps/{}/logappend/'.format(jobstep_id), data)

    def list_snapshots(self):
        return self.request('/snapshots/?state=valid&per_page=0')
