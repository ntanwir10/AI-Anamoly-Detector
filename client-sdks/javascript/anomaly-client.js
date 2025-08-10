/**
 * AI Anomaly Detector JavaScript/Node.js Client SDK
 *
 * Usage:
 *   const AnomalyClient = require('./anomaly-client');
 *
 *   const client = new AnomalyClient('http://anomaly-detector:4000', 'your-api-key');
 *
 *   // Send application metrics
 *   await client.sendMetric({
 *     service: 'user-service',
 *     endpoint: 'GET:/api/users',
 *     metrics: {
 *       response_time: 150,
 *       status_code: 200
 *     }
 *   });
 *
 *   // Express.js middleware
 *   app.use(client.expressMiddleware('my-express-app'));
 */

const fetch = require("node-fetch");

class AnomalyClientError extends Error {
  constructor(message, statusCode = null) {
    super(message);
    this.name = "AnomalyClientError";
    this.statusCode = statusCode;
  }
}

class AnomalyClient {
  /**
   * Initialize the anomaly client
   * @param {string} baseUrl - Base URL of the anomaly detector service
   * @param {string} apiKey - Optional API key for authentication
   * @param {object} options - Additional options
   */
  constructor(baseUrl, apiKey = null, options = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.apiKey = apiKey;
    this.timeout = options.timeout || 30000;
    this.retries = options.retries || 3;

    this.headers = {
      "Content-Type": "application/json",
      "User-Agent": "AnomalyClient-JavaScript/1.0",
    };

    if (apiKey) {
      this.headers["Authorization"] = `Bearer ${apiKey}`;
    }
  }

  /**
   * Make HTTP request to the anomaly detector service
   * @param {string} method - HTTP method
   * @param {string} endpoint - API endpoint
   * @param {object} data - Request payload
   */
  async _makeRequest(method, endpoint, data = null) {
    const url = `${this.baseUrl}/${endpoint.replace(/^\//, "")}`;

    const options = {
      method,
      headers: this.headers,
      timeout: this.timeout,
    };

    if (data) {
      options.body = JSON.stringify(data);
    }

    let lastError;

    for (let attempt = 0; attempt < this.retries; attempt++) {
      try {
        const response = await fetch(url, options);

        if (!response.ok) {
          let errorMessage;
          try {
            const errorData = await response.json();
            errorMessage = errorData.error || `HTTP ${response.status}`;
          } catch {
            errorMessage = `HTTP ${response.status}: ${response.statusText}`;
          }
          throw new AnomalyClientError(errorMessage, response.status);
        }

        return await response.json();
      } catch (error) {
        lastError = error;
        if (attempt < this.retries - 1) {
          await this._sleep(Math.pow(2, attempt) * 1000); // Exponential backoff
        }
      }
    }

    throw new AnomalyClientError(
      `Request failed after ${this.retries} attempts: ${lastError.message}`
    );
  }

  /**
   * Sleep for specified milliseconds
   * @param {number} ms - Milliseconds to sleep
   */
  _sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Check if the anomaly detector service is healthy
   */
  async healthCheck() {
    return this._makeRequest("GET", "/health");
  }

  /**
   * Send application metrics
   * @param {object} metricData - Metric data object
   * @param {string} metricData.service - Service name
   * @param {string} metricData.endpoint - Endpoint identifier
   * @param {object} metricData.metrics - Metrics object
   * @param {string} [metricData.source_service] - Source service name
   * @param {string} [metricData.timestamp] - ISO timestamp
   */
  async sendMetric(metricData) {
    if (!metricData.timestamp) {
      metricData.timestamp = new Date().toISOString();
    }

    return this._makeRequest("POST", "/api/metrics", metricData);
  }

  /**
   * Send business metrics
   * @param {string} metricName - Name of the business metric
   * @param {number} value - Metric value
   * @param {Array<number>} [expectedRange] - Expected range [min, max]
   * @param {object} [metadata] - Additional metadata
   */
  async sendBusinessMetric(
    metricName,
    value,
    expectedRange = null,
    metadata = null
  ) {
    const data = {
      metric_name: metricName,
      value: value,
      timestamp: new Date().toISOString(),
    };

    if (expectedRange) {
      data.expected_range = expectedRange;
    }

    if (metadata) {
      data.metadata = metadata;
    }

    return this._makeRequest("POST", "/api/business-metrics", data);
  }

  /**
   * Send log-based metrics
   * @param {string} logLevel - Log level (INFO, WARN, ERROR, etc.)
   * @param {string} message - Log message
   * @param {string} service - Service name
   * @param {object} [context] - Additional context
   */
  async sendLog(logLevel, message, service, context = null) {
    const data = {
      log_level: logLevel.toUpperCase(),
      message: message,
      service: service,
      timestamp: new Date().toISOString(),
    };

    if (context) {
      data.context = context;
    }

    return this._makeRequest("POST", "/api/logs", data);
  }

  /**
   * Send multiple metrics in a single request
   * @param {Array<object>} metrics - Array of metric objects
   */
  async sendBatch(metrics) {
    return this._makeRequest("POST", "/api/batch", { metrics });
  }

  /**
   * Get current anomaly detector configuration
   */
  async getConfig() {
    return this._makeRequest("GET", "/config");
  }

