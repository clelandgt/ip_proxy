# coding:utf-8
import json
import time
import operator
import logging
import config

from mongoengine import connect
from gevent.pool import Pool
from config import PARSER_LIST
from models import IpProxies
from crawl import Crawl
from validator import Validator


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

    def run(self):
        while True:
            try:
                proxies = IpProxies.objects.all()
                self.validate(proxies)
                proxies = IpProxies.objects.all()
                if proxies.count() < config.IPS_MIN_NUM:
                    new_proxies = self.crawl()
                    if not new_proxies:
                        new_proxies = []
                    self.logger.info('crawl {0} ips \n'.format(len(new_proxies)))
                    self.validate(new_proxies)
                time.sleep(config.UPDATE_TIME)
            except Exception as e:
                self.logger.error(str(e))

    def validate(self, proxies):
        proxies_len = len(proxies)
        start_time = time.time()
        self.logger.info('{0} proxies need validate -------\n'.format(proxies_len))
        self.validator.run(proxies)
        end_time = time.time()
        self.logger.info('validate end -------\n')
        self.logger.info('{0} proxies, spend {1}s\n'.format(proxies_len, end_time-start_time))
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

    def get_proxy(self, count=None, in_detail=False):
        proxies = []
        proxy_objs = IpProxies.objects.all()
        if in_detail:
            for proxy_obj in proxy_objs:
                proxy_json = json.loads(proxy_obj.to_json())
                proxies.append(proxy_json)
        else:
            for proxy_obj in proxy_objs:
                ip_addr = '{ip}:{port}'.format(ip=proxy_obj['ip'], port=proxy_obj['port'])
                proxies.append(ip_addr)
        return proxies[:count]

    def ip_rank(self, count=None):
        '''当前根据成功率单一指标进行ip排名
        当times<5, 不进入ip排名
        times>=5. 取最后10次的数据求平均值

        TODO: 评估指标: 成功率, 平均数据, ip速度的稳定性
        '''
        FAIL_PLACEHOLDER = 0
        proxies = self.get_proxy(in_detail=True)
        pre_proxies = []
        for proxy in proxies:
            speeds = proxy['speeds']
            speeds_len = len(speeds)
            if speeds_len > 5:
                success_count = 0
                for speed in speeds:
                    if speed != FAIL_PLACEHOLDER:
                        success_count += 1
                success_rate = float(success_count) / speeds_len
                ip_addr = '{ip}:{port}'.format(ip=proxy['ip'], port=proxy['port'])
                pre_proxies.append((ip_addr, success_rate))
        pre_proxies.sort(key=operator.itemgetter(1))
        sort_proxies = pre_proxies.reverse()[:count]
        return sort_proxies


def main():
    ip_proxy = IPProxy()
    ip_proxy.run()


if __name__ == '__main__':
    main()
