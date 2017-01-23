# coding:utf-8
import random
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
        resp = self.download(url)
        try:
            return self.parse(resp, parser)
        except Exception as e:
            self.logger.error(str(e))

    def download(self, url):
        count = 0
        while True:
            try:
                if count == 0:
                    resp = self.request.get(url=url, timeout=CRAWL_TIMEOUT)
                elif (count > 0) and (count <= MAX_RETRY_TIMES):
                    proxy = self.get_proxy()
                    resp = self.request.get(url=url, timeout=CRAWL_TIMEOUT, proxies=proxy)
                elif count > MAX_RETRY_TIMES:
                    self.logger.error('retry connect url {0} {1} times, but is failed.'.format(url, MAX_RETRY_TIMES))
                    break
                if not resp.ok:
                    raise ValueError('response status code is {}, not 200', resp.status_code)
                self.logger.info('connect url {} success.'.format(url))
                return resp.text
            except Exception as e:
                count += 1
                self.logger.exception(e)

    def parse(self, document, parser):
        if parser['type'] != 'xpath':
            raise ValueError('type of parser is {0}, not xpath'.format(parser['type']))
        proxies = []
        root = etree.HTML(document)
        pattern = root.xpath(parser['pattern'])

        for position in pattern:
            ip = position.xpath(parser['position']['ip'])[0].text
            port = position.xpath(parser['position']['port'])[0].text
            ip_type = position.xpath(parser['position']['type'])[0].text
            if ip_type.find(u'高匿') != -1:
                ip_type = '高匿'
            else:
                ip_type = '匿名'
            if parser['position']['protocol'] != '':
                protocol = position.xpath(parser['position']['protocol'])[0].text
                if protocol.lower().find('https') == -1:
                    protocol = 'HTTPS'
                else:
                    protocol = 'HTTP'
            else:
                protocol = 'HTTP'

            proxy = {'ip': ip, 'port': int(port), 'ip_type': ip_type, 'protocol': protocol, 'speeds': []}
            proxies.append(proxy)
        return proxies

    def get_proxy(self):
        if len(self.proxies) == 0:
            proxies = random.choice(IpProxies.objects.all()).get_proxies()
            proxies = ranking(proxies)
            for proxy in proxies:
                self.proxies.append({
                    'http': 'http://{}'.format(proxy[0])
                })
        return self.proxies.pop()