  /**
   * Express.js middleware for automatic request tracking
   * @param {string} serviceName - Name of the service
   * @param {object} [options] - Middleware options
   */
  expressMiddleware(serviceName, options = {}) {
    const {
      trackErrors = true,
      trackSuccesses = true,
      extractUserId = null,
      ignoreRoutes = [],
    } = options;

    return (req, res, next) => {
      const startTime = Date.now();

      // Skip ignored routes
      if (ignoreRoutes.some((route) => req.path.includes(route))) {
        return next();
      }

      const originalSend = res.send;
      const originalJson = res.json;

      const sendMetrics = async () => {
        const duration = Date.now() - startTime;
        const shouldTrack =
          (res.statusCode >= 400 && trackErrors) ||
          (res.statusCode < 400 && trackSuccesses);

        if (!shouldTrack) return;

        const metrics = {
          response_time: duration,
          status_code: res.statusCode,
          payload_size: res.get("content-length") || 0,
        };

        // Extract user ID if function provided
        if (extractUserId && typeof extractUserId === "function") {
          try {
            const userId = extractUserId(req);
            if (userId) {
              metrics.user_id = userId;
            }
          } catch (error) {
            // Ignore extraction errors
          }
        }

        try {
          await this.sendMetric({
            service: serviceName,
            endpoint: `${req.method}:${req.route?.path || req.path}`,
            metrics: metrics,
            source_service: req.get("x-service-name") || "unknown",
          });
        } catch (error) {
          // Don't let anomaly detection break the application
          console.warn(
            "Failed to send metrics to anomaly detector:",
            error.message
          );
        }
      };

      // Override response methods to capture metrics
      res.send = function (body) {
        sendMetrics();
        return originalSend.call(this, body);
      };

      res.json = function (obj) {
        sendMetrics();
        return originalJson.call(this, obj);
      };

      next();
    };
  }

  /**
   * Koa.js middleware for automatic request tracking
   * @param {string} serviceName - Name of the service
   * @param {object} [options] - Middleware options
   */
  koaMiddleware(serviceName, options = {}) {
    const { trackErrors = true, trackSuccesses = true } = options;

    return async (ctx, next) => {
      const startTime = Date.now();

      try {
        await next();
      } finally {
        const duration = Date.now() - startTime;
        const shouldTrack =
          (ctx.status >= 400 && trackErrors) ||
          (ctx.status < 400 && trackSuccesses);

        if (shouldTrack) {
          try {
            await this.sendMetric({
              service: serviceName,
              endpoint: `${ctx.method}:${ctx.path}`,
              metrics: {
                response_time: duration,
                status_code: ctx.status,
                payload_size: ctx.length || 0,
              },
            });
          } catch (error) {
            console.warn(
              "Failed to send metrics to anomaly detector:",
              error.message
            );
          }
        }
      }
    };
  }
}

/**
 * Request timer helper class
 */
class RequestTimer {
  constructor(client, service, endpoint) {
    this.client = client;
    this.service = service;
    this.endpoint = endpoint;
    this.startTime = null;
  }

  start() {
    this.startTime = Date.now();
    return this;
  }

  async end(statusCode = 200, extraMetrics = {}) {
    if (!this.startTime) {
      throw new Error("Timer not started");
    }

    const duration = Date.now() - this.startTime;

    const metrics = {
      response_time: duration,
      status_code: statusCode,
      ...extraMetrics,
    };

    try {
      await this.client.sendMetric({
        service: this.service,
        endpoint: this.endpoint,
        metrics: metrics,
      });
    } catch (error) {
      console.warn("Failed to send metrics:", error.message);
    }
  }
}

/**
 * Function decorator for automatic timing
 * @param {AnomalyClient} client - Anomaly client instance
 * @param {string} service - Service name
 */
function trackFunction(client, service) {
  return function (target, propertyKey, descriptor) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args) {
      const timer = new RequestTimer(
        client,
        service,
        `function:${propertyKey}`
      );
      timer.start();

      try {
        const result = await originalMethod.apply(this, args);
        await timer.end(200);
        return result;
      } catch (error) {
        await timer.end(500);
        throw error;
      }
    };

    return descriptor;
  };
}

// Export classes and utilities
module.exports = {
  AnomalyClient,
  AnomalyClientError,
  RequestTimer,
  trackFunction,
};

// Example usage
if (require.main === module) {
  async function example() {
    // Initialize client
    const client = new AnomalyClient("http://localhost:4000", "your-api-key");

    try {
      // Check health
      const health = await client.healthCheck();
      console.log("Service health:", health);

      // Send application metric
      const response = await client.sendMetric({
        service: "example-service",
        endpoint: "GET:/api/test",
        metrics: {
          response_time: 150,
          status_code: 200,
          payload_size: 1024,
        },
      });
      console.log("Metric sent:", response);

      // Send business metric
      const businessResponse = await client.sendBusinessMetric(
        "test_metric",
        100,
        [80, 120],
        { currency: "USD" }
      );
      console.log("Business metric sent:", businessResponse);

      // Send log
      const logResponse = await client.sendLog(
        "INFO",
        "Test log message",
        "example-service",
        { user_id: "12345" }
      );
      console.log("Log sent:", logResponse);
    } catch (error) {
      console.error("Error:", error.message);
    }
  }

  example();
}
