# coding:utf-8
import multiprocessing

from multiprocessing import Queue
from gevent import monkey
from gevent.pool import Pool
monkey.patch_all()


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


def cocurrent(func, items, process_num, coroutine_num):
    queue = Queue()
    pieces = average_cut_list(items, process_num)
    processes = []
    for piece in pieces:
        process = multiprocessing.Process(target=process_with_coroutine, args=(func, piece, queue, coroutine_num))
        process.start()
        processes.append(process)
    for process in processes:
        process.join()

    results = []
    for _ in processes:
        result = queue.get()
        results.extend(result)
    return results


def process_with_coroutine(func, piece, queue, coroutine_num):
    validate_pool = Pool(coroutine_num)
    result = validate_pool.map(func, piece)
    queue.put(result)


def average_cut_list(source_list, count):
    func = lambda A, n: [A[i:i + n] for i in range(0, len(A), n)]
    return func(source_list, count)
