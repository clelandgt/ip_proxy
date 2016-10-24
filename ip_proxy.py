# coding:utf-8
import json
import time
import logging
import config
import requests

from mongoengine import connect
from gevent.pool import Pool
from config import PARSER_LIST
from models import IpProxies
from crawl import Crawl
from validator import Validator
from utils import diff


class IPProxy(object):
    def __init__(self):
        self.connect_mongodb()
        self.config_logging()
        self.validator = Validator()
        self.crawl_pool = Pool(config.CRAWL_THREAD_NUM)
        self.logger = logging.getLogger(__name__)

    def connect_mongodb(self):
        connect(host='mongodb://localhost:27017/material', alias='material')

    def config_logging(self):
        logging.basicConfig(filename=config.LOGGING_FILE, level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s \n\t\t%(message)s',
                            datefmt='%Y.%m.%d  %H:%M:%S')
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(console)

    def run_with_free_proxy(self):
        while True:
            try:
                proxies = list(IpProxies.objects.all())
                active_proxies = self.validate(proxies)
                invalid_proxies = diff(proxies, active_proxies)
                self.delete_invaild_proxies(invalid_proxies)
                if len(active_proxies) < config.IPS_MIN_NUM:
                    new_proxies = self.crawl()
                    self.logger.info('crawl {0} ips \n'.format(len(new_proxies)))
                    self.import_proxies(new_proxies)
                    time.sleep(config.UPDATE_TIME)
            except Exception as e:
                self.logger.error(str(e))

    def run_with_paid_proxy(self):
        while True:
            try:
                proxies = list(IpProxies.objects.all())
                active_proxies = self.validate(proxies)
                invalid_proxies = diff(proxies, active_proxies)
                self.delete_invaild_proxies(invalid_proxies)
                new_proxies = self._get_paid_proxies()
                self.import_proxies(new_proxies)
                time.sleep(config.INTERVAL_CALL_PAID_API)
            except Exception as e:
                self.logger.error(str(e))

    def _get_paid_proxies(self):
        proxies = []
        request = requests.session()
        url = config.PAID_PROXY_API
        resp = request.get(url)
        resp_json = json.loads(resp.text)
        proxy_list = resp_json['data']['proxy_list']
        for item in proxy_list:
            item = item.strip()
            collist = item.split(',')
            ip, port = collist[0].split(':')
            ip_type = None
            if u'高匿' in collist[1]:
                ip_type = u'高匿'
            ip_protocol = collist[2]
            speed = collist[3]
            proxy = {
                'ip': ip,
                'port': port,
                'ip_type': ip_type,
                'protocol': ip_protocol,
                'speed': speed
            }
            proxies.append(proxy)
        return proxies

    def validate(self, proxies):
        start_time = time.time()
        self.logger.info('{0} proxies need validate -------\n'.format(len(proxies)))
        proxies = self.validator.run(proxies)
        end_time = time.time()
        self.logger.info('validate end -------\n')
        self.logger.info('{0} proxies, spend {1}s\n'.format(len(proxies), end_time-start_time))
        return proxies

    def crawl(self):
        proxies = []
        self.logger.info('crawl beginning -------\n')
        results = self.crawl_pool.map(self._crawl, PARSER_LIST)
        for result in results:
            proxies.extend(result)
        self.logger.info('crawl end -------\n')
        return proxies

    def _crawl(self, parser):
        ip_proxies = []
        crawl = Crawl()
        for url in parser['urls']:
            self.logger.info('crawl {0}\n'.format(url))
            items = crawl.run(url, parser)
            if items != None:
                ip_proxies.extend(items)
        return ip_proxies

    def import_proxies(self, proxies):
        existed_proxies = IpProxies.objects.all()
        new_proxies = self.distinct(proxies, existed_proxies)
        new_proxies = self.validator.run(new_proxies)
        proxies = [proxy for proxy in new_proxies if proxy is not None]
        for proxy in proxies:
            try:
                IpProxies(
                    ip=proxy['ip'],
                    port=proxy['port'],
                    ip_type=proxy['ip_type'],
                    protocol=proxy['protocol'],
                    speed=proxy['speed']
                ).save()
            except Exception as e:
                self.logger.error('Exception:{0}\n'.format(str(e)))
        self.logger.info('import {0} proxies, now have proxies {1} in database'.
                         format(len(proxies), len(IpProxies.objects.all())))

    def distinct(self, new_items, items_db):
        result = []
        for item in new_items:
            if (item not in items_db) and (item not in result):
                result.append(item)
        return result

    def delete_invaild_proxies(self, proxies):
        for proxy in proxies:
            try:
                item = IpProxies.objects.get(ip=proxy['ip'], port=proxy['port'])
                self.logger.info('delete invalid ip: {0}\n'.format(proxy['ip']))
                item.delete()
            except Exception as e:
                self.logger.error(str(e))


def main():
    ip_proxy = IPProxy()
    if config.FREE_PROXY:
        ip_proxy.run_with_free_proxy()
    if config.PAID_PROXY:
        ip_proxy.run_with_paid_proxy()


if __name__ == '__main__':
    main()
