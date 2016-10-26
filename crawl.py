# coding:utf-8
import random
import requests
import logging
from lxml import etree
from requests.exceptions import RequestException
from config import HEADER, CRAWL_TIMEOUT
from models import IpProxies


class Crawl(object):
    def __init__(self):
        self.parser = None
        self.request = requests.Session()
        self.request.headers.update(HEADER)
        self.request.adapters.DEFAULT_RETRIES = 5
        self.logger = logging.getLogger(__name__)

    def run(self, url, parser):
        try:
            self.parser = parser
            resp = self.download(url)
            return self.parse(resp)
        except Exception as e:
            self.logger.error(str(e))

    def download(self, url):
        try:
            resp = self.request.get(url=url, timeout=CRAWL_TIMEOUT)
            if not resp.ok:
                raise
        except Exception as e:
            self.logger.error('crawl failed, exception: {0}'.format(str(e)))
            try:
                proxies = random.choice(IpProxies.objects.all()).get_proxies()
                resp = self.request.get(url=url, timeout=CRAWL_TIMEOUT,
                                        proxies=proxies, verify=False)
            except Exception as e:
                self.logger.error('crawl failed, exception: {0}'.format(str(e)))
        resp.encoding = 'gbk'
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
                type = '高匿'
            else:
                type = '匿名'
            if len(parser['postion']['protocol']) > 0:
                protocol = proxy.xpath(parser['postion']['protocol'])[0].text
                if protocol.lower().find('https') != -1:
                    protocol = 'HTTP'
                else:
                    protocol = 'HTTPS'
            else:
                protocol = 'HTTPS'

            proxy = {
                'ip': ip,
                'port': int(port),
                'ip_type': type,
                'protocol': protocol,
                'speeds': []
            }
            proxylist.append(proxy)
        return proxylist
