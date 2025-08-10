import os
import json
import time
from flask import Flask, request, Response, jsonify
import requests
import redis
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime
import logging

# Enhanced Data Collector with Real-World Integration Support

REDIS_HOST = os.getenv("REDIS_HOST", "redis-stack")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
API_KEY = os.getenv("API_KEY", None)  # Optional API key for security

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


def get_redis_client() -> redis.Redis:
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def validate_api_key(req):
    """Validate API key if configured"""
    if not API_KEY:
        return True

    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False

    return auth_header[7:] == API_KEY


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
    try:
        r.execute_command("CMS.INITBYDIM", "response-times", 100000, 10)
    except redis.ResponseError:
        pass
    try:
        r.execute_command("CMS.INITBYDIM", "business-metrics", 100000, 10)
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
        "service": "Enhanced Data Collector",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "metrics": "POST /api/metrics - Send custom application metrics",
            "business_metrics": "POST /api/business-metrics - Send business KPI metrics",
            "logs": "POST /api/logs - Send log-based metrics",
            "batch": "POST /api/batch - Send multiple metrics at once",
            "forward": "GET /forward/<target_service>/<target_path> - Legacy forwarding (replace placeholders, e.g., /forward/service-b/api/data)",
            "health": "GET /health - Health check",
            "metrics_endpoint": "GET /metrics - Prometheus metrics",
            "config": "GET /config - View current configuration",
        },
        "description": "Enhanced data collection service for AI Anomaly Detector with real-world integration support",
        "authentication": (
            "Bearer token required" if API_KEY else "No authentication required"
        ),
    }


@app.route("/health")
def health_check():
    try:
        redis_client.ping()
        return {
            "status": "healthy",
            "redis": "connected",
            "timestamp": time.time(),
            "version": "2.0.0",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "redis": "disconnected",
            "error": str(e),
            "timestamp": time.time(),
        }, 503


@app.route("/config")
def get_config():
    """Get current system configuration"""
    return {
        "redis": {
            "host": REDIS_HOST,
            "port": REDIS_PORT,
            "connected": True if redis_client.ping() else False,
        },
        "security": {"api_key_required": API_KEY is not None},
        "structures": {
            "service_calls": "Cuckoo Filter (1M capacity)",
            "endpoint_frequency": "Count-Min Sketch (100K x 10)",
            "status_codes": "Count-Min Sketch (100K x 10)",
            "response_times": "Count-Min Sketch (100K x 10)",
            "business_metrics": "Count-Min Sketch (100K x 10)",
        },
    }


