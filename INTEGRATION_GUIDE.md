# AI Anomaly Detector - Real-World Integration Guide

## 🌍 Real-World Usage Scenarios

This AI Anomaly Detection system can be integrated into existing infrastructures in multiple ways:

### 1. **API Gateway Integration**

Deploy as a sidecar service that monitors API traffic

### 2. **Microservices Monitoring**

Monitor service-to-service communication patterns

### 3. **Application Performance Monitoring (APM)**

Integrate with existing observability stacks

### 4. **Infrastructure Monitoring**

Monitor system metrics, resource usage, and performance

### 5. **Business Intelligence**

Detect anomalies in business metrics and KPIs

---

## 🔌 Integration Methods

### Method 1: Direct API Integration

**Best For**: Applications that can send metrics programmatically

```bash
# Send custom metrics to the anomaly detector
curl -X POST http://your-anomaly-detector:4000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "service": "user-auth-service",
    "endpoint": "POST:/api/login",
    "status_code": 200,
    "response_time": 150,
    "timestamp": "2024-01-20T10:30:00Z"
  }'
```

### Method 2: Agent-Based Collection

**Best For**: Legacy systems, third-party applications

Deploy lightweight agents on each server:

```yaml
# docker-compose.agent.yml
version: '3.8'
services:
  anomaly-agent:
    image: ai-anomaly-agent:latest
    volumes:
      - /var/log:/var/log:ro
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    environment:
      - COLLECTOR_URL=http://central-anomaly-detector:4000
      - LOG_PATHS=/var/log/nginx/*.log,/var/log/app/*.log
      - METRICS_INTERVAL=30s
```

### Method 3: Service Mesh Integration

**Best For**: Kubernetes environments with Istio/Linkerd

```yaml
# istio-anomaly-detector.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: anomaly-detector-config
data:
  anomaly_detector.lua: |
    function envoy_on_request(request_handle)
      -- Capture request metrics
      local headers = request_handle:headers()
      local method = headers:get(":method")
      local path = headers:get(":path")
      
      -- Send to anomaly detector
      local metric = {
        service = headers:get("x-service-name"),
        endpoint = method .. ":" .. path,
        timestamp = os.time()
      }
      -- HTTP call to anomaly detector...
    end
```

### Method 4: Log Streaming Integration

**Best For**: Systems with centralized logging

```yaml
# fluentd-anomaly.conf
<source>
  @type tail
  path /var/log/nginx/access.log
  pos_file /tmp/nginx.log.pos
  tag nginx.access
  format nginx
</source>

<match nginx.access>
  @type http
  endpoint http://anomaly-detector:4000/api/logs
  headers {"Content-Type":"application/json"}
  format json
</match>
```

### Method 5: Webhook Integration

**Best For**: Monitoring tools, alerting systems

```javascript
// Send alerts to existing systems
const webhookEndpoints = [
  'https://hooks.slack.com/services/...',
  'https://your-pagerduty-integration.com/webhook',
  'https://your-custom-alerting-system.com/api/alerts'
];

// In your anomaly detection handler
async function sendAnomalyAlert(anomaly) {
  const alertPayload = {
    severity: 'high',
    message: anomaly.message,
    timestamp: anomaly.timestamp,
    system: 'ai-anomaly-detector'
  };
  
  await Promise.all(
    webhookEndpoints.map(url => 
      fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(alertPayload)
      })
    )
  );
}
```

---

## 🏗️ Deployment Patterns

### Pattern 1: Centralized Deployment

```flow
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Service A │───▶│   Service B │───▶│   Service C │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────┐
│          Centralized Anomaly Detector              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │    Redis    │ │ AI Service  │ │  Dashboard  │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Pros**: Single point of management, resource efficiency
**Cons**: Single point of failure, potential bottleneck

### Pattern 2: Distributed Edge Deployment

```arch
┌─────────────────────────┐  ┌─────────────────────────┐
│      Data Center 1      │  │      Data Center 2      │
│  ┌─────────────────┐    │  │  ┌─────────────────┐    │
│  │ Local Anomaly   │    │  │  │ Local Anomaly   │    │
│  │ Detector        │    │  │  │ Detector        │    │
│  └─────────────────┘    │  │  └─────────────────┘    │
└─────────────────────────┘  └─────────────────────────┘
            │                            │
            └──────────┬─────────────────┘
                       ▼
          ┌─────────────────────────┐
          │   Central Dashboard     │
          │   & Alert Manager       │
          └─────────────────────────┘
