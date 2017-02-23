# coding:utf-
import time
import requests
import logging
import multiprocessing

from multiprocessing import Queue
from gevent import monkey
from gevent.pool import Pool
monkey.patch_all()

from mongoengine import NotUniqueError, DoesNotExist
from requests.exceptions import RequestException
from models import IpProxies
from settings import (HEADER, TEST_URL, VALIDATE_TIMEOUT, VALIDATE_PROCESS_NUM, VALIDATE_THREAD_NUM, CONT_FAIL_TIMES,
                      FAIL_RATE_LIMIT, ON_FAIL_RATE_TIMES)


FAIL_PLACEHOLDER = 0


class Validator(object):
    def __init__(self):
        self.request = requests.Session()
        self.request.adapters.DEFAULT_RETRIES = 5
        self.request.headers.update(HEADER)
        self.logger = logging.getLogger(__name__)

    def run(self, ips):
        cocurrent(self.validate, ips, VALIDATE_PROCESS_NUM, VALIDATE_THREAD_NUM)

    def validate(self, ip_obj):
        ip, port = ip_obj['ip'], ip_obj['port']
        ip_obj['protocol'] = 'https'
        ip_addr = '{ip}:{port}'.format(ip=ip, port=port)
        proxies = {'https': 'https://{}'.format(ip_addr)}
        start = time.time()
        try:
            resp = requests.get(url=TEST_URL, timeout=VALIDATE_TIMEOUT, proxies=proxies, verify=False)
            if not resp.ok:
                raise RequestException
            speed = round(time.time() - start, 2)
            ip_obj['speeds'].append(speed)
            self.store_into_db(ip_obj)
            self.logger.info('success ip={ip}, port={port}, speed={speed}\n'.format(ip=ip, port=port, speed=speed))
        except RequestException:
            self.logger.warning('fail ip={}\n'.format(ip))
            self.handle_request_error(ip_obj)

    def handle_request_error(self, ip_obj):
        """处理验证失败的代理ip
            爬取的ip直接返回.
            数据库里的ip验证淘汰规则(失败的ip,speed=99):
                1. 失败数: 连续验证失败3次的IP直接上删除淘汰.
                2. 失败率: ip验证次数超过10次时,开启失败率淘汰(当失败率>50%时,直接淘汰删除)
        :param ip_obj:
        :return:
        """
        ip_obj['speeds'].append(FAIL_PLACEHOLDER)
        ip, speeds = ip_obj['ip'], ip_obj['speeds']
        speeds_len = len(speeds)
        if speeds_len >= CONT_FAIL_TIMES:
            # 失败数
            last_speeds = speeds[(0 - CONT_FAIL_TIMES):]
            if len(last_speeds) == last_speeds.count(FAIL_PLACEHOLDER):
                self.logger.warning('ip {ip} continue fail {count} times arrive limit.'.format(ip=ip, count=CONT_FAIL_TIMES))
                self.delete_ip_from_db(ip)
                return
            # 失败率
            if speeds_len >= ON_FAIL_RATE_TIMES:
                fail_count = speeds.count(FAIL_PLACEHOLDER)
                fail_rate = float(fail_count)/speeds_len
                if fail_rate > FAIL_RATE_LIMIT:
                    self.logger.warning('ip failed rate {} arrive limit.'.format(fail_rate))
                    self.delete_ip_from_db(ip)
                    return
        self.store_into_db(ip_obj)

    @staticmethod
    def store_into_db(ip_obj):
        ip, port, ip_type, protocol, speeds = ip_obj['ip'], ip_obj['port'], ip_obj['ip_type'], ip_obj['protocol'], ip_obj['speeds']
        try:
            obj = IpProxies.objects.get(ip=ip)
            if len(speeds) == 1:
                speeds.extend(obj['speeds'])
            obj.update(port=port, ip_type=ip_type, protocol=protocol, speeds=speeds)
        except DoesNotExist:
            IpProxies(ip=ip, port=port, ip_type=ip_type, protocol=protocol, speeds=speeds).save()

    def delete_ip_from_db(self, ip):
        IpProxies.objects(ip=ip).delete()
        self.logger.warning('delete ip {0} from database'.format(ip))


def cocurrent(func, items, process_num, coroutine_num):
    queue = Queue()
    pieces = average_cut_list(items, process_num)
    processes = []
    for piece in pieces:
        process = multiprocessing.Process(target=process_with_coroutine, args=(func, piece, queue, coroutine_num))
        process.start()
        processes.append(process)
    for process in processes:
        process.join()

    results = []
    for _ in processes:
        result = queue.get()
        results.extend(result)
    return results


def process_with_coroutine(func, piece, queue, coroutine_num):
    validate_pool = Pool(coroutine_num)
    result = validate_pool.map(func, piece)
    queue.put(result)


def average_cut_list(source_list, count):
    func = lambda A, n: [A[i:i + n] for i in range(0, len(A), n)]
    return func(source_list, count)
