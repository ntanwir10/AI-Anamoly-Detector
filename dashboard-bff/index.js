import express from 'express';
import { WebSocketServer } from 'ws';
import { createClient } from 'redis';

const app = express();
const wsPort = parseInt(process.env.WS_PORT || '8080', 10);

const server = app.listen(wsPort, () => {
  console.log(`dashboard-bff listening on ${wsPort}`);
});

// WebSocket server
const wss = new WebSocketServer({ server });

// Redis subscriber
const redisHost = process.env.REDIS_HOST || 'redis-stack';
const redisPort = parseInt(process.env.REDIS_PORT || '6379', 10);
const sub = createClient({ url: `redis://${redisHost}:${redisPort}` });
await sub.connect();
await sub.subscribe('alerts', (message) => {
  const payload = JSON.stringify({ message, ts: Date.now() });
  wss.clients.forEach((client) => {
    try { client.send(payload); } catch (_) {}
  });
});

app.get('/health', (_req, res) => res.json({ status: 'ok' }));


