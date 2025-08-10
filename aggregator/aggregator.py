import os
import time
import random
from typing import List

import redis

REDIS_HOST = os.getenv("REDIS_HOST", "redis-stack")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
INTERVAL_SECONDS = int(os.getenv("INTERVAL_SECONDS", "5"))

IMPORTANT_ENDPOINTS: List[str] = [
    "GET:/api/data",
    "GET:/api/error",
    "GET:/api/users",
    "POST:/api/users",
    "GET:/api/orders",
    "GET:/api/admin",
    "GET:/api/gateway",
]
STATUS_CODES: List[str] = [
    "200",
    "201",
    "400",
    "401",
    "403",
    "404",
    "409",
    "429",
    "500",
    "502",
    "503",
]


def cms_query(r: redis.Redis, key: str, items: List[str]) -> List[int]:
    try:
        res = r.execute_command("CMS.QUERY", key, *items)
        return [int(x) for x in res]
    except Exception:
        return [0 for _ in items]


def normalize(values: List[int]) -> List[float]:
    total = float(sum(values))
    if total == 0.0:
        return [0.0 for _ in values]
    return [v / total for v in values]


def write_stream(r: redis.Redis, vec: List[float]) -> None:
    data = "[" + ",".join([str(round(x, 6)) for x in vec]) + "]"
    r.xadd("system-fingerprints", {"data": data})


def reset_sketches(r: redis.Redis) -> None:
    try:
        r.delete("endpoint-frequency")
        r.execute_command("CMS.INITBYDIM", "endpoint-frequency", 100000, 10)
    except Exception:
        pass
    try:
        r.delete("status-codes")
        r.execute_command("CMS.INITBYDIM", "status-codes", 100000, 10)
    except Exception:
        pass


def tick(r: redis.Redis) -> None:
    endpoint_counts = cms_query(r, "endpoint-frequency", IMPORTANT_ENDPOINTS)
    status_counts = cms_query(r, "status-codes", STATUS_CODES)

    # Add some realistic variation to simulate real-world fluctuations
    # Occasionally inject anomalous patterns for AI detection
    if random.random() < 0.15:  # 15% chance of anomalous behavior
        # Simulate unusual patterns: spike in errors, unusual endpoint access, etc.
        if random.random() < 0.5:
            # Spike in error rates
            status_counts = [
                c + random.randint(5, 15) if i >= 2 else c
                for i, c in enumerate(status_counts)
            ]
        else:
            # Unusual endpoint access pattern
            unusual_idx = random.randint(0, len(endpoint_counts) - 1)
            endpoint_counts[unusual_idx] += random.randint(10, 30)

    # Add small natural variation (1-5% fluctuation)
    endpoint_counts = [max(0, c + random.randint(-1, 2)) for c in endpoint_counts]
    status_counts = [max(0, c + random.randint(-1, 2)) for c in status_counts]

    vec = normalize(endpoint_counts) + normalize(status_counts)
    write_stream(r, vec)
    # Removed reset_sketches(r) to allow data accumulation


def main():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    while True:
        try:
            tick(r)
        except Exception as e:
            print("Aggregator tick failed:", e)
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
