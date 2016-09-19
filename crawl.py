# coding:utf-8
import sys
import random
import requests

from lxml import etree
from config import HEADER, RETRY_TIME, CRAWL_TIMEOUT
from models import IpProxies


class Crawl(object):
    def __init__(self):
        self.request = requests.Session()
        self.request.adapters.DEFAULT_RETRIES = 5
        self.request.headers.update(HEADER)

    def run(self, url, parser):
        count = 0
        self.parser = parser
        need_proxy = False
        while(count <= RETRY_TIME):
            try:
                resp = self.run_get(url, need_proxy)
                return self.parse(resp)
            except Exception as e:
                # TODO: Instead of logging
                sys.stdout.write('Exception:{0}\n'.format(str(e)))
                need_proxy = True
            count = count + 1

    def run_get(self, url, need_proxy):
        if need_proxy:
            proxy = random.choice(IpProxies.objects.all())
            proxies = proxy.get_proxies()
            resp = self.request.get(url=url, timeout=CRAWL_TIMEOUT, proxies=proxies, verify=False)
        else:
            resp = self.request.get(url=url, timeout=CRAWL_TIMEOUT)
        if resp.status_code != 200:
            raise ValueError('response status is {0} not 200'.format(resp.status_code))
        resp.encoding ='gbk'
        return resp.text

    def parse(self, resp):
        parser = self.parser
        if parser['type'] != 'xpath':
            raise ValueError('type of parser is {0}, not xpath'.format(parser['type']))
        proxylist = []
        root = etree.HTML(resp)
        proxys = root.xpath(parser['pattern'])
        for proxy in proxys:
            ip = proxy.xpath(parser['postion']['ip'])[0].text
            port = proxy.xpath(parser['postion']['port'])[0].text
            type = proxy.xpath(parser['postion']['type'])[0].text
            if type.find(u'高匿') != -1:
                type = 0
            else:
                type = 1
            if len(parser['postion']['protocol']) > 0:
                protocol = proxy.xpath(parser['postion']['protocol'])[0].text
                if protocol.lower().find('https') != -1:
                    protocol = 1
                else:
                    protocol = 0
            else:
                protocol = 0

            proxy = {
                'ip': ip,
                'port': int(port),
                'ip_type': int(type),
                'protocol': int(protocol),
                'speed': 100
            }
            proxylist.append(proxy)

        return proxylist
