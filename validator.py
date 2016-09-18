# coding:utf-8
import sys
import time
import requests

from gevent.pool import Pool
from config import HEADER, TEST_URL, TIMEOUT, THREADNUM


class Validator(object):
    def __init__(self):
        self.request = requests.Session()
        self.request.adapters.DEFAULT_RETRIES = 5
        self.request.headers.update(HEADER)
        self.detect_pool = Pool(THREADNUM)

    def check_is_active(self, proxies):
        sys.stdout.write('validator beginning -------\n')
        proxies = self.detect_pool.map(self.detect_list, proxies)
        sys.stdout.write('validator end -------\n')
        return proxies

    def detect_list(self, proxy):
        ip = proxy['ip']
        port = proxy['port']
        proxy_address = '{ip}:{port}'.format(
            ip=ip,
            port=port
        )
        proxies = {
            'http': 'http://%s' % proxy_address,
            # 'https': 'https://%s' % proxy_address,
        }
        start = time.time()
        try:
            r = requests.get(url=TEST_URL, timeout=TIMEOUT, proxies=proxies)
            if not r.ok:
                sys.stdout.write('fail ip = {0}\n'.format(ip))
                proxy = None
            else:
                speed = round(time.time()-start, 2)
                proxy['speed'] = speed
                sys.stdout.write('success ip = {ip}, port = {port}, speed = {speed}\n'.format(ip=ip, port=port, speed=speed))
        except:
                sys.stdout.write('fail ip = {0}\n'.format(ip))
                proxy = None
        return proxy
