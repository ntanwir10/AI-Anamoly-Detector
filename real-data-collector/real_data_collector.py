#!/usr/bin/env python3
"""
Real Data Collector Service
Replaces mock data with real production data sources
"""

import os
import yaml
import asyncio
import aiohttp
import redis
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import time
from dataclasses import dataclass
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUESTS_TOTAL = Counter(
    "real_data_collector_requests_total", "Total requests processed"
)
COLLECTION_DURATION = Histogram(
    "real_data_collection_duration_seconds", "Time spent collecting data"
)
DATA_SOURCE_ERRORS = Counter(
    "real_data_source_errors_total", "Total errors from data sources"
)
REDIS_OPERATIONS = Counter("redis_operations_total", "Total Redis operations")


@dataclass
class DataSource:
    name: str
    type: str
    config: Dict[str, Any]
    enabled: bool = True


class RealDataCollector:
    def __init__(self, config_path: str = "config/real_data_sources.yml"):
        self.config = self.load_config(config_path)
        self.redis_client = self.init_redis()
        self.data_sources = self.init_data_sources()
        self.session = None

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self.get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self.get_default_config()

    def get_default_config(self) -> Dict[str, Any]:
        """Default configuration if no file is found"""
        return {
            "data_sources": {
                "apm": {"enabled": False},
                "infrastructure": {"enabled": False},
                "logs": {"enabled": False},
                "business_intelligence": {"enabled": False},
                "custom_apis": {"enabled": False},
            },
            "collection": {
                "mode": "real_time",
                "intervals": {
                    "apm": "30s",
                    "infrastructure": "1m",
                    "logs": "10s",
                    "business": "5m",
                },
            },
        }

    def init_redis(self) -> redis.Redis:
        """Initialize Redis connection"""
        try:
            client = redis.Redis(
                host=os.getenv("REDIS_HOST", "redis-stack"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                decode_responses=True,
            )
            client.ping()
            logger.info("Redis connection established")
            return client
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    def init_data_sources(self) -> List[DataSource]:
        """Initialize data sources from configuration"""
        sources = []

        # APM Sources
        if self.config.get("data_sources", {}).get("apm", {}).get("enabled"):
            for provider in self.config["data_sources"]["apm"].get("providers", []):
                sources.append(
                    DataSource(name=provider["name"], type="apm", config=provider)
                )

        # Infrastructure Sources
        if self.config.get("data_sources", {}).get("infrastructure", {}).get("enabled"):
            for provider in self.config["data_sources"]["infrastructure"].get(
                "providers", []
            ):
                sources.append(
                    DataSource(
                        name=provider["name"], type="infrastructure", config=provider
                    )
                )

        # Custom API Sources
        if self.config.get("data_sources", {}).get("custom_apis", {}).get("enabled"):
            for endpoint in self.config["data_sources"]["custom_apis"].get(
                "endpoints", []
            ):
                sources.append(
                    DataSource(
                        name=endpoint["name"], type="custom_api", config=endpoint
                    )
                )

        logger.info(f"Initialized {len(sources)} data sources")
        return sources

    async def start_session(self):
        """Start aiohttp session for HTTP requests"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def stop_session(self):
        """Stop aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def collect_datadog_metrics(self, source: DataSource) -> Dict[str, Any]:
        """Collect metrics from Datadog"""
        try:
            api_key = os.getenv("DATADOG_API_KEY")
            app_key = os.getenv("DATADOG_APP_KEY")

            if not api_key or not app_key:
                logger.warning("Datadog API credentials not configured")
                return {}

            headers = {
                "Content-Type": "application/json",
                "DD-API-KEY": api_key,
                "DD-APPLICATION-KEY": app_key,
            }

            # Get metrics from last hour
            end_time = int(time.time())
            start_time = end_time - 3600

            # Example queries for common metrics
            queries = [
                "avg:http.response_time{*}",
                "sum:http.requests{status_code:5xx}",
                "sum:http.requests{status_code:2xx}",
                "avg:system.cpu.user{*}",
                "avg:system.mem.used{*}",
            ]

            metrics = {}
            for query in queries:
                params = {"query": query, "from": start_time, "to": end_time}

                async with self.session.get(
                    "https://api.datadoghq.com/api/v1/query",
                    headers=headers,
                    params=params,
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("series"):
                            # Extract the metric value
                            metric_name = query.split(":")[1].split("{")[0]
                            metrics[metric_name] = data["series"][0]["pointlist"][-1][1]

            return metrics

        except Exception as e:
            logger.error(f"Error collecting Datadog metrics: {e}")
            DATA_SOURCE_ERRORS.inc()
            return {}

    async def collect_prometheus_metrics(self, source: DataSource) -> Dict[str, Any]:
        """Collect metrics from Prometheus"""
        try:
            endpoint = source.config.get("endpoint")
            if not endpoint:
                logger.warning(f"No endpoint configured for {source.name}")
                return {}

            # Common Prometheus queries
            queries = {
                "request_rate": "rate(http_requests_total[5m])",
                "response_time_p95": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
                "error_rate": 'rate(http_requests_total{status=~"5.."}[5m])',
                "cpu_usage": '100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
                "memory_usage": "100 - ((node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100)",
            }

            metrics = {}
            for metric_name, query in queries.items():
                params = {"query": query}

                async with self.session.get(
                    f"{endpoint}/api/v1/query", params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("data", {}).get("result"):
                            # Extract the metric value
                            result = data["data"]["result"][0]
                            if "value" in result:
                                metrics[metric_name] = float(result["value"][1])

            return metrics

        except Exception as e:
            logger.error(f"Error collecting Prometheus metrics: {e}")
            DATA_SOURCE_ERRORS.inc()
            return {}

    async def collect_custom_api_metrics(self, source: DataSource) -> Dict[str, Any]:
        """Collect metrics from custom API endpoints"""
        try:
            url = source.config.get("url")
            auth_type = source.config.get("auth_type")
            auth_value = source.config.get("auth_token") or source.config.get(
                "auth_value"
            )

            headers = {"Content-Type": "application/json"}
            if auth_type == "bearer" and auth_value:
                headers["Authorization"] = f"Bearer {auth_value}"
            elif auth_type == "api_key" and auth_value:
                header_name = source.config.get("auth_header", "X-API-Key")
                headers[header_name] = auth_value

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    # Extract metrics based on configuration
                    metric_name = source.config.get("metric_name", "custom_metric")
                    transform = source.config.get("transform")

                    if transform and transform.startswith("jsonpath:"):
                        # Simple JSON path extraction (you might want to use jsonpath-ng for complex paths)
                        path = transform.split(":", 1)[1]
                        if path == "$.count":
                            return {metric_name: data.get("count", 0)}
                        elif path == "$.success_rate":
                            return {metric_name: data.get("success_rate", 0)}
                        else:
                            return {metric_name: data.get(path.split(".")[-1], 0)}
                    else:
                        return {metric_name: data}
                else:
                    logger.warning(
                        f"Custom API {source.name} returned status {response.status}"
                    )
                    return {}

        except Exception as e:
            logger.error(f"Error collecting custom API metrics from {source.name}: {e}")
            DATA_SOURCE_ERRORS.inc()
            return {}

    async def collect_from_source(self, source: DataSource) -> Dict[str, Any]:
        """Collect data from a specific source"""
        start_time = time.time()

        try:
            if source.type == "apm" and source.name == "datadog":
                metrics = await self.collect_datadog_metrics(source)
            elif source.type == "infrastructure" and source.name == "prometheus":
                metrics = await self.collect_prometheus_metrics(source)
            elif source.type == "custom_api":
                metrics = await self.collect_custom_api_metrics(source)
            else:
                logger.warning(
                    f"Unsupported data source type: {source.type} for {source.name}"
                )
                return {}

            # Add metadata
            metrics["_source"] = source.name
            metrics["_type"] = source.type
            metrics["_timestamp"] = datetime.utcnow().isoformat()

            duration = time.time() - start_time
            COLLECTION_DURATION.observe(duration)
            REQUESTS_TOTAL.inc()

            return metrics

        except Exception as e:
            logger.error(f"Error collecting from {source.name}: {e}")
            DATA_SOURCE_ERRORS.inc()
            return {}

    def store_metrics_in_redis(self, metrics: Dict[str, Any]):
        """Store collected metrics in Redis data structures"""
        try:
            timestamp = datetime.utcnow()

            # Store in Redis Stream for time-series analysis
            stream_data = {
                "data": json.dumps(metrics),
                "timestamp": timestamp.isoformat(),
                "source": metrics.get("_source", "unknown"),
            }

            self.redis_client.xadd("real-system-fingerprints", stream_data)
            REDIS_OPERATIONS.inc()

            # Update Count-Min Sketch for endpoint frequency (if applicable)
            if "endpoint" in metrics:
                self.redis_client.execute_command(
                    "CMS.INCRBY", "endpoint-frequency", metrics["endpoint"], 1
                )
                REDIS_OPERATIONS.inc()

            # Update status codes (if applicable)
            if "status_code" in metrics:
                self.redis_client.execute_command(
                    "CMS.INCRBY", "status-codes", str(metrics["status_code"]), 1
                )
                REDIS_OPERATIONS.inc()

            # Store raw metrics for dashboard
            metric_key = f"metrics:{metrics.get('_source', 'unknown')}:{timestamp.strftime('%Y%m%d%H%M')}"
            self.redis_client.setex(metric_key, 3600, json.dumps(metrics))  # 1 hour TTL
            REDIS_OPERATIONS.inc()

            logger.debug(f"Stored metrics from {metrics.get('_source', 'unknown')}")

        except Exception as e:
            logger.error(f"Error storing metrics in Redis: {e}")

    async def collect_all_sources(self):
        """Collect data from all enabled sources"""
        await self.start_session()

        try:
            for source in self.data_sources:
                if source.enabled:
                    logger.info(f"Collecting from {source.name} ({source.type})")
                    metrics = await self.collect_from_source(source)

                    if metrics:
                        self.store_metrics_in_redis(metrics)
                        logger.info(
                            f"Collected {len(metrics)} metrics from {source.name}"
                        )
                    else:
                        logger.warning(f"No metrics collected from {source.name}")

        finally:
            await self.stop_session()

    async def run_collection_loop(self):
        """Main collection loop"""
        logger.info("Starting real data collection loop")

        while True:
            try:
                await self.collect_all_sources()

                # Wait for next collection cycle
                await asyncio.sleep(60)  # Collect every minute

            except KeyboardInterrupt:
                logger.info("Collection loop interrupted")
                break
            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying


async def main():
    """Main entry point"""
    # Start Prometheus metrics server
    start_http_server(8000)

    collector = RealDataCollector()

    try:
        await collector.run_collection_loop()
    finally:
        await collector.stop_session()


if __name__ == "__main__":
    asyncio.run(main())
