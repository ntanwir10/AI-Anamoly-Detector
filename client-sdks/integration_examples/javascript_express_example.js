#!/usr/bin/env node
/**
 * Example: Integrating AI Anomaly Detector with Express.js application
 */

const express = require("express");
const path = require("path");

// Import the Anomaly Client SDK
const { AnomalyClient, RequestTimer } = require("../javascript/anomaly-client");

// Initialize Express app
const app = express();
app.use(express.json());

// Initialize Anomaly Detector client
const ANOMALY_DETECTOR_URL =
  process.env.ANOMALY_DETECTOR_URL || "http://localhost:4000";
const API_KEY = process.env.ANOMALY_API_KEY || "demo-api-key";

let anomalyClient;
try {
  anomalyClient = new AnomalyClient(ANOMALY_DETECTOR_URL, API_KEY);
  console.log(`✅ Connected to Anomaly Detector at ${ANOMALY_DETECTOR_URL}`);
} catch (error) {
  console.error(`❌ Failed to initialize Anomaly Detector: ${error.message}`);
  anomalyClient = null;
}

// Apply anomaly detection middleware (automatic request tracking)
if (anomalyClient) {
  app.use(
    anomalyClient.expressMiddleware("express-demo-app", {
      trackErrors: true,
      trackSuccesses: true,
      ignoreRoutes: ["/favicon.ico"],
      extractUserId: (req) => req.headers["x-user-id"] || req.query.user_id,
    })
  );
}

// Health check endpoint
app.get("/health", async (req, res) => {
  const healthData = {
    status: "healthy",
    service: "express-demo-app",
    timestamp: new Date().toISOString(),
  };

  // Check anomaly detector connectivity
  if (anomalyClient) {
    try {
      const detectorHealth = await anomalyClient.healthCheck();
      healthData.anomaly_detector = "connected";
      healthData.detector_status = detectorHealth.status || "unknown";
    } catch (error) {
      healthData.anomaly_detector = "disconnected";
      healthData.detector_error = error.message;
    }
  } else {
    healthData.anomaly_detector = "not_configured";
  }

  res.json(healthData);
});

// API endpoints with different response patterns
app.get("/api/products", async (req, res) => {
  // Simulate variable response time
  const delay = Math.random() * 400 + 100; // 100-500ms
  await new Promise((resolve) => setTimeout(resolve, delay));

  const products = [
    { id: 1, name: "Laptop", price: 999.99, category: "Electronics" },
    { id: 2, name: "Book", price: 24.99, category: "Education" },
    { id: 3, name: "Coffee Mug", price: 12.99, category: "Kitchen" },
  ];

  res.json({
    products,
    count: products.length,
    response_time: delay,
  });
});

app.get("/api/orders/:userId", async (req, res) => {
  const { userId } = req.params;

  // 5% chance of error to test anomaly detection
  if (Math.random() < 0.05) {
    return res.status(500).json({ error: "Database connection timeout" });
  }

  // Simulate slower query for certain users
  const delay =
    userId === "999" ? Math.random() * 2000 + 1000 : Math.random() * 300 + 100;
  await new Promise((resolve) => setTimeout(resolve, delay));

  const orders = [
    { id: 201, user_id: parseInt(userId), amount: 45.99, status: "shipped" },
    {
      id: 202,
      user_id: parseInt(userId),
      amount: 129.99,
      status: "processing",
    },
  ];

  res.json({
    orders,
    user_id: parseInt(userId),
    total_amount: orders.reduce((sum, order) => sum + order.amount, 0),
  });
});

