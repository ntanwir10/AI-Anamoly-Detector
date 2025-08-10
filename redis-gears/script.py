# RedisGears Python script to aggregate metrics periodically

from redisgears import executeCommand as redis_cmd
from redisgears import log as log
from typing import List

IMPORTANT_ENDPOINTS = [
    "GET:/api/data",
    "GET:/api/error",
]

STATUS_CODES = ["200", "500", "599"]


def read_count_min_sketch(key: str, items: List[str]) -> List[int]:
    # Returns estimated counts for items; if item not found, CMS.QUERY returns 0
    res = redis_cmd("CMS.QUERY", key, *items)
    return [int(x) for x in res]


def normalize(values: List[int]) -> List[float]:
    total = float(sum(values))
    if total == 0.0:
        return [0.0 for _ in values]
    return [v / total for v in values]


def build_fingerprint() -> List[float]:
    try:
        endpoint_counts = read_count_min_sketch(
            "endpoint-frequency", IMPORTANT_ENDPOINTS
        )
    except Exception as e:
        log(f"CMS read failed (endpoint-frequency): {e}")
        endpoint_counts = [0 for _ in IMPORTANT_ENDPOINTS]
    try:
        status_counts = read_count_min_sketch("status-codes", STATUS_CODES)
    except Exception as e:
        log(f"CMS read failed (status-codes): {e}")
        status_counts = [0 for _ in STATUS_CODES]

    features = normalize(endpoint_counts) + normalize(status_counts)
    return features


def write_to_stream(vec: List[float]) -> None:
    data = "[" + ",".join([str(round(x, 6)) for x in vec]) + "]"
    try:
        redis_cmd("XADD", "system-fingerprints", "*", "data", data)
    except Exception as e:
        log(f"XADD failed: {e}")


def aggregate_tick():
    vec = build_fingerprint()
    write_to_stream(vec)
    log("Aggregation completed")


def main():
    # Initialize sketches if they don't exist
    try:
        redis_cmd("CMS.INITBYDIM", "endpoint-frequency", 100000, 10)
        redis_cmd("CMS.INITBYDIM", "status-codes", 100000, 10)
        log("Initialized Count-Min Sketches")
    except Exception as e:
        log(f"Failed to initialize sketches: {e}")

    # Run one aggregation cycle
    aggregate_tick()
    log("Script execution completed")


main()
