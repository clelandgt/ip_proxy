# coding:utf-
import time
import requests
import logging

import config
import multiprocessing
from gevent import monkey
from gevent.pool import Pool
monkey.patch_all()
from requests.exceptions import RequestException
from config import HEADER, TEST_URL, VALIDATE_TIMEOUT


class Validator(object):
    def __init__(self):
        self.process_num = config.VALIDATE_PROCESS_NUM
        self.thread_num = config.VALIDATE_THREAD_NUM
        self.timeout = config.VALIDATE_TIMEOUT
        self.request = requests.Session()
        self.request.headers.update(HEADER)
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(console)

    def run(self, ips):
        process = []
        result_queue = multiprocessing.Queue()
        piece = len(ips) / self.process_num + 1
        for i in range(self.process_num):
            ip_list = ips[piece*i:piece*(i+1)]
            p = multiprocessing.Process(target=self.process_with_gevent, args=(ip_list, result_queue))
            p.start()
            process.append(p)
        for p in process:
            p.join()
        result = []
        for p in process:
            result.extend(result_queue.get())
        return result

    def process_with_gevent(self, ip_list, result_queue):
        validate_pool = Pool(self.thread_num)
        result = validate_pool.map(self.validate, ip_list)
        result_queue.put(result)

    def validate(self, proxy):
        ip = proxy['ip']
        port = proxy['port']
        proxy_address = '{ip}:{port}'.format(
            ip=ip,
            port=port
        )
        proxies = {
            'http': 'http://%s' % proxy_address,
            'https': 'https://%s' % proxy_address,
        }
        start = time.time()
        try:
            resp = requests.get(url=TEST_URL, timeout=VALIDATE_TIMEOUT, proxies=proxies)
            if not resp.ok:
                raise RequestException
        except RequestException:
            self.logger.warning('fail ip = {0}\n'.format(ip))
            return
        except Exception as e:
            self.logger.error(str(e))
            return
        else:
            speed = round(time.time()-start, 2)
            proxy['speed'] = speed
            self.logger.info('success ip = {ip}, port = {port}, speed = {speed}\n'.format(ip=ip, port=port, speed=speed))
        return proxy
