# coding:utf-8
import time
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
            # try:
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
            # except Exception as e:
            #     self.logger.error(str(e))

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


def main():
    ip_proxy = IPProxy()
    ip_proxy.run()


if __name__ == '__main__':
    main()
