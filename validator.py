# coding:utf-8
import time
import requests

from gevent.pool import Pool
from config import HEADER, TEST_URL, TIMEOUT, THREADNUM


class Validator(object):
    def __init__(self):
        self.request = requests.Session()
        self.request.adapters.DEFAULT_RETRIES = 5
        self.request.headers.update(HEADER)
        self.detect_pool = Pool(THREADNUM)

    def check_is_active(self, proxies):
        proxies = self.detect_pool.map(self.detect_list, proxies)
        return proxies

    def detect_list(self, proxy):
        ip = proxy['ip']
        port = proxy['port']
        proxies={"http": "http://%s:%s"%(ip,port)}
        start = time.time()
        try:
            r = requests.get(url=TEST_URL, timeout=TIMEOUT, proxies=proxies)
            if not r.ok:
                print 'fail ip =%s'%ip
                proxy = None
            else:
                speed = round(time.time()-start,2)
                print 'success ip =%s,speed=%s'%(ip,speed)
                proxy['speed']=speed
        except Exception as e:
                print 'fail ip =%s'%ip
                proxy = None
        return proxy
