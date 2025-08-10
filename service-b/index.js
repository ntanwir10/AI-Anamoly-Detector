import express from "express";

const app = express();
const port = 3000;

// Root route for better user experience
app.get("/", (req, res) => {
  res.json({
    service: "Service B",
    status: "running",
    endpoints: {
      data: "/api/data",
      error: "/api/error",
      health: "/health",
    },
    description:
      "Service B for AI Anomaly Detector - generates simulated data and errors",
  });
});

app.get("/health", (req, res) => {
  res.status(200).json({
    status: "healthy",
    service: "service-b",
    uptime: process.uptime(),
    timestamp: Date.now(),
  });
});

app.get("/api/data", (req, res) => {
  res.status(200).json({ status: "ok", ts: Date.now() });
});

app.get("/api/error", (req, res) => {
  res
    .status(500)
    .json({ status: "error", message: "Simulated failure", ts: Date.now() });
});

// Additional endpoints with various HTTP status codes
app.get("/api/users", (req, res) => {
  const rand = Math.random();
  if (rand < 0.7) {
    res
      .status(200)
      .json({ users: ["alice", "bob", "charlie"], ts: Date.now() });
  } else if (rand < 0.85) {
    res.status(404).json({ error: "Users not found", ts: Date.now() });
  } else {
    res.status(401).json({ error: "Unauthorized access", ts: Date.now() });
  }
});

app.post("/api/users", (req, res) => {
  const rand = Math.random();
  if (rand < 0.6) {
    res
      .status(201)
      .json({
        message: "User created",
        id: Math.floor(Math.random() * 1000),
        ts: Date.now(),
      });
  } else if (rand < 0.8) {
    res
      .status(400)
      .json({ error: "Bad request - invalid user data", ts: Date.now() });
  } else {
    res.status(409).json({ error: "User already exists", ts: Date.now() });
  }
});

app.get("/api/orders", (req, res) => {
  const rand = Math.random();
  if (rand < 0.8) {
    res.status(200).json({ orders: [{ id: 1, total: 99.99 }], ts: Date.now() });
  } else if (rand < 0.9) {
    res.status(404).json({ error: "Orders not found", ts: Date.now() });
  } else {
    res.status(429).json({ error: "Rate limit exceeded", ts: Date.now() });
  }
});

app.get("/api/admin", (req, res) => {
  const rand = Math.random();
  if (rand < 0.3) {
    res.status(200).json({ admin: "panel", ts: Date.now() });
  } else if (rand < 0.7) {
    res
      .status(403)
      .json({ error: "Forbidden - admin access required", ts: Date.now() });
  } else {
    res.status(401).json({ error: "Unauthorized", ts: Date.now() });
  }
});

app.get("/api/gateway", (req, res) => {
  const rand = Math.random();
  if (rand < 0.4) {
    res.status(200).json({ gateway: "healthy", ts: Date.now() });
  } else if (rand < 0.7) {
    res.status(502).json({ error: "Bad Gateway", ts: Date.now() });
  } else {
    res.status(503).json({ error: "Service Unavailable", ts: Date.now() });
  }
});

// Catch-all for undefined routes
app.use("*", (req, res) => {
  res.status(404).json({
    error: "Not Found",
    path: req.originalUrl,
    method: req.method,
    ts: Date.now(),
  });
});

app.listen(port, () => {
  console.log(`service-b listening on port ${port}`);
});
