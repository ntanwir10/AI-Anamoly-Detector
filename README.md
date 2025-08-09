AI-Driven Distributed System Anomaly Detection

Run:

1. docker compose build
2. docker compose up -d
3. Open dashboard at http://localhost:3001. WebSocket proxy at ws://localhost:8080.

Services:
- redis-stack (6379, 8001)
- service-b (3000)
- data-collector (4000)
- service-a (traffic generator)
- redis-gears (registration one-off)
- ai-service (model training and detection)
- dashboard-bff (WebSocket → Redis Pub/Sub)
- dashboard-ui (React static)


