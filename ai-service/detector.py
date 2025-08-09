import os
import time
from typing import List

import numpy as np
import redis
from sklearn.ensemble import IsolationForest

REDIS_HOST = os.getenv('REDIS_HOST', 'redis-stack')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

STREAM_KEY = 'system-fingerprints'
PUBSUB_CHANNEL = 'alerts'


def read_stream_blocking(r: redis.Redis, last_id: str):
    resp = r.xread({STREAM_KEY: last_id}, count=1, block=10_000)
    if not resp:
        return last_id, None
    _, entries = resp[0]
    entry_id, fields = entries[0]
    return entry_id, fields


def parse_vector(fields) -> List[float]:
    raw = fields.get('data')
    if not raw:
        return []
    try:
        raw = raw.strip()
        if raw.startswith('[') and raw.endswith(']'):
            raw = raw[1:-1]
        return [float(x) for x in raw.split(',') if x.strip()]
    except Exception:
        return []


def main():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    # Training phase: collect ~60 fingerprints (~5 minutes at 5s interval)
    training_vectors: List[List[float]] = []
    last_id = '$'
    start = time.time()
    training_target = int(os.getenv('TRAINING_TARGET', '10'))

    print('AI service: collecting training data...')
    while len(training_vectors) < training_target and time.time() - start < 600:
        last_id, fields = read_stream_blocking(r, last_id)
        if not fields:
            continue
        vec = parse_vector(fields)
        if vec:
            training_vectors.append(vec)
            print(f'Collected {len(training_vectors)}/{training_target}')

    if not training_vectors:
        print('No training data collected; exiting.')
        return

    X_train = np.array(training_vectors)
    model = IsolationForest(contamination='auto', random_state=42)
    model.fit(X_train)
    print('Model training complete; entering detection mode.')

    # Detection loop
    while True:
        last_id, fields = read_stream_blocking(r, last_id)
        if not fields:
            continue
        vec = parse_vector(fields)
        if not vec:
            continue
        X_new = np.array([vec])
        pred = model.predict(X_new)  # 1 normal, -1 anomaly
        if pred[0] == -1:
            msg = 'Anomaly detected: Outlier fingerprint observed.'
            r.publish(PUBSUB_CHANNEL, msg)
            print(msg)


if __name__ == '__main__':
    main()


