# coding:utf-8


def ranking(proxies, count=None):
    """当前根据成功率单一指标进行ip排名
    当times<5, 不进入ip排名
    times>=5. 取最后10次的数据求平均值

    TODO: 评估指标: 成功率, 平均数据, ip速度的稳定性
    """
    if not proxies: return []
    failed_flag = 0
    items = []
    for proxy in proxies:
        speeds = proxy['speeds']
        speeds_len = len(speeds)
        if speeds_len <= 5:
            continue
        failed_count = speeds.count(failed_flag)
        success_rate = 1 - (float(failed_count) / speeds_len)
        ip_addr = '{ip}:{port}'.format(ip=proxy['ip'], port=proxy['port'])
        items.append((ip_addr, success_rate))
    proxies = sorted(items, key=lambda item: item[1], reverse=True)
    return proxies[:count]
