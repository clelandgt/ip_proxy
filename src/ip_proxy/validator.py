# coding:utf-
import time
import requests
import logging

from mongoengine import NotUniqueError, DoesNotExist
from requests.exceptions import RequestException
from models import IpProxies
from utils import cocurrent
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
        ip_obj['protocol'] = 'http'
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
            self.handle_request_error(ip_obj)
            self.logger.warning('fail ip={}\n'.format(ip))

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
        if speeds_len == 1:
            return
        # 失败数
        is_cont_fail = True
        last_speeds = speeds[(0 - CONT_FAIL_TIMES):]
        for speed in last_speeds:
            if speed != FAIL_PLACEHOLDER:
                is_cont_fail = False
                break
        if is_cont_fail:
            self.logger.info('ip {ip} continue fail {count} times arrive limit.'.format(ip=ip, count=CONT_FAIL_TIMES))
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

    @staticmethod
    def update_speeds(ip, speeds):
        try:
            ip_obj = IpProxies.objects.get(ip=ip)
            ip_obj.update(speeds=speeds)
        except Exception:
            pass

    def delete_ip_from_db(self, ip):
        IpProxies.objects(ip=ip).delete()
        self.logger.warning('delete ip {0} from database'.format(ip))
