"""
AI Anomaly Detector Python Client SDK

Usage:
    from anomaly_client import AnomalyClient

    client = AnomalyClient('http://anomaly-detector:4000', api_key='your-key')

    # Send application metrics
    client.send_metric({
        'service': 'user-service',
        'endpoint': 'GET:/api/users',
        'metrics': {
            'response_time': 150,
            'status_code': 200
        }
    })

    # Send business metrics
    client.send_business_metric('daily_revenue', 45000, expected_range=[40000, 60000])

    # Send logs
    client.send_log('ERROR', 'Database timeout', 'payment-service')
"""

import json
import time
import requests
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import logging


class AnomalyClientError(Exception):
    """Custom exception for anomaly client errors"""

    pass


class AnomalyClient:
    """Python client for AI Anomaly Detector"""

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 30):
        """
        Initialize the anomaly client

        Args:
            base_url: Base URL of the anomaly detector service
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "AnomalyClient-Python/1.0",
            }
        )

        # Setup logging
        self.logger = logging.getLogger("AnomalyClient")

    def _make_request(
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Dict:
        """Make HTTP request to the anomaly detector service"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(
                method=method, url=url, json=data, timeout=self.timeout
            )

            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", f"HTTP {response.status_code}")
                except:
                    error_msg = f"HTTP {response.status_code}: {response.text}"

                raise AnomalyClientError(f"Request failed: {error_msg}")

            return response.json()

        except requests.RequestException as e:
            raise AnomalyClientError(f"Network error: {str(e)}")

    def health_check(self) -> Dict:
        """Check if the anomaly detector service is healthy"""
        return self._make_request("GET", "/health")

    def send_metric(self, metric_data: Dict) -> Dict:
        """
        Send application metrics

        Args:
            metric_data: Dictionary containing metric information
                Required fields: service, endpoint, metrics
                Optional fields: source_service, timestamp

        Example:
            client.send_metric({
                'service': 'user-service',
                'endpoint': 'GET:/api/users',
                'metrics': {
                    'response_time': 150,
                    'status_code': 200,
                    'payload_size': 1024
                },
                'source_service': 'web-gateway'
            })
        """
        if "timestamp" not in metric_data:
            metric_data["timestamp"] = datetime.utcnow().isoformat() + "Z"

        return self._make_request("POST", "/api/metrics", metric_data)

    def send_business_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        expected_range: Optional[List[float]] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Send business metrics

        Args:
            metric_name: Name of the business metric
            value: Metric value
            expected_range: Optional expected range [min, max]
            metadata: Optional metadata dictionary

        Example:
            client.send_business_metric(
                'daily_revenue',
                45000,
                expected_range=[40000, 60000],
                metadata={'currency': 'USD', 'region': 'US-WEST'}
            )
        """
        data = {
            "metric_name": metric_name,
            "value": value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        if expected_range:
            data["expected_range"] = expected_range

        if metadata:
            data["metadata"] = metadata

        return self._make_request("POST", "/api/business-metrics", data)

    def send_log(
        self, log_level: str, message: str, service: str, context: Optional[Dict] = None
    ) -> Dict:
        """
        Send log-based metrics

        Args:
            log_level: Log level (INFO, WARN, ERROR, FATAL, etc.)
            message: Log message
            service: Service name that generated the log
            context: Optional context dictionary

        Example:
            client.send_log(
                'ERROR',
                'Database connection timeout',
                'payment-service',
                context={'user_id': '12345', 'transaction_id': 'tx_789'}
            )
        """
        data = {
            "log_level": log_level.upper(),
            "message": message,
            "service": service,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        if context:
            data["context"] = context

        return self._make_request("POST", "/api/logs", data)

    def send_batch(self, metrics: List[Dict]) -> Dict:
        """
        Send multiple metrics in a single request

        Args:
            metrics: List of metric dictionaries

        Example:
            client.send_batch([
                {
                    'type': 'application',
                    'service': 'user-service',
                    'endpoint': 'GET:/api/users',
                    'metrics': {'response_time': 150, 'status_code': 200}
                },
                {
                    'type': 'business',
                    'metric_name': 'login_count',
                    'value': 1500
                }
            ])
        """
        data = {"metrics": metrics}
        return self._make_request("POST", "/api/batch", data)

    def get_config(self) -> Dict:
        """Get current anomaly detector configuration"""
        return self._make_request("GET", "/config")


class AnomalyMiddleware:
    """Middleware helper for automatic metric collection"""

    def __init__(self, client: AnomalyClient, service_name: str):
        self.client = client
        self.service_name = service_name

    def track_request(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time: float,
        extra_metrics: Optional[Dict] = None,
    ):
        """Track a request automatically"""
        metrics = {"response_time": response_time, "status_code": status_code}

        if extra_metrics:
            metrics.update(extra_metrics)

        try:
            self.client.send_metric(
                {
                    "service": self.service_name,
                    "endpoint": f"{method}:{path}",
                    "metrics": metrics,
                }
            )
        except AnomalyClientError as e:
            # Don't let anomaly detection break the application
            logging.warning(f"Failed to send metrics: {e}")


# Context manager for automatic timing
class RequestTimer:
    """Context manager for timing requests"""

    def __init__(self, client: AnomalyClient, service: str, endpoint: str):
        self.client = client
        self.service = service
        self.endpoint = endpoint
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (time.time() - self.start_time) * 1000  # Convert to milliseconds
            status_code = 500 if exc_type else 200

            try:
                self.client.send_metric(
                    {
                        "service": self.service,
                        "endpoint": self.endpoint,
                        "metrics": {
                            "response_time": duration,
                            "status_code": status_code,
                        },
                    }
                )
            except AnomalyClientError:
                pass  # Silently fail to not break the application


# Decorator for automatic function timing
def track_function(client: AnomalyClient, service: str):
    """Decorator to automatically track function execution"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            with RequestTimer(client, service, f"function:{func.__name__}"):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# Example usage
if __name__ == "__main__":
    # Initialize client
    client = AnomalyClient("http://localhost:4000", api_key="your-api-key")

    # Check health
    try:
        health = client.health_check()
        print(f"Service health: {health}")
    except AnomalyClientError as e:
        print(f"Health check failed: {e}")

    # Send sample metrics
    try:
        # Application metric
        response = client.send_metric(
            {
                "service": "example-service",
                "endpoint": "GET:/api/test",
                "metrics": {
                    "response_time": 150,
                    "status_code": 200,
                    "payload_size": 1024,
                },
            }
        )
        print(f"Metric sent: {response}")

        # Business metric
        response = client.send_business_metric(
            "test_metric", 100, expected_range=[80, 120]
        )
        print(f"Business metric sent: {response}")

        # Log metric
        response = client.send_log("INFO", "Test log message", "example-service")
        print(f"Log sent: {response}")

    except AnomalyClientError as e:
        print(f"Error sending metrics: {e}")