@app.route("/api/metrics", methods=["POST"])
def receive_metrics():
    """
    Receive custom application metrics

    Example payload:
    {
        "service": "user-service",
        "endpoint": "GET:/api/users",
        "metrics": {
            "response_time": 150,
            "status_code": 200,
            "payload_size": 1024
        },
        "timestamp": "2024-01-20T10:30:00Z"
    }
    """
    if not validate_api_key(request):
        return jsonify({"error": "Invalid API key"}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON payload required"}), 400

        service = data.get("service", "unknown")
        endpoint = data.get("endpoint", "unknown")
        metrics = data.get("metrics", {})
        timestamp = data.get("timestamp", datetime.utcnow().isoformat())

        # Update Redis structures
        endpoint_key = f"{endpoint}"
        status_code = str(metrics.get("status_code", 200))
        response_time = metrics.get("response_time", 0)

        # Track service communication (if source service provided)
        source_service = data.get("source_service")
        if source_service:
            redis_client.execute_command(
                "CF.ADD", "service-calls", f"{source_service}:{service}"
            )

        # Track endpoint frequency
        redis_client.execute_command(
            "CMS.INCRBY", "endpoint-frequency", endpoint_key, 1
        )

        # Track status codes
        redis_client.execute_command("CMS.INCRBY", "status-codes", status_code, 1)

        # Track response times (bucketed)
        time_bucket = (
            "fast"
            if response_time < 100
            else "medium" if response_time < 500 else "slow"
        )
        redis_client.execute_command("CMS.INCRBY", "response-times", time_bucket, 1)

        # Store additional metrics as JSON in a stream for detailed analysis
        redis_client.xadd(
            "detailed-metrics",
            {
                "service": service,
                "endpoint": endpoint,
                "metrics": json.dumps(metrics),
                "timestamp": timestamp,
            },
        )

        logging.info(f"Received metrics from {service} - {endpoint} - {status_code}")

        return jsonify(
            {
                "status": "success",
                "message": "Metrics received and processed",
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        logging.error(f"Error processing metrics: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/business-metrics", methods=["POST"])
def receive_business_metrics():
    """
    Receive business-level metrics for anomaly detection

    Example payload:
    {
        "metric_name": "daily_revenue",
        "value": 45000,
        "expected_range": [40000, 60000],
        "timestamp": "2024-01-20T00:00:00Z",
        "metadata": {
            "currency": "USD",
            "region": "US-WEST"
        }
    }
    """
    if not validate_api_key(request):
        return jsonify({"error": "Invalid API key"}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON payload required"}), 400

        metric_name = data.get("metric_name")
        value = data.get("value")
        expected_range = data.get("expected_range", [])
        timestamp = data.get("timestamp", datetime.utcnow().isoformat())
        metadata = data.get("metadata", {})

        if not metric_name or value is None:
            return jsonify({"error": "metric_name and value are required"}), 400

        # Track business metric frequency
        redis_client.execute_command("CMS.INCRBY", "business-metrics", metric_name, 1)

        # Store detailed business metrics
        redis_client.xadd(
            "business-metrics-stream",
            {
                "metric_name": metric_name,
                "value": str(value),
                "expected_range": json.dumps(expected_range),
                "metadata": json.dumps(metadata),
                "timestamp": timestamp,
            },
        )

        # Check for immediate anomalies
        anomaly_detected = False
        if expected_range and len(expected_range) == 2:
            min_val, max_val = expected_range
            if value < min_val or value > max_val:
                anomaly_detected = True
                redis_client.publish(
                    "alerts",
                    f"Business metric anomaly: {metric_name} = {value} (expected: {min_val}-{max_val})",
                )

        logging.info(f"Business metric received: {metric_name} = {value}")

        return jsonify(
            {
                "status": "success",
                "message": "Business metrics received and processed",
                "anomaly_detected": anomaly_detected,
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        logging.error(f"Error processing business metrics: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/logs", methods=["POST"])
def receive_logs():
    """
    Receive log-based metrics for anomaly detection

    Example payload:
    {
        "log_level": "ERROR",
        "message": "Database connection timeout",
        "service": "payment-service",
        "timestamp": "2024-01-20T10:30:00Z",
        "context": {
            "user_id": "12345",
            "transaction_id": "tx_789"
        }
    }
    """
    if not validate_api_key(request):
        return jsonify({"error": "Invalid API key"}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON payload required"}), 400

        log_level = data.get("log_level", "INFO")
        message = data.get("message", "")
        service = data.get("service", "unknown")
        timestamp = data.get("timestamp", datetime.utcnow().isoformat())
        context = data.get("context", {})

        # Track log levels by service
        log_key = f"{service}:{log_level}"
        redis_client.execute_command("CMS.INCRBY", "endpoint-frequency", log_key, 1)

        # Store detailed logs
        redis_client.xadd(
            "log-metrics-stream",
            {
                "log_level": log_level,
                "message": message,
                "service": service,
                "context": json.dumps(context),
                "timestamp": timestamp,
            },
        )

        # Alert on ERROR/FATAL logs
        if log_level in ["ERROR", "FATAL", "CRITICAL"]:
            redis_client.publish(
                "alerts", f"Critical log detected in {service}: {log_level} - {message}"
            )

        logging.info(f"Log received from {service}: {log_level}")

        return jsonify(
            {
                "status": "success",
                "message": "Log metrics received and processed",
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        logging.error(f"Error processing logs: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/batch", methods=["POST"])
def receive_batch_metrics():
    """
    Receive multiple metrics in a single request for efficiency

    Example payload:
    {
        "metrics": [
            {
                "type": "application",
                "service": "user-service",
                "endpoint": "GET:/api/users",
                "metrics": {"response_time": 150, "status_code": 200}
            },
            {
                "type": "business",
                "metric_name": "login_count",
                "value": 1500
            }
        ]
    }
    """
    if not validate_api_key(request):
        return jsonify({"error": "Invalid API key"}), 401

    try:
        data = request.get_json()
        if not data or "metrics" not in data:
            return jsonify({"error": "JSON payload with 'metrics' array required"}), 400

        processed = 0
        errors = []

        for i, metric in enumerate(data["metrics"]):
            try:
                metric_type = metric.get("type", "application")

                if metric_type == "application":
                    # Process as application metric
                    service = metric.get("service", "unknown")
                    endpoint = metric.get("endpoint", "unknown")
                    metrics = metric.get("metrics", {})

                    status_code = str(metrics.get("status_code", 200))
                    redis_client.execute_command(
                        "CMS.INCRBY", "endpoint-frequency", endpoint, 1
                    )
                    redis_client.execute_command(
                        "CMS.INCRBY", "status-codes", status_code, 1
                    )

                elif metric_type == "business":
                    # Process as business metric
                    metric_name = metric.get("metric_name")
                    value = metric.get("value")

                    if metric_name and value is not None:
                        redis_client.execute_command(
                            "CMS.INCRBY", "business-metrics", metric_name, 1
                        )

                processed += 1

            except Exception as e:
                errors.append(f"Metric {i}: {str(e)}")

        logging.info(f"Batch processed: {processed} metrics, {len(errors)} errors")

        return jsonify(
            {
                "status": "success",
                "processed": processed,
                "errors": errors,
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        logging.error(f"Error processing batch metrics: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/metrics")
def prometheus_metrics():
    """Prometheus-compatible metrics endpoint"""
    try:
        # Get metrics from Redis
        endpoint_info = redis_client.execute_command("CMS.INFO", "endpoint-frequency")
        status_info = redis_client.execute_command("CMS.INFO", "status-codes")

        endpoint_count = endpoint_info[5] if len(endpoint_info) > 5 else 0
        status_count = status_info[5] if len(status_info) > 5 else 0

        # Get stream lengths
        fingerprints_count = redis_client.xlen("system-fingerprints")
        detailed_metrics_count = redis_client.xlen("detailed-metrics")

        metrics_text = f"""# HELP anomaly_detector_endpoint_requests_total Total endpoint requests processed
# TYPE anomaly_detector_endpoint_requests_total counter
anomaly_detector_endpoint_requests_total {endpoint_count}

# HELP anomaly_detector_status_events_total Total status code events processed  
# TYPE anomaly_detector_status_events_total counter
anomaly_detector_status_events_total {status_count}

# HELP anomaly_detector_fingerprints_total Total system fingerprints generated
# TYPE anomaly_detector_fingerprints_total counter
anomaly_detector_fingerprints_total {fingerprints_count}

# HELP anomaly_detector_detailed_metrics_total Total detailed metrics stored
# TYPE anomaly_detector_detailed_metrics_total counter
anomaly_detector_detailed_metrics_total {detailed_metrics_count}

# HELP anomaly_detector_uptime_seconds Uptime in seconds
# TYPE anomaly_detector_uptime_seconds gauge
anomaly_detector_uptime_seconds {time.time()}
"""

        return Response(metrics_text, mimetype="text/plain")

    except Exception as e:
        return Response(f"# Error generating metrics: {e}", mimetype="text/plain"), 500


# Legacy endpoint for backward compatibility
@app.route("/forward/<target_service>/<path:target_path>", methods=["GET"])
def forward(target_service: str, target_path: str):
    """Legacy forwarding endpoint for backward compatibility"""
    # Validate that template placeholders weren't used literally
    if (
        target_service.startswith("<")
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
        upstream = requests.request(method, target_url, timeout=5)
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000)
