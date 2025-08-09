import os
import redis

REDIS_HOST = os.getenv('REDIS_HOST', 'redis-stack')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

SCRIPT_FILE = os.path.join(os.path.dirname(__file__), 'script.py')


def main():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    with open(SCRIPT_FILE, 'r') as f:
        code = f.read()
    try:
        res = r.execute_command('RG.PYEXECUTE', code)
        print('RedisGears script registered:', res)
    except redis.ResponseError as e:
        print('Failed to register RedisGears script:', e)


if __name__ == '__main__':
    main()