// Business metrics endpoint
app.get("/api/business-metrics", async (req, res) => {
  if (!anomalyClient) {
    return res.status(503).json({ error: "Anomaly detector not configured" });
  }

  try {
    // Simulate business metrics
    const dailyRevenue = Math.random() * 10000 + 45000; // 45k-55k
    const activeUsers = Math.floor(Math.random() * 500 + 1000); // 1000-1500

    // Send business metrics
    const revenueResult = await anomalyClient.sendBusinessMetric(
      "daily_revenue",
      dailyRevenue,
      [40000, 60000],
      { currency: "USD", region: "US-WEST" }
    );

    const usersResult = await anomalyClient.sendBusinessMetric(
      "active_users",
      activeUsers,
      [800, 1600],
      { platform: "web", measurement_period: "daily" }
    );

    res.json({
      daily_revenue: {
        value: dailyRevenue,
        anomaly_response: revenueResult,
      },
      active_users: {
        value: activeUsers,
        anomaly_response: usersResult,
      },
    });
  } catch (error) {
    res
      .status(500)
      .json({ error: `Failed to send business metrics: ${error.message}` });
  }
});

// Log-based anomaly detection demo
app.post("/api/logs-demo", async (req, res) => {
  if (!anomalyClient) {
    return res.status(503).json({ error: "Anomaly detector not configured" });
  }

  try {
    const {
      level = "INFO",
      message = "Test log message",
      context = {},
    } = req.body;

    // Send log to anomaly detector
    const result = await anomalyClient.sendLog(
      level,
      message,
      "express-demo-app",
      { ...context, endpoint: req.originalUrl, ip: req.ip }
    );

    // Also send some sample log entries
    const sampleLogs = [
      [
        "INFO",
        "User session started",
        { user_id: "12345", session_id: "sess_abc" },
      ],
      [
        "WARN",
        "High memory usage detected",
        { memory_usage: "85%", threshold: "80%" },
      ],
      [
        "ERROR",
        "External API timeout",
        { api: "payment-gateway", timeout: "30s" },
      ],
    ];

    const sampleResults = [];
    for (const [logLevel, logMessage, logContext] of sampleLogs) {
      try {
        const sampleResult = await anomalyClient.sendLog(
          logLevel,
          logMessage,
          "express-demo-app",
          logContext
        );
        sampleResults.push({
          level: logLevel,
          message: logMessage,
          response: sampleResult,
        });
      } catch (error) {
        sampleResults.push({
          level: logLevel,
          message: logMessage,
          error: error.message,
        });
      }
    }

    res.json({
      user_log: {
        level,
        message,
        response: result,
      },
      sample_logs: sampleResults,
    });
  } catch (error) {
    res.status(500).json({ error: `Failed to send logs: ${error.message}` });
  }
});

// Batch metrics demo
app.post("/api/batch-demo", async (req, res) => {
  if (!anomalyClient) {
    return res.status(503).json({ error: "Anomaly detector not configured" });
  }

  try {
    // Create batch of mixed metrics
    const batchMetrics = [
      {
        type: "application",
        service: "express-demo-app",
        endpoint: "GET:/api/products",
        metrics: {
          response_time: Math.random() * 200 + 100,
          status_code: 200,
          payload_size: Math.floor(Math.random() * 3000 + 1000),
        },
      },
      {
        type: "application",
        service: "express-demo-app",
        endpoint: "GET:/api/orders",
        metrics: {
          response_time: Math.random() * 500 + 200,
          status_code: Math.random() < 0.1 ? 500 : 200, // 10% error rate
          payload_size: Math.floor(Math.random() * 5000 + 2000),
        },
      },
      {
        type: "business",
        metric_name: "api_requests_per_minute",
        value: Math.floor(Math.random() * 100 + 50),
      },
      {
        type: "business",
        metric_name: "concurrent_users",
        value: Math.floor(Math.random() * 200 + 100),
      },
    ];

    const result = await anomalyClient.sendBatch(batchMetrics);

    res.json({
      message: "Batch metrics sent successfully",
      batch_size: batchMetrics.length,
      metrics_preview: batchMetrics.map((m) => ({
        type: m.type,
        service: m.service,
        endpoint: m.endpoint,
        metric_name: m.metric_name,
      })),
      response: result,
    });
  } catch (error) {
    res
      .status(500)
      .json({ error: `Failed to send batch metrics: ${error.message}` });
  }
});

