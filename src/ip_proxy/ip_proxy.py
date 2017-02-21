# coding:utf-8
import time
import logging
import logging.config
import settings

from mongoengine import connect
from settings import PARSER_LIST, LOGGING
from models import IpProxies
from crawl import Crawl
from validator import Validator


class IPProxy(object):
    def __init__(self):
        self.config_logging()
        self.connect_mongodb()
        self.validator = Validator()
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def connect_mongodb():
        connect(host='mongodb://localhost:27017/material', alias='material')

    @staticmethod
    def config_logging():
        logging.config.dictConfig(LOGGING)

    def run(self):
        while True:
            try:
                proxies = IpProxies.objects.all()
                self.validate(proxies)
                proxies = IpProxies.objects.all()
                if proxies.count() < settings.IPS_MIN_NUM:
                    new_proxies = self.crawl()
                    self.validate(new_proxies)
                time.sleep(settings.UPDATE_TIME)
            except Exception as e:
                self.logger.exception(e)

    def validate(self, proxies):
        proxies_len = len(proxies)
        start_time = time.time()
        self.logger.info('{0} proxies need validate -------'.format(proxies_len))
        self.validator.run(proxies)
        self.logger.info('validate end -------\n'
                         '{0} proxies, spend {1}s'.format(proxies_len, time.time()-start_time))
        return proxies

    def crawl(self):
        crawl = Crawl()
        proxies = []
        self.logger.info('crawl beginning -------')
        for parser in PARSER_LIST:
            for url in parser['urls']:
                self.logger.info('crawling {0}'.format(url))
                result = crawl.run(url, parser)
                proxies.extend(result)
        self.logger.info('crawl end -------\n'
                         'crawl {0} ips'.format(len(proxies)))
        return proxies


def main():
    ip_proxy = IPProxy()
    ip_proxy.run()


if __name__ == '__main__':
    main()
