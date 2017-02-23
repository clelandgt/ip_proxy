# -*- coding:utf-8 -*-
import json

from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseForbidden
from ip_proxy.models import IpProxies
from ip_proxy.utils import ranking
from api.utils import render_json_only


REDIS_KEY = 'ip'
NEVER_REDIS_TIMEOUT = 60 * 2  # 缓存2分钟更新一次


@csrf_exempt
@render_json_only
def ip_proxy(request):
    if request.method == 'POST':
        try:
            data = request.POST
            count = int(data['count'])
        except:
            return u'请求失败'
    else:
        count = None
    proxies = get_proxy()
    return proxies[:count]


def get_proxy():
    proxies = cache.get(REDIS_KEY)
    if proxies:
        return json.loads(proxies)
    if not proxies or (len(proxies) == 0):
        proxies = []
        objs = IpProxies.objects.all()
        for obj in objs:
            proxies.append(json.loads(obj.to_json()))
        proxies = ranking(proxies)
        proxies = [item[0] for item in proxies]
        cache.set(REDIS_KEY, json.dumps(proxies), NEVER_REDIS_TIMEOUT)
    return proxies

