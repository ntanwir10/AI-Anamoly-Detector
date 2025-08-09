import os
import json
from flask import Flask, request, Response
import requests
import redis
from tenacity import retry, stop_after_attempt, wait_exponential

REDIS_HOST = os.getenv('REDIS_HOST', 'redis-stack')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

app = Flask(__name__)


def get_redis_client() -> redis.Redis:
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=0.5, min=0.5, max=5))
def init_structures(r: redis.Redis) -> None:
    try:
        r.execute_command('CF.RESERVE', 'service-calls', 10000)
    except redis.ResponseError:
        pass
    try:
        r.execute_command('CMS.INITBYPROB', 'endpoint-frequency', 0.001, 0.99)
    except redis.ResponseError:
        pass
    try:
        r.execute_command('CMS.INITBYPROB', 'status-codes', 0.001, 0.99)
    except redis.ResponseError:
        pass


redis_client = get_redis_client()
try:
    init_structures(redis_client)
except Exception as e:
    print(f"Failed to initialize Redis structures: {e}")


@app.route('/forward/<target_service>/<path:target_path>', methods=['GET'])
def forward(target_service: str, target_path: str):
    method = request.method
    source_service = 'service-a'
    target_url = f'http://{target_service}:3000/{target_path}'

    try:
        upstream = requests.request(method, target_url, timeout=5)
        status_code = upstream.status_code
        endpoint_key = f"{method}:{'/' + target_path.strip('/')}"

        try:
            # Update probabilistic structures
            redis_client.execute_command('CF.ADD', 'service-calls', f'{source_service}:{target_service}')
            redis_client.execute_command('CMS.INCRBY', 'endpoint-frequency', endpoint_key, 1)
            redis_client.execute_command('CMS.INCRBY', 'status-codes', str(status_code), 1)
        except Exception as e:
            print(f"Redis update failed: {e}")

        return Response(upstream.content, status=status_code, content_type=upstream.headers.get('Content-Type', 'text/plain'))
    except requests.RequestException as e:
        try:
            redis_client.execute_command('CMS.INCRBY', 'status-codes', '599', 1)
        except Exception:
            pass
        return Response(json.dumps({"error": str(e)}), status=502, content_type='application/json')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000)