// Request timer example
app.get("/api/timed-operation", async (req, res) => {
  if (!anomalyClient) {
    return res.status(503).json({ error: "Anomaly detector not configured" });
  }

  const timer = new RequestTimer(
    anomalyClient,
    "express-demo-app",
    "GET:/api/timed-operation"
  );
  timer.start();

  try {
    // Simulate some work
    const processingTime = Math.random() * 800 + 200; // 200-1000ms
    await new Promise((resolve) => setTimeout(resolve, processingTime));

    // Simulate occasional failure
    if (Math.random() < 0.1) {
      await timer.end(500, { error_type: "processing_error" });
      throw new Error("Simulated processing error");
    }

    await timer.end(200, {
      processing_time: processingTime,
      data_processed: Math.floor(Math.random() * 1000 + 100),
    });

    res.json({
      message: "Timed operation completed",
      processing_time: processingTime,
      data: "Some processed data",
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Configuration endpoint
app.get("/api/config", async (req, res) => {
  if (!anomalyClient) {
    return res.status(503).json({ error: "Anomaly detector not configured" });
  }

  try {
    const config = await anomalyClient.getConfig();
    res.json({
      anomaly_detector_config: config,
      app_config: {
        service_name: "express-demo-app",
        anomaly_detector_url: ANOMALY_DETECTOR_URL,
        api_key_configured: !!API_KEY,
      },
    });
  } catch (error) {
    res.status(500).json({ error: `Failed to get config: ${error.message}` });
  }
});

// Error handling middleware
app.use((error, req, res, next) => {
  console.error("Express error:", error);

  // Send error to anomaly detector if available
  if (anomalyClient) {
    anomalyClient
      .sendLog("ERROR", `Express error: ${error.message}`, "express-demo-app", {
        endpoint: req.originalUrl,
        method: req.method,
        stack: error.stack?.split("\n")[0], // First line only
      })
      .catch((logError) => {
        console.warn(
          "Failed to send error log to anomaly detector:",
          logError.message
        );
      });
  }

  res.status(500).json({ error: "Internal server error" });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: "Not found" });
});

// Start server
const PORT = process.env.PORT || 3500;

app.listen(PORT, () => {
  console.log("\n🚀 Express Demo Application Started");
  console.log(`   - Server: http://localhost:${PORT}`);
  console.log(`   - Anomaly Detector: ${ANOMALY_DETECTOR_URL}`);
  console.log(`   - API Key configured: ${!!API_KEY}`);
  console.log("\nAvailable endpoints:");
  console.log("   - GET  /health                    - Health check");
  console.log(
    "   - GET  /api/products              - List products (variable response time)"
  );
  console.log(
    "   - GET  /api/orders/:userId        - List user orders (occasional errors)"
  );
  console.log("   - GET  /api/business-metrics      - Send business metrics");
  console.log("   - POST /api/logs-demo             - Send log entries");
  console.log("   - POST /api/batch-demo            - Send batch metrics");
  console.log(
    "   - GET  /api/timed-operation       - Timed operation with manual tracking"
  );
  console.log(
    "   - GET  /api/config                - Get anomaly detector configuration"
  );
  console.log("\nTest the integration:");
  console.log(`   curl http://localhost:${PORT}/health`);
  console.log(`   curl http://localhost:${PORT}/api/products`);
  console.log(`   curl http://localhost:${PORT}/api/orders/123`);
  console.log(`   curl http://localhost:${PORT}/api/business-metrics`);
  console.log(
    `   curl -X POST http://localhost:${PORT}/api/logs-demo -H "Content-Type: application/json" -d '{"level":"ERROR","message":"Test error"}'`
  );
  console.log("\n");
});
