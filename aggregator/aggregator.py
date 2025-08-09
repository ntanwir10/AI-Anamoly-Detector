import os
import time
from typing import List

import redis

REDIS_HOST = os.getenv('REDIS_HOST', 'redis-stack')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
INTERVAL_SECONDS = int(os.getenv('INTERVAL_SECONDS', '5'))

IMPORTANT_ENDPOINTS: List[str] = [
    'GET:/api/data',
    'GET:/api/error',
]
STATUS_CODES: List[str] = ['200', '500', '599']


def cms_query(r: redis.Redis, key: str, items: List[str]) -> List[int]:
    try:
        res = r.execute_command('CMS.QUERY', key, *items)
        return [int(x) for x in res]
    except Exception:
        return [0 for _ in items]


def normalize(values: List[int]) -> List[float]:
    total = float(sum(values))
    if total == 0.0:
        return [0.0 for _ in values]
    return [v / total for v in values]


def write_stream(r: redis.Redis, vec: List[float]) -> None:
    data = '[' + ','.join([str(round(x, 6)) for x in vec]) + ']'
    r.xadd('system-fingerprints', {'data': data})


def reset_sketches(r: redis.Redis) -> None:
    try:
        r.delete('endpoint-frequency')
        r.execute_command('CMS.INITBYPROB', 'endpoint-frequency', 0.001, 0.99)
    except Exception:
        pass
    try:
        r.delete('status-codes')
        r.execute_command('CMS.INITBYPROB', 'status-codes', 0.001, 0.99)
    except Exception:
        pass


def tick(r: redis.Redis) -> None:
    endpoint_counts = cms_query(r, 'endpoint-frequency', IMPORTANT_ENDPOINTS)
    status_counts = cms_query(r, 'status-codes', STATUS_CODES)
    vec = normalize(endpoint_counts) + normalize(status_counts)
    write_stream(r, vec)
    reset_sketches(r)


def main():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    while True:
        try:
            tick(r)
        except Exception as e:
            print('Aggregator tick failed:', e)
        time.sleep(INTERVAL_SECONDS)


if __name__ == '__main__':
    main()


