# RedisGears Python script to aggregate metrics periodically

from redisgears import executeCommand as redis_cmd
from redisgears import log as log

IMPORTANT_ENDPOINTS = [
    'GET:/api/data',
    'GET:/api/error',
]

STATUS_CODES = ['200', '500', '599']


def read_count_min_sketch(key: str, items: list[str]) -> list[int]:
    # Returns estimated counts for items; if item not found, CMS.QUERY returns 0
    res = redis_cmd('CMS.QUERY', key, *items)
    return [int(x) for x in res]


def normalize(values: list[int]) -> list[float]:
    total = float(sum(values))
    if total == 0.0:
        return [0.0 for _ in values]
    return [v / total for v in values]


def build_fingerprint() -> list[float]:
    try:
        endpoint_counts = read_count_min_sketch('endpoint-frequency', IMPORTANT_ENDPOINTS)
    except Exception as e:
        log(f'CMS read failed (endpoint-frequency): {e}')
        endpoint_counts = [0 for _ in IMPORTANT_ENDPOINTS]
    try:
        status_counts = read_count_min_sketch('status-codes', STATUS_CODES)
    except Exception as e:
        log(f'CMS read failed (status-codes): {e}')
        status_counts = [0 for _ in STATUS_CODES]

    features = normalize(endpoint_counts) + normalize(status_counts)
    return features


def write_to_stream(vec: list[float]) -> None:
    data = '[' + ','.join([str(round(x, 6)) for x in vec]) + ']'
    try:
        redis_cmd('XADD', 'system-fingerprints', '*', 'data', data)
    except Exception as e:
        log(f'XADD failed: {e}')


def reset_sketches() -> None:
    # Re-initialize sketches to avoid ever-growing counts
    try:
        redis_cmd('DEL', 'endpoint-frequency')
        redis_cmd('CMS.INITBYPROB', 'endpoint-frequency', 0.001, 0.99)
    except Exception as e:
        log(f'Failed to reset endpoint-frequency: {e}')
    try:
        redis_cmd('DEL', 'status-codes')
        redis_cmd('CMS.INITBYPROB', 'status-codes', 0.001, 0.99)
    except Exception as e:
        log(f'Failed to reset status-codes: {e}')


def aggregate_tick():
    vec = build_fingerprint()
    write_to_stream(vec)
    reset_sketches()


def register_periodic(seconds: int):
    # Use a command trigger and a time event to self-trigger periodically
    from redisgears import GearsBuilder
    builder = GearsBuilder('CommandReader')
    builder.map(lambda x: aggregate_tick())
    builder.register(trigger='aggregate_tick', mode='async_local')

    # schedule the trigger periodically
    # The following uses RG.TIMER stateless API available in RedisGears to create a periodic timer
    try:
        redis_cmd('RG.TIMER', seconds, 'aggregate_tick')
    except Exception as e:
        log(f'RG.TIMER failed: {e}')


def main():
    # Register periodic run every 5 seconds
    register_periodic(5)


main()


