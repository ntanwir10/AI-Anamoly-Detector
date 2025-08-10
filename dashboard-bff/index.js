import express from "express";
import { WebSocketServer } from "ws";
import { createClient } from "redis";

const app = express();

// CORS middleware
app.use((req, res, next) => {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
  res.header(
    "Access-Control-Allow-Headers",
    "Origin, X-Requested-With, Content-Type, Accept, Authorization"
  );

  if (req.method === "OPTIONS") {
    res.sendStatus(200);
  } else {
    next();
  }
});
const wsPort = parseInt(process.env.WS_PORT || "8080", 10);

const server = app.listen(wsPort, () => {
  console.log(`dashboard-bff listening on ${wsPort}`);
});

// WebSocket server
const wss = new WebSocketServer({ server });

// Redis subscriber
const redisHost = process.env.REDIS_HOST || "redis-stack";
const redisPort = parseInt(process.env.REDIS_PORT || "6379", 10);
const sub = createClient({ url: `redis://${redisHost}:${redisPort}` });
await sub.connect();
await sub.subscribe("alerts", (message) => {
  const payload = JSON.stringify({ message, ts: Date.now() });
  wss.clients.forEach((client) => {
    try {
      client.send(payload);
    } catch (_) {}
  });
});

// Redis client for reading data
const redisClient = createClient({ url: `redis://${redisHost}:${redisPort}` });
await redisClient.connect();

app.get("/health", async (_req, res) => {
  try {
    await redisClient.ping();
    res.json({
      status: "healthy",
      redis: "connected",
      uptime: process.uptime(),
      timestamp: Date.now(),
      anomalies_count: recentAnomalies.length,
    });
  } catch (error) {
    res.status(503).json({
      status: "unhealthy",
      redis: "disconnected",
      error: error.message,
      timestamp: Date.now(),
    });
  }
});

// Root route for better user experience
app.get("/", (_req, res) => {
  res.json({
    service: "Dashboard BFF",
    status: "running",
    endpoints: {
      health: "/health",
      redisData: "/redis-data",
      fingerprints: "/api/fingerprints",
      anomalies: "/api/anomalies",
      websocket: "ws://localhost:8080",
    },
    description: "Backend service for AI Anomaly Detector Dashboard",
  });
});

// Endpoint to fetch RedisBloom data structures
app.get("/redis-data", async (req, res) => {
  try {
    // Get endpoint frequency data from Count-Min Sketch
    const endpointFrequency = {};
    try {
      // Query for the actual endpoints being tracked
      const endpoints = [
        "GET:/api/data",
        "GET:/api/error",
        "GET:/api/users",
        "POST:/api/users",
        "GET:/api/orders",
        "GET:/api/admin",
        "GET:/api/gateway",
      ];
      for (const endpoint of endpoints) {
        try {
          const count = await redisClient.sendCommand([
            "CMS.QUERY",
            "endpoint-frequency",
            endpoint,
          ]);
          if (count > 0) {
            endpointFrequency[endpoint] = count;
          }
        } catch (e) {
          // Endpoint might not exist yet
        }
      }
    } catch (e) {
      console.log("CMS endpoint-frequency not available yet");
    }

    // Get status codes data from Count-Min Sketch
    const statusCodes = {};
    try {
      const codes = [
        "200",
        "201",
        "400",
        "401",
        "403",
        "404",
        "409",
        "429",
        "500",
        "502",
        "503",
      ];
      for (const code of codes) {
        try {
          const count = await redisClient.sendCommand([
            "CMS.QUERY",
            "status-codes",
            code,
          ]);
          if (count > 0) {
            statusCodes[code] = count;
          }
        } catch (e) {
          // Status code might not exist yet
        }
      }
    } catch (e) {
      console.log("CMS status-codes not available yet");
    }

    // Get service calls from Cuckoo Filter (simplified - Cuckoo Filter doesn't support listing all items)
    const serviceCalls = [];
    try {
      // We can only check if specific items exist, not list all
      const testCalls = ["service-a:service-b", "service-b:service-c"];
      for (const call of testCalls) {
        try {
          const exists = await redisClient.sendCommand([
            "CF.EXISTS",
            "service-calls",
            call,
          ]);
          if (exists) {
            serviceCalls.push(call);
          }
        } catch (e) {
          // Service call might not exist yet
        }
      }
    } catch (e) {
      console.log("CF service-calls not available yet");
    }

    // Get system fingerprints from Redis Stream
    const systemFingerprints = [];
    try {
      const streamData = await redisClient.xRange(
        "system-fingerprints",
        "-",
        "+",
        { COUNT: 10 }
      );
      systemFingerprints.push(
        ...streamData.map((item) => {
          // Extract timestamp from Redis stream ID (format: timestamp-sequence)
          const rawTimestamp = parseInt(item.id.split("-")[0]);
          const readableTimestamp = new Date(rawTimestamp).toISOString();

          return {
            timestamp: readableTimestamp,
            timestampRaw: rawTimestamp,
            streamId: item.id,
            data: item.message.data,
          };
        })
      );
    } catch (e) {
      console.log("Stream system-fingerprints not available yet");
    }

    res.json({
      endpointFrequency,
      statusCodes,
      serviceCalls,
      systemFingerprints,
    });
  } catch (error) {
    console.error("Error fetching Redis data:", error);
    res.status(500).json({ error: "Failed to fetch Redis data" });
  }
});

// API endpoint for fingerprints (expected by frontend)
app.get("/api/fingerprints", async (req, res) => {
  try {
    const systemFingerprints = [];
    const streamData = await redisClient.xRange(
      "system-fingerprints",
      "-",
      "+",
      { COUNT: 100 }
    );
    systemFingerprints.push(
      ...streamData.map((item) => {
        // Extract timestamp from Redis stream ID (format: timestamp-sequence)
        const rawTimestamp = parseInt(item.id.split("-")[0]);
        const readableTimestamp = new Date(rawTimestamp).toISOString();

        return {
          timestamp: readableTimestamp,
          timestampRaw: rawTimestamp,
          streamId: item.id,
          fingerprint: JSON.parse(item.message.data),
        };
      })
    );
    res.json(systemFingerprints);
  } catch (error) {
    console.error("Error fetching fingerprints:", error);
    res.status(500).json({ error: "Failed to fetch fingerprints" });
  }
});

// Store recent anomalies in memory
const recentAnomalies = [];

// Subscribe to anomaly alerts
await sub.subscribe("alerts", (message) => {
  const anomaly = {
    id: Date.now(),
    message: message,
    timestamp: new Date().toISOString(),
    severity: "high",
  };
  recentAnomalies.push(anomaly);
  // Keep only last 100 anomalies
  if (recentAnomalies.length > 100) {
    recentAnomalies.shift();
  }
  const payload = JSON.stringify({ message, ts: Date.now() });
  wss.clients.forEach((client) => {
    try {
      client.send(payload);
    } catch (_) {}
  });
});

// API endpoint for anomalies (expected by frontend)
app.get("/api/anomalies", async (req, res) => {
  try {
    res.json(recentAnomalies);
  } catch (error) {
    console.error("Error fetching anomalies:", error);
    res.status(500).json({ error: "Failed to fetch anomalies" });
  }
});
