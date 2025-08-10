"""
Comprehensive test suite for AI Anomaly Detector Python Client SDK
"""

import pytest
import json
import requests_mock
from datetime import datetime
from unittest.mock import Mock, patch
import logging

from anomaly_client import (
    AnomalyClient,
    AnomalyClientError,
    AnomalyMiddleware,
    RequestTimer,
    track_function
)


class TestAnomalyClient:
    """Test cases for AnomalyClient class"""

    def setup_method(self):
        """Setup test client"""
        self.base_url = "http://test-anomaly-detector:4000"
        self.api_key = "test-api-key"
        self.client = AnomalyClient(self.base_url, self.api_key)

    def test_client_initialization(self):
        """Test client initialization"""
        # Test with API key
        assert self.client.base_url == self.base_url
        assert self.client.api_key == self.api_key
        assert self.client.session.headers["Authorization"] == f"Bearer {self.api_key}"
        assert self.client.session.headers["Content-Type"] == "application/json"
        assert self.client.session.headers["User-Agent"] == "AnomalyClient-Python/1.0"

        # Test without API key
        client_no_key = AnomalyClient(self.base_url)
        assert "Authorization" not in client_no_key.session.headers

    def test_base_url_normalization(self):
        """Test base URL normalization (removes trailing slash)"""
        client = AnomalyClient("http://test.com/")
        assert client.base_url == "http://test.com"

    @requests_mock.Mocker()
    def test_health_check_success(self, m):
        """Test successful health check"""
        expected_response = {"status": "healthy", "redis_connected": True}
        m.get(f"{self.base_url}/health", json=expected_response)

        result = self.client.health_check()
        assert result == expected_response

    @requests_mock.Mocker()
    def test_health_check_failure(self, m):
        """Test failed health check"""
        m.get(f"{self.base_url}/health", status_code=500, json={"error": "Redis connection failed"})

        with pytest.raises(AnomalyClientError) as exc_info:
            self.client.health_check()
        
        assert "Redis connection failed" in str(exc_info.value)

    @requests_mock.Mocker()
    def test_send_metric_success(self, m):
        """Test successful metric sending"""
        metric_data = {
            "service": "test-service",
            "endpoint": "GET:/api/users",
            "metrics": {
                "response_time": 150,
                "status_code": 200
            }
        }
        expected_response = {"status": "success", "metric_id": "12345"}
        m.post(f"{self.base_url}/api/metrics", json=expected_response)

        result = self.client.send_metric(metric_data)
        assert result == expected_response
        
        # Verify request was made correctly
        request = m.last_request
        request_data = json.loads(request.text)
        assert request_data["service"] == "test-service"
        assert request_data["endpoint"] == "GET:/api/users"
        assert "timestamp" in request_data  # Should auto-add timestamp

    @requests_mock.Mocker()
    def test_send_business_metric_success(self, m):
        """Test successful business metric sending"""
        expected_response = {"status": "success", "metric_id": "67890"}
        m.post(f"{self.base_url}/api/business-metrics", json=expected_response)

        result = self.client.send_business_metric(
            "daily_revenue", 
            45000, 
            expected_range=[40000, 60000],
            metadata={"currency": "USD"}
        )
        assert result == expected_response

        # Verify request data
        request = m.last_request
        request_data = json.loads(request.text)
        assert request_data["metric_name"] == "daily_revenue"
        assert request_data["value"] == 45000
        assert request_data["expected_range"] == [40000, 60000]
        assert request_data["metadata"]["currency"] == "USD"
        assert "timestamp" in request_data

    @requests_mock.Mocker()
    def test_send_log_success(self, m):
        """Test successful log sending"""
        expected_response = {"status": "success", "log_id": "log123"}
        m.post(f"{self.base_url}/api/logs", json=expected_response)

        result = self.client.send_log(
            "ERROR", 
            "Database timeout", 
            "payment-service",
            context={"user_id": "12345"}
        )
        assert result == expected_response

        # Verify request data
        request = m.last_request
        request_data = json.loads(request.text)
        assert request_data["log_level"] == "ERROR"
        assert request_data["message"] == "Database timeout"
        assert request_data["service"] == "payment-service"
        assert request_data["context"]["user_id"] == "12345"
        assert "timestamp" in request_data

    @requests_mock.Mocker()
    def test_send_batch_success(self, m):
        """Test successful batch sending"""
        batch_data = [
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
        expected_response = {"status": "success", "processed": 2}
        m.post(f"{self.base_url}/api/batch", json=expected_response)

        result = self.client.send_batch(batch_data)
        assert result == expected_response

        # Verify request data
        request = m.last_request
        request_data = json.loads(request.text)
        assert len(request_data["metrics"]) == 2

    @requests_mock.Mocker()
    def test_get_config_success(self, m):
        """Test successful config retrieval"""
        expected_config = {
            "redis_structures": {"service-calls": "cuckoo_filter"},
            "version": "1.0.0"
        }
        m.get(f"{self.base_url}/config", json=expected_config)

        result = self.client.get_config()
        assert result == expected_config

    @requests_mock.Mocker()
    def test_network_error_handling(self, m):
        """Test network error handling"""
        m.get(f"{self.base_url}/health", exc=requests.exceptions.ConnectionError)

        with pytest.raises(AnomalyClientError) as exc_info:
            self.client.health_check()
        
        assert "Network error" in str(exc_info.value)

    @requests_mock.Mocker()
    def test_http_error_handling(self, m):
        """Test HTTP error handling"""
        m.get(f"{self.base_url}/health", status_code=404, text="Not found")

        with pytest.raises(AnomalyClientError) as exc_info:
            self.client.health_check()
        
        assert "404" in str(exc_info.value)


class TestAnomalyMiddleware:
    """Test cases for AnomalyMiddleware class"""

    def setup_method(self):
        """Setup test middleware"""
        self.client = Mock(spec=AnomalyClient)
        self.middleware = AnomalyMiddleware(self.client, "test-service")

    def test_middleware_initialization(self):
        """Test middleware initialization"""
        assert self.middleware.client == self.client
        assert self.middleware.service_name == "test-service"

    def test_track_request_success(self):
        """Test successful request tracking"""
        self.client.send_metric.return_value = {"status": "success"}

        self.middleware.track_request("GET", "/api/users", 200, 150.5)

        self.client.send_metric.assert_called_once()
        call_args = self.client.send_metric.call_args[0][0]
        assert call_args["service"] == "test-service"
        assert call_args["endpoint"] == "GET:/api/users"
        assert call_args["metrics"]["response_time"] == 150.5
        assert call_args["metrics"]["status_code"] == 200

    def test_track_request_with_extra_metrics(self):
        """Test request tracking with extra metrics"""
        self.client.send_metric.return_value = {"status": "success"}
        extra_metrics = {"payload_size": 1024, "user_id": "12345"}

        self.middleware.track_request("POST", "/api/orders", 201, 200.0, extra_metrics)

        call_args = self.client.send_metric.call_args[0][0]
        assert call_args["metrics"]["payload_size"] == 1024
        assert call_args["metrics"]["user_id"] == "12345"

    def test_track_request_error_handling(self):
        """Test middleware error handling doesn't break application"""
        self.client.send_metric.side_effect = AnomalyClientError("Network error")

        # Should not raise exception
        with patch('logging.warning') as mock_warning:
            self.middleware.track_request("GET", "/api/users", 500, 1000)
            mock_warning.assert_called_once()


class TestRequestTimer:
    """Test cases for RequestTimer context manager"""

    def setup_method(self):
        """Setup test timer"""
        self.client = Mock(spec=AnomalyClient)
        self.timer = RequestTimer(self.client, "test-service", "GET:/api/test")

    def test_timer_success(self):
        """Test timer with successful execution"""
        self.client.send_metric.return_value = {"status": "success"}

        with self.timer:
            # Simulate some work
            pass

        self.client.send_metric.assert_called_once()
        call_args = self.client.send_metric.call_args[0][0]
        assert call_args["service"] == "test-service"
        assert call_args["endpoint"] == "GET:/api/test"
        assert call_args["metrics"]["status_code"] == 200
        assert call_args["metrics"]["response_time"] > 0

    def test_timer_with_exception(self):
        """Test timer when exception occurs"""
        self.client.send_metric.return_value = {"status": "success"}

        try:
            with self.timer:
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected

        call_args = self.client.send_metric.call_args[0][0]
        assert call_args["metrics"]["status_code"] == 500

    def test_timer_error_handling(self):
        """Test timer when sending metrics fails"""
        self.client.send_metric.side_effect = AnomalyClientError("Network error")

        # Should not raise exception
        with self.timer:
            pass


class TestTrackFunctionDecorator:
    """Test cases for track_function decorator"""

    def setup_method(self):
        """Setup test decorator"""
        self.client = Mock(spec=AnomalyClient)
        self.client.send_metric.return_value = {"status": "success"}

    def test_decorator_success(self):
        """Test decorator with successful function"""
        @track_function(self.client, "test-service")
        def test_function(x, y):
            return x + y

        result = test_function(2, 3)
        assert result == 5

        self.client.send_metric.assert_called_once()
        call_args = self.client.send_metric.call_args[0][0]
        assert call_args["service"] == "test-service"
        assert call_args["endpoint"] == "function:test_function"
        assert call_args["metrics"]["status_code"] == 200

    def test_decorator_with_exception(self):
        """Test decorator when function raises exception"""
        @track_function(self.client, "test-service")
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        call_args = self.client.send_metric.call_args[0][0]
        assert call_args["metrics"]["status_code"] == 500


@pytest.mark.integration
class TestIntegration:
    """Integration tests with actual HTTP server"""

    def setup_method(self):
        """Setup integration test"""
        self.client = AnomalyClient("http://localhost:4000", timeout=5)

    def test_integration_health_check(self):
        """Test health check against running service"""
        # This test requires the data collector to be running
        try:
            result = self.client.health_check()
            assert "status" in result
        except AnomalyClientError:
            pytest.skip("Data collector not running")

    def test_integration_send_metric(self):
        """Test sending metric to running service"""
        try:
            result = self.client.send_metric({
                "service": "test-integration",
                "endpoint": "GET:/api/test",
                "metrics": {"response_time": 100, "status_code": 200}
            })
            assert "status" in result or "success" in str(result).lower()
        except AnomalyClientError:
            pytest.skip("Data collector not running")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
