# coding:utf-8
import sys
import time
import config
import random

from mongoengine import connect
from gevent.pool import Pool
from config import parserList
from models import IpProxies
from crawl import Crawl
from validator import Validator
from utils import diff


class IPProxy(object):
    def __init__(self):
        connect(host='mongodb://localhost:27017/material', alias='material')
        self.validator = Validator()
        self.crawl_pool = Pool(config.THREADNUM)

    def run(self):
        while True:
            try:
                proxies = list(IpProxies.objects.all())
                active_proxies = self.validator.check_is_active(proxies)
                invalid_proxies = diff(proxies, active_proxies)
                self.delete_invaild_proxies(invalid_proxies)
                if len(active_proxies) < config.IPS_MINNUM:
                    new_proxies = self.crawl()
                    self.import_proxies(new_proxies)
                    time.sleep(config.UPDATE_TIME)
            except Exception as e:
                sys.stdout.write('Exception:{0}'.format(str(e)))

    def crawl(self):
        proxies = []
        sys.stdout.write('crawl beginning -------\n')
        results = self.crawl_pool.map(self._crawl, parserList)
        for result in results:
            proxies.extend(result)
        sys.stdout.write('crawl end -------\n')
        return proxies

    def _crawl(self, parser):
        ip_proxies = []
        crawl = Crawl()
        for url in parser['urls']:
            sys.stdout.write('crawl {0}\n'.format(url))
            items = crawl.run(url, parser)
            if items != None:
                ip_proxies.extend(items)
        return ip_proxies

    @classmethod
    def get_proxies(self, ip_type=IpProxies.ANONYMITY, lte_speed=5):
        results = IpProxies.objects.filter(ip_type=ip_type, lte_speed=lte_speed)
        ip_proxies = []
        for result in results:
            ip_proxies.append(result.get_proxies)
        return ip_proxies

    def import_proxies(self, proxies):
        existed_proxies = IpProxies.objects.all()
        new_proxies = self.distinct(proxies, existed_proxies)
        new_proxies = self.validator.check_is_active(new_proxies)
        try:
            for item in new_proxies:
                # TODO: save others
                IpProxies(
                    ip=item['ip'],
                    port=item['port'],
                    ip_type=item['ip_type'],
                    # protocol=item['protocol'],
                    speed=item['speed']
                ).save()
        except Exception as e:
            sys.stdout.write('Exception:{0}'.format(str(e)))

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
                sys.stdout.write('delete invalid ip: {0}\n'.format(proxy['ip']))
                item.delete()
            except:
                pass


def main():
    ip_proxy = IPProxy()
    ip_proxy.run()


if __name__ == '__main__':
    main()
