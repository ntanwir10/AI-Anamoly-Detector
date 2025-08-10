import os
import json
import time
from flask import Flask, request, Response
import requests
import redis
from tenacity import retry, stop_after_attempt, wait_exponential

REDIS_HOST = os.getenv("REDIS_HOST", "redis-stack")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

app = Flask(__name__)


def get_redis_client() -> redis.Redis:
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


@retry(
    stop=stop_after_attempt(5), wait=wait_exponential(multiplier=0.5, min=0.5, max=5)
)
def init_structures(r: redis.Redis) -> None:
    try:
        r.execute_command("CF.RESERVE", "service-calls", 1000000)
    except redis.ResponseError:
        pass
    try:
        r.execute_command("CMS.INITBYDIM", "endpoint-frequency", 100000, 10)
    except redis.ResponseError:
        pass
    try:
        r.execute_command("CMS.INITBYDIM", "status-codes", 100000, 10)
    except redis.ResponseError:
        pass


redis_client = get_redis_client()
try:
    init_structures(redis_client)
except Exception as e:
    print(f"Failed to initialize Redis structures: {e}")


@app.route("/")
def root():
    return {
        "service": "Data Collector",
        "status": "running",
        "endpoints": {
            "forward": "/forward/<target_service>/<target_path> (replace placeholders with actual values, e.g., /forward/service-b/api/data)",
            "health": "/health",
            "metrics": "/metrics",
        },
        "description": "Data collection service for AI Anomaly Detector - forwards requests and tracks metrics",
    }


@app.route("/health")
def health_check():
    try:
        # Test Redis connection
        redis_client.ping()
        return {"status": "healthy", "redis": "connected", "timestamp": time.time()}
    except Exception as e:
        return {
            "status": "unhealthy",
            "redis": "disconnected",
            "error": str(e),
            "timestamp": time.time(),
        }, 503


@app.route("/test-debug")
def test_debug():
    print("DEBUG: Test endpoint called successfully!")
    return {"message": "Debug endpoint working", "timestamp": time.time()}


@app.route("/metrics")
def get_metrics():
    try:
        # Get basic metrics from Redis
        endpoint_count = redis_client.execute_command("CMS.INFO", "endpoint-frequency")[
            5
        ]  # count field
        status_count = redis_client.execute_command("CMS.INFO", "status-codes")[5]
        return {
            "endpoint_requests": endpoint_count,
            "status_code_events": status_count,
            "timestamp": time.time(),
        }
    except Exception as e:
        return {"error": str(e), "timestamp": time.time()}, 500


@app.route(
    "/forward/<target_service>/<path:target_path>",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
def forward(target_service: str, target_path: str):
    # Debug logging
    print("========== FORWARD FUNCTION CALLED ==========")
    print(
        f"DEBUG: Received target_service='{target_service}', target_path='{target_path}'"
    )
    print(
        f"DEBUG: target_service type: {type(target_service)}, target_path type: {type(target_path)}"
    )
    print(f"DEBUG: Request path: {request.path}")
    print(f"DEBUG: Request method: {request.method}")
    print("=" * 46)

    # Validate that template placeholders weren't used literally
    if (
        target_service in ["<target_service>", "target_service"]
        or target_path in ["<target_path>", "target_path"]
        or target_service.startswith("<")
        or target_service.endswith(">")
        or target_path.startswith("<")
        or target_path.endswith(">")
    ):
        return Response(
            json.dumps(
                {
                    "error": "Invalid service or path format",
                    "message": f"Replace '<target_service>' with actual service name (e.g., 'service-b') and '<target_path>' with actual path (e.g., 'api/data')",
                    "received": f"service='{target_service}', path='{target_path}'",
                    "example": "GET /forward/service-b/api/data",
                    "documentation": "See README.md for correct usage examples",
                }
            ),
            status=400,
            content_type="application/json",
        )

    method = request.method
    source_service = "service-a"
    target_url = f"http://{target_service}:3000/{target_path}"

    try:
        # Forward the request with proper headers and body
        headers = dict(request.headers)
        headers.pop("Host", None)  # Remove Host header to avoid conflicts

        # Forward request data/json for POST/PUT requests
        request_kwargs = {"timeout": 5, "headers": headers}

        if method in ["POST", "PUT", "PATCH"] and request.data:
            if request.is_json:
                request_kwargs["json"] = request.get_json()
            else:
                request_kwargs["data"] = request.data

        upstream = requests.request(method, target_url, **request_kwargs)
        status_code = upstream.status_code
        endpoint_key = f"{method}:{'/' + target_path.strip('/')}"

        try:
            # Update probabilistic structures
            redis_client.execute_command(
                "CF.ADD", "service-calls", f"{source_service}:{target_service}"
            )
            redis_client.execute_command(
                "CMS.INCRBY", "endpoint-frequency", endpoint_key, 1
            )
            redis_client.execute_command(
                "CMS.INCRBY", "status-codes", str(status_code), 1
            )
        except Exception as e:
            print(f"Redis update failed: {e}")

        return Response(
            upstream.content,
            status=status_code,
            content_type=upstream.headers.get("Content-Type", "text/plain"),
        )
    except requests.RequestException as e:
        try:
            redis_client.execute_command("CMS.INCRBY", "status-codes", "599", 1)
        except Exception:
            pass
        return Response(
            json.dumps({"error": str(e)}), status=502, content_type="application/json"
        )


# Handle the specific case where someone uses template syntax literally
@app.errorhandler(404)
def handle_template_syntax_error(e):
    # Check if the path contains template syntax
    if request.path.startswith("/forward/") and (
        "<" in request.path or ">" in request.path
    ):
        return Response(
            json.dumps(
                {
                    "error": "Invalid service or path format",
                    "message": "Replace '<target_service>' with actual service name (e.g., 'service-b') and '<target_path>' with actual path (e.g., 'api/data')",
                    "received_path": request.path,
                    "example": "GET /forward/service-b/api/data",
                    "documentation": "See README.md for correct usage examples",
                }
            ),
            status=400,
            content_type="application/json",
        )
    # Return default 404 for other cases
    return Response(
        json.dumps({"error": "Not Found", "path": request.path}),
        status=404,
        content_type="application/json",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000)
