# coding:utf-8
import sys
import time
import random
import config

from mongoengine import connect
from gevent.pool import Pool
from config import parserList
from models import IpProxies
from crawl import Crawl
from validator import Validator


class IPProxy(object):
    def __init__(self):
        connect(host='mongodb://localhost:27017/material', alias='material')
        self.validator = Validator()
        self.crawl_pool = Pool(config.THREADNUM)

    def run(self):
        while True:
            try:
                sys.stdout.write('validator beginning -------\n')
                proxies = IpProxies.objects.all()
                proxies = self.validator.check_is_active(proxies)
                if len(proxies) < config.IPS_MINNUM:
                    new_proxies = self.crawl_pool.map(self.crawl, parserList)[0]
                    self.import_proxies(new_proxies)
                    time.sleep(config.UPDATE_TIME)
            except Exception as e:
                sys.stdout.write('Exception:{0}'.format(str(e)))

    def crawl(self, parser):
        ip_proxies = []
        crawl = Crawl()
        for url in parser['urls']:
            items = crawl.run(url, parser)
            ip_proxies.extend(items)
        return ip_proxies

    def get_proxies(self):
        ip_proxies = random.choice(IpProxies.objects.all())
        return ip_proxies.get_proxies

    def import_proxies(self, proxies):
        existed_proxies = IpProxies.objects.all()
        new_proxies = self.distinct(proxies, existed_proxies)
        new_proxies = self.validator.check_is_active(new_proxies)
        for item in new_proxies:
            # TODO: save others
            IpProxies(
                ip=item['ip'],
                port=item['port'],

            ).save()

    def distinct(self, new_items, items_db):
        result = []
        for item in new_items:
            if (item not in items_db) and (item not in result):
                result.append(item)
        return result


def main():
    ip_proxy = IPProxy()
    ip_proxy.run()


if __name__ == '__main__':
    main()
