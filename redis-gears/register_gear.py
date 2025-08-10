import os
import redis
import traceback

REDIS_HOST = os.getenv("REDIS_HOST", "redis-stack")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

SCRIPT_FILE = os.path.join(os.path.dirname(__file__), "script.py")


def main():
    print(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}")
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    # Test connection first
    try:
        r.ping()
        print("Successfully connected to Redis")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        return

    # Read and validate script
    try:
        with open(SCRIPT_FILE, "r") as f:
            code = f.read()
        print(f"Successfully read script file: {SCRIPT_FILE}")
        print(f"Script length: {len(code)} characters")
    except Exception as e:
        print(f"Failed to read script file: {e}")
        return

    # Try to execute the script
    try:
        print("Attempting to register RedisGears script...")
        res = r.execute_command("rg.pyexecute", code)
        print("RedisGears script registered successfully:", res)
    except redis.ResponseError as e:
        print("Redis ResponseError during script registration:", e)
        print("Full error details:", str(e))
    except Exception as e:
        print("Unexpected error during script registration:", e)
        print("Full traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    main()