```

**Pros**: Low latency, fault tolerance, scalability
**Cons**: Complex management, data synchronization

### Pattern 3: Hybrid Cloud-Edge

```arch
┌─────────────────┐     ┌─────────────────┐
│  On-Premise     │     │    Cloud        │
│  Edge Detector  │────▶│  ML Training    │
│                 │     │  & Analytics    │
└─────────────────┘     └─────────────────┘
```

**Pros**: Data privacy, advanced analytics, scalability
**Cons**: Network dependency, complexity

---

## 🔧 Configuration Examples

### Environment-Specific Configurations

#### Production Environment

```yaml
# config/production.yml
redis:
  cluster_mode: true
  nodes:
    - redis-cluster-1:6379
    - redis-cluster-2:6379
    - redis-cluster-3:6379
  
ai_service:
  model_type: "isolation_forest"
  training_samples: 1000
  retrain_interval: "24h"
  contamination: 0.05
  
alerts:
  channels:
    - type: "webhook"
      url: "https://alerts.company.com/webhook"
    - type: "pagerduty"
      integration_key: "${PAGERDUTY_KEY}"
    - type: "slack"
      webhook_url: "${SLACK_WEBHOOK}"
      
data_collection:
  batch_size: 100
  flush_interval: "30s"
  max_memory: "512MB"
```

#### Development Environment

```yaml
# config/development.yml
redis:
  single_node: true
  host: "localhost"
  port: 6379
  
ai_service:
  model_type: "isolation_forest"
  training_samples: 50
  retrain_interval: "5m"
  contamination: 0.1
  
alerts:
  channels:
    - type: "console"
    - type: "webhook"
      url: "https://webhook.site/your-test-url"
```

---

## 📊 Integration APIs

### Enhanced Data Collector API

```javascript
// POST /api/metrics - Send custom metrics
{
  "service": "user-service",
  "endpoint": "GET:/api/users",
  "metrics": {
    "response_time": 150,
    "status_code": 200,
    "payload_size": 1024,
    "cpu_usage": 45.2,
    "memory_usage": 67.8
  },
  "timestamp": "2024-01-20T10:30:00Z",
  "tags": ["production", "critical"]
}

// POST /api/business-metrics - Business-level anomaly detection
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

// POST /api/logs - Log-based anomaly detection
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
```

### Alert Configuration API

```javascript
// POST /api/alert-rules
{
  "name": "High Error Rate",
  "condition": {
    "metric": "status_codes.5xx",
    "threshold": 10,
    "window": "5m",
    "aggregation": "count"
  },
  "actions": [
    {
      "type": "webhook",
      "url": "https://your-system.com/alerts",
      "headers": {
        "Authorization": "Bearer ${API_TOKEN}"
      }
    },
    {
      "type": "email",
      "recipients": ["ops@company.com"]
    }
  ]
}
```

---

## 🚀 Quick Integration Examples

### Express.js Application

```javascript
const express = require('express');
const AnomalyClient = require('./anomaly-client');

const app = express();
const anomalyClient = new AnomalyClient('http://anomaly-detector:4000');

// Middleware to track all requests
app.use((req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    
    anomalyClient.sendMetric({
      service: 'web-app',
      endpoint: `${req.method}:${req.path}`,
      status_code: res.statusCode,
      response_time: duration,
      timestamp: new Date().toISOString()
    });
  });
  
  next();
});
```

### Spring Boot Application

```java
@Component
public class AnomalyDetectorIntegration {
    
    @Autowired
    private RestTemplate restTemplate;
    
    @Value("${anomaly.detector.url}")
    private String anomalyDetectorUrl;
    
    @EventListener
    public void handleRequest(RequestEvent event) {
        MetricPayload payload = MetricPayload.builder()
            .service("spring-app")
            .endpoint(event.getMethod() + ":" + event.getPath())
            .statusCode(event.getStatusCode())
            .responseTime(event.getDuration())
            .timestamp(Instant.now())
            .build();
            
        restTemplate.postForEntity(
            anomalyDetectorUrl + "/api/metrics", 
            payload, 
            Void.class
        );
    }
}
```

### Python Django Application

```python
import requests
from django.utils.deprecation import MiddlewareMixin
import time

class AnomalyDetectorMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response
        self.anomaly_detector_url = settings.ANOMALY_DETECTOR_URL
        
    def process_request(self, request):
        request._start_time = time.time()
        
    def process_response(self, request, response):
        if hasattr(request, '_start_time'):
            duration = (time.time() - request._start_time) * 1000
            
            try:
                requests.post(f"{self.anomaly_detector_url}/api/metrics", json={
                    'service': 'django-app',
                    'endpoint': f"{request.method}:{request.path}",
                    'status_code': response.status_code,
                    'response_time': duration,
                    'timestamp': timezone.now().isoformat()
                }, timeout=1)
            except:
                pass  # Don't let anomaly detection break the app
                
        return response
```

---

## 🛡️ Security Considerations

### API Authentication

```yaml
# Enhanced security configuration
security:
  api_key_required: true
  rate_limiting:
    requests_per_minute: 1000
    burst_limit: 100
  
  allowed_origins:
    - "https://your-app.com"
    - "https://monitoring.company.com"
    
  encryption:
    data_at_rest: true
    data_in_transit: true
    
audit:
  log_all_requests: true
  retention_days: 90
```

### Network Security

```bash
# Firewall rules for anomaly detector
# Allow only necessary ports
iptables -A INPUT -p tcp --dport 4000 -s 10.0.0.0/8 -j ACCEPT  # Data collector
iptables -A INPUT -p tcp --dport 8080 -s 10.0.0.0/8 -j ACCEPT  # Dashboard
iptables -A INPUT -p tcp --dport 6379 -s 127.0.0.1 -j ACCEPT   # Redis (local only)
```

---

## 📈 Monitoring & Observability

### Health Checks

```bash
# System health verification script
#!/bin/bash
echo "=== ANOMALY DETECTOR HEALTH CHECK ==="

# Check services
curl -f http://localhost:8080/health || echo "❌ Dashboard BFF unhealthy"
curl -f http://localhost:4000/health || echo "❌ Data Collector unhealthy"

# Check Redis
redis-cli ping || echo "❌ Redis unavailable"

# Check AI service logs
docker logs ai-service --tail 5 | grep -q "Model training complete" || echo "❌ AI service not ready"

# Check data flow
FINGERPRINTS=$(curl -s http://localhost:8080/api/fingerprints | jq 'length')
echo "📊 Fingerprints collected: $FINGERPRINTS"

ANOMALIES=$(curl -s http://localhost:8080/api/anomalies | jq 'length')
echo "🚨 Anomalies detected: $ANOMALIES"
```

### Prometheus Metrics Integration

```javascript
// Enhanced metrics endpoint
app.get('/metrics', async (req, res) => {
  const metrics = await collectMetrics();
  res.set('Content-Type', 'text/plain');
  res.send(`
# HELP anomaly_detector_fingerprints_total Total fingerprints processed
# TYPE anomaly_detector_fingerprints_total counter
anomaly_detector_fingerprints_total ${metrics.fingerprints}

# HELP anomaly_detector_anomalies_total Total anomalies detected
# TYPE anomaly_detector_anomalies_total counter
anomaly_detector_anomalies_total ${metrics.anomalies}

# HELP anomaly_detector_response_time Response time for anomaly detection
# TYPE anomaly_detector_response_time histogram
anomaly_detector_response_time_bucket{le="0.1"} ${metrics.response_times.bucket_100ms}
anomaly_detector_response_time_bucket{le="0.5"} ${metrics.response_times.bucket_500ms}
anomaly_detector_response_time_bucket{le="1.0"} ${metrics.response_times.bucket_1s}
  `);
});
```

---

## 🎯 Next Steps for Implementation

1. **Choose Integration Method**: Select the approach that best fits your infrastructure
2. **Deploy in Staging**: Test with a subset of your traffic
3. **Configure Alerts**: Set up appropriate alert channels
4. **Monitor Performance**: Track system impact and adjust thresholds
5. **Scale Gradually**: Increase monitoring coverage over time

This integration guide provides multiple pathways for real-world deployment, from simple API integration to complex distributed architectures.
