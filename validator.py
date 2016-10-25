# coding:utf-
import time
import requests
import logging
import config
import multiprocessing

from mongoengine import NotUniqueError, DoesNotExist
from gevent import monkey
from gevent.pool import Pool
monkey.patch_all()
from requests.exceptions import RequestException
from models import IpProxies
from config import (HEADER, TEST_URL, VALIDATE_TIMEOUT, CONT_FAIL_TIMES, \
    FAIL_RATE_LIMIT, ON_FAIL_RATE_TIMES)


FAIL_PLACEHOLDER = 0


class Validator(object):
    def __init__(self):
        self.process_num = config.VALIDATE_PROCESS_NUM
        self.thread_num = config.VALIDATE_THREAD_NUM
        self.timeout = config.VALIDATE_TIMEOUT
        self.request = requests.Session()
        self.request.adapters.DEFAULT_RETRIES = 5
        self.request.headers.update(HEADER)
        self.logger = None
        self.set_logger()

    def set_logger(self):
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(console)

    def run(self, ips):
        process = []
        piece = len(ips) / self.process_num + 1
        for i in range(self.process_num):
            ip_list = ips[piece*i:piece*(i+1)]
            p = multiprocessing.Process(target=self.process_with_gevent, args=(ip_list,))
            p.start()
            process.append(p)
        for p in process:
            p.join()
        # for ip_obj in ips:
        #     self.validate(ip_obj)

    def process_with_gevent(self, ips):
        validate_pool = Pool(self.thread_num)
        validate_pool.map(self.validate, ips)

    def validate(self, ip_obj):
        ip = ip_obj['ip']
        port = ip_obj['port']
        proxy_addr = '{ip}:{port}'.format(ip=ip, port=port)
        proxies = {
            'http': 'http://%s' % proxy_addr,
            'https': 'https://%s' % proxy_addr,
        }
        start = time.time()
        try:
            resp = requests.get(url=TEST_URL, timeout=VALIDATE_TIMEOUT, proxies=proxies, verify=False)
            if not resp.ok:
                raise RequestException
        except RequestException:
            ip_obj['speeds'].append(FAIL_PLACEHOLDER)
            self.handle_request_error(ip_obj)
            self.logger.warning('fail ip = {0}\n'.format(ip))
            return
        except Exception as e:
            self.logger.error(str(e))
            return
        else:
            speed = round(time.time()-start, 2)
            ip_obj['speeds'].append(speed)
            self.store_into_db(ip_obj)
            self.logger.info('success ip = {ip}, port = {port}, speed = {speed}\n'.format(ip=ip, port=port, speed=speed))

    def handle_request_error(self, ip_obj):
        '''处理验证失败的代理ip
            爬取的ip直接返回.
            数据库里的ip验证淘汰规则(失败的ip,speed=99):
                1. 失败数: 连续验证失败3次的IP直接上删除淘汰.
                2. 失败率: ip验证次数超过10次时,开启失败率淘汰(当失败率>50%时,直接淘汰删除)
        :param ip_obj:
        :return:
        '''
        if not ip_obj:
            return
        ip = ip_obj['ip']
        speeds = ip_obj['speeds']
        speeds_len = len(speeds)
        if speeds_len == 1:
            return
        else:
            # 失败数
            is_cont_fail = True
            index = 0 - CONT_FAIL_TIMES
            last_speeds = speeds[index:]
            for speed in last_speeds:
                if speed != FAIL_PLACEHOLDER:
                    is_cont_fail = False
                    break
            if is_cont_fail:
                self.logger.info('ip {ip} continuous fail times arrive limit, {count} times.'.format(ip=ip, count=CONT_FAIL_TIMES))
                self.delete_ip_from_db(ip)
                return
            # 失败率
            if speeds_len >= ON_FAIL_RATE_TIMES:
                fail_count = 0
                for speed in speeds:
                    if speed == FAIL_PLACEHOLDER:
                        fail_count += 1
                fail_rate = float(fail_count)/speeds_len
                if fail_rate > FAIL_RATE_LIMIT:
                    self.delete_ip_from_db(ip)
                    return
            self.update_speeds(ip, speeds)

    def store_into_db(self, ip_obj):
        if not ip_obj:
            return
        ip = ip_obj['ip']
        port = ip_obj['port']
        ip_type = ip_obj['ip_type']
        protocol = ip_obj['protocol']
        speeds = ip_obj['speeds']

        try:
            IpProxies.objects.get(ip=ip)
            self.update_speeds(ip, speeds)
        except DoesNotExist:
            try:
                IpProxies(
                    ip=ip,
                    port=port,
                    ip_type=ip_type,
                    protocol=protocol,
                    speeds=speeds
                ).save()
            except Exception as e:
                self.logger.error(str(e))

    def update_speeds(self, ip, speeds):
        try:
            ip_obj = IpProxies.objects.get(ip=ip)
            ip_obj['speeds'] = speeds
            ip_obj.save()
        except DoesNotExist as e:
            self.logger.error(str(e))

    def delete_ip_from_db(self, ip):
        IpProxies.objects(ip=ip).delete()
        self.logger.warning('delete ip {0} from database'.format(ip))
