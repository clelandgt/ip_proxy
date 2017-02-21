# coding:utf-8
import requests
import logging

from lxml import etree
from settings import HEADER, CRAWL_TIMEOUT, MAX_RETRY_TIMES
from models import IpProxies
from utils import ranking


class Crawl(object):
    def __init__(self):
        self.proxies = []
        self.request = requests.Session()
        self.request.headers.update(HEADER)
        self.request.adapters.DEFAULT_RETRIES = 5
        self.logger = logging.getLogger(__name__)

    def run(self, url, parser):
        try:
            resp = self.download(url)
            return self.parse(resp, parser)
        except Exception as e:
            self.logger.exception(e)
            return []

    def download(self, url):
        for index in xrange(1, MAX_RETRY_TIMES+1):
            try:
                resp = self.request.get(url=url, timeout=CRAWL_TIMEOUT)
                if index != 1:
                    proxy = self.get_proxy()
                    resp = self.request.get(url=url, timeout=CRAWL_TIMEOUT, proxies=proxy)
                if not resp.ok:
                    raise ValueError('response status code is {}, not 200'.format(resp.status_code))
                self.logger.info('connect url {} success.'.format(url))
                return resp.text
            except Exception as e:
                self.logger.error(e)
                if index == MAX_RETRY_TIMES:
                    self.logger.error('retry connect url {0} {1} times, but is failed.'.format(url, MAX_RETRY_TIMES))
                    raise e

    @staticmethod
    def parse(document, parser):
        proxies = []
        root = etree.HTML(document)
        pattern = root.xpath(parser['pattern'])

        for position in pattern:
            ip = position.xpath(parser['position']['ip'])[0].text
            port = position.xpath(parser['position']['port'])[0].text
            ip_type = position.xpath(parser['position']['type'])[0].text
            ip_type = '高匿' if ip_type.find(u'高匿') != -1 else '匿名'
            proxies.append({'ip': ip, 'port': int(port), 'ip_type': ip_type, 'protocol': '', 'speeds': []})
        return proxies

    def get_proxy(self):
        if len(self.proxies) == 0:
            proxies = IpProxies.objects.all()
            proxies = ranking(proxies)
            self.proxies = [{'http': 'http://{}'.format(proxy[0])} for proxy in proxies]
        return self.proxies.pop()
