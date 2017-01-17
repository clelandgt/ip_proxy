# -*- coding:utf-8 -*-
import json
import operator

from django.views.decorators.csrf import csrf_exempt
from ip_proxy.models import IpProxies
from api.utils import render_json_only
from django.core.cache import cache


DEBUG = False
REDIS_KEY = 'ip'
NEVER_REDIS_TIMEOUT = 2 * 60 # 缓存2分钟更新一次


@csrf_exempt
@render_json_only
def ip_proxy(request):
    proxies = cache.get(REDIS_KEY)
    if not proxies:
        proxies = get_proxy()
        if not DEBUG:
            proxies_tmp = []
            for proxy in proxies:
                proxies_tmp.append(proxy[0])
            proxies = proxies_tmp
        cache.set(REDIS_KEY, json.dumps(proxies), NEVER_REDIS_TIMEOUT)
    else:
        proxies = json.loads(proxies)
    if request.method == 'GET':
        return proxies
    elif request.method == 'POST':
        try:
            data = request.POST
            count = int(data['count'])
            return proxies[:count]
        except:
            return []



def get_proxy():
    proxies = []
    proxy_objs = IpProxies.objects.all()
    for proxy_obj in proxy_objs:
        proxy_json = json.loads(proxy_obj.to_json())
        proxies.append(proxy_json)
    return ip_rank(proxies)


def ip_rank(proxies, count=None):
    '''当前根据成功率单一指标进行ip排名
    当times<5, 不进入ip排名
    times>=5. 取最后10次的数据求平均值

    TODO: 评估指标: 成功率, 平均数据, ip速度的稳定性
    '''
    FAIL_PLACEHOLDER = 0
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
    sort_proxies = pre_proxies[::-1][:count]
    return sort_proxies