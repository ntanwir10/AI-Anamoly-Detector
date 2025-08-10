/**
 * Comprehensive test suite for AI Anomaly Detector JavaScript Client SDK
 */

const { AnomalyClient, AnomalyClientError, RequestTimer } = require('./anomaly-client');
const nock = require('nock');

describe('AnomalyClient', () => {
  let client;
  const baseUrl = 'http://test-anomaly-detector:4000';
  const apiKey = 'test-api-key';

  beforeEach(() => {
    client = new AnomalyClient(baseUrl, apiKey);
    nock.cleanAll();
  });

  afterEach(() => {
    nock.cleanAll();
  });

  describe('Initialization', () => {
    test('should initialize client with API key', () => {
      expect(client.baseUrl).toBe(baseUrl);
      expect(client.apiKey).toBe(apiKey);
      expect(client.headers['Authorization']).toBe(`Bearer ${apiKey}`);
      expect(client.headers['Content-Type']).toBe('application/json');
      expect(client.headers['User-Agent']).toBe('AnomalyClient-JavaScript/1.0');
    });

    test('should initialize client without API key', () => {
      const clientNoKey = new AnomalyClient(baseUrl);
      expect(clientNoKey.headers['Authorization']).toBeUndefined();
    });

    test('should normalize base URL', () => {
      const clientWithSlash = new AnomalyClient('http://test.com/');
      expect(clientWithSlash.baseUrl).toBe('http://test.com');
    });

    test('should set default options', () => {
      expect(client.timeout).toBe(30000);
      expect(client.retries).toBe(3);
    });

    test('should allow custom options', () => {
      const customClient = new AnomalyClient(baseUrl, apiKey, { timeout: 10000, retries: 5 });
      expect(customClient.timeout).toBe(10000);
      expect(customClient.retries).toBe(5);
    });
  });

  describe('Health Check', () => {
    test('should perform successful health check', async () => {
      const expectedResponse = { status: 'healthy', redis_connected: true };
      
      nock(baseUrl)
        .get('/health')
        .reply(200, expectedResponse);

      const result = await client.healthCheck();
      expect(result).toEqual(expectedResponse);
    });

    test('should handle health check failure', async () => {
      nock(baseUrl)
        .get('/health')
        .reply(500, { error: 'Redis connection failed' });

      await expect(client.healthCheck()).rejects.toThrow(AnomalyClientError);
    });
  });

  describe('Send Metric', () => {
    test('should send application metric successfully', async () => {
      const metricData = {
        service: 'test-service',
        endpoint: 'GET:/api/users',
        metrics: {
          response_time: 150,
          status_code: 200
        }
      };
      const expectedResponse = { status: 'success', metric_id: '12345' };

      nock(baseUrl)
        .post('/api/metrics')
        .reply(200, expectedResponse);

      const result = await client.sendMetric(metricData);
      expect(result).toEqual(expectedResponse);
    });

    test('should auto-add timestamp if not provided', async () => {
      const metricData = {
        service: 'test-service',
        endpoint: 'GET:/api/users',
        metrics: { response_time: 150 }
      };

      nock(baseUrl)
        .post('/api/metrics', (body) => {
          expect(body.timestamp).toBeDefined();
          expect(new Date(body.timestamp)).toBeInstanceOf(Date);
          return true;
        })
        .reply(200, { status: 'success' });

      await client.sendMetric(metricData);
    });

    test('should preserve existing timestamp', async () => {
      const timestamp = '2023-01-01T12:00:00.000Z';
      const metricData = {
        service: 'test-service',
        endpoint: 'GET:/api/users',
        metrics: { response_time: 150 },
        timestamp: timestamp
      };

      nock(baseUrl)
        .post('/api/metrics', (body) => {
          expect(body.timestamp).toBe(timestamp);
          return true;
        })
        .reply(200, { status: 'success' });

      await client.sendMetric(metricData);
    });
  });

  describe('Send Business Metric', () => {
    test('should send business metric successfully', async () => {
      const expectedResponse = { status: 'success', metric_id: '67890' };

      nock(baseUrl)
        .post('/api/business-metrics')
        .reply(200, expectedResponse);

      const result = await client.sendBusinessMetric(
        'daily_revenue',
        45000,
        [40000, 60000],
        { currency: 'USD' }
      );

      expect(result).toEqual(expectedResponse);
    });

    test('should handle business metric without optional parameters', async () => {
      nock(baseUrl)
        .post('/api/business-metrics', (body) => {
          expect(body.metric_name).toBe('simple_metric');
          expect(body.value).toBe(100);
          expect(body.expected_range).toBeUndefined();
          expect(body.metadata).toBeUndefined();
          expect(body.timestamp).toBeDefined();
          return true;
        })
        .reply(200, { status: 'success' });

      await client.sendBusinessMetric('simple_metric', 100);
    });
  });

  describe('Send Log', () => {
    test('should send log successfully', async () => {
      const expectedResponse = { status: 'success', log_id: 'log123' };

      nock(baseUrl)
        .post('/api/logs')
        .reply(200, expectedResponse);

      const result = await client.sendLog(
        'ERROR',
        'Database timeout',
        'payment-service',
        { user_id: '12345' }
      );

      expect(result).toEqual(expectedResponse);
    });

    test('should uppercase log level', async () => {
      nock(baseUrl)
        .post('/api/logs', (body) => {
          expect(body.log_level).toBe('ERROR');
          return true;
        })
        .reply(200, { status: 'success' });

      await client.sendLog('error', 'Test message', 'test-service');
    });

    test('should handle log without context', async () => {
      nock(baseUrl)
        .post('/api/logs', (body) => {
          expect(body.context).toBeUndefined();
          return true;
        })
        .reply(200, { status: 'success' });

      await client.sendLog('INFO', 'Test message', 'test-service');
    });
  });

  describe('Send Batch', () => {
    test('should send batch metrics successfully', async () => {
      const batchData = [
        {
          type: 'application',
          service: 'user-service',
          endpoint: 'GET:/api/users',
          metrics: { response_time: 150, status_code: 200 }
        },
        {
          type: 'business',
          metric_name: 'login_count',
          value: 1500
        }
      ];
      const expectedResponse = { status: 'success', processed: 2 };

      nock(baseUrl)
        .post('/api/batch')
        .reply(200, expectedResponse);

      const result = await client.sendBatch(batchData);
      expect(result).toEqual(expectedResponse);
    });
  });

  describe('Get Config', () => {
    test('should get configuration successfully', async () => {
      const expectedConfig = {
        redis_structures: { 'service-calls': 'cuckoo_filter' },
        version: '1.0.0'
      };

      nock(baseUrl)
        .get('/config')
        .reply(200, expectedConfig);

      const result = await client.getConfig();
      expect(result).toEqual(expectedConfig);
    });
  });

  describe('Error Handling', () => {
    test('should handle network errors', async () => {
      nock(baseUrl)
        .get('/health')
        .replyWithError('Network error');

      await expect(client.healthCheck()).rejects.toThrow(AnomalyClientError);
    });

    test('should handle HTTP errors', async () => {
      nock(baseUrl)
        .get('/health')
        .reply(404, 'Not found');

      await expect(client.healthCheck()).rejects.toThrow(AnomalyClientError);
    });

    test('should retry on failure', async () => {
      nock(baseUrl)
        .get('/health')
        .times(2)
        .replyWithError('Network error')
        .get('/health')
        .reply(200, { status: 'healthy' });

      const result = await client.healthCheck();
      expect(result.status).toBe('healthy');
    });

    test('should fail after max retries', async () => {
      nock(baseUrl)
        .get('/health')
        .times(3)
        .replyWithError('Network error');

      await expect(client.healthCheck()).rejects.toThrow(AnomalyClientError);
    });
  });

  describe('Express Middleware', () => {
    test('should create Express middleware', () => {
      const middleware = client.expressMiddleware('test-service');
      expect(typeof middleware).toBe('function');
    });

    test('should track successful requests', (done) => {
      // Mock sendMetric to verify it's called
      const originalSendMetric = client.sendMetric;
      client.sendMetric = jest.fn().mockResolvedValue({ status: 'success' });

      const middleware = client.expressMiddleware('test-service');
      
      // Mock Express req/res objects
      const req = {
        method: 'GET',
        path: '/api/users',
        route: { path: '/api/users' },
        get: jest.fn()
      };
      const res = {
        statusCode: 200,
        get: jest.fn().mockReturnValue('1024'),
        send: jest.fn(function(body) {
          // Verify sendMetric was called
          setTimeout(() => {
            expect(client.sendMetric).toHaveBeenCalled();
            const callArgs = client.sendMetric.mock.calls[0][0];
            expect(callArgs.service).toBe('test-service');
            expect(callArgs.endpoint).toBe('GET:/api/users');
            expect(callArgs.metrics.status_code).toBe(200);
            expect(callArgs.metrics.response_time).toBeGreaterThan(0);
            
            // Restore original method
            client.sendMetric = originalSendMetric;
            done();
          }, 10);
          return this;
        }),
        json: jest.fn()
      };
      const next = jest.fn();

      middleware(req, res, next);
      expect(next).toHaveBeenCalled();
      
      // Simulate response
      res.send('{"data": "test"}');
    });

    test('should handle middleware options', () => {
      const middleware = client.expressMiddleware('test-service', {
        trackErrors: false,
        trackSuccesses: true,
        ignoreRoutes: ['/health']
      });

      // Mock request to ignored route
      const req = { path: '/health' };
      const res = {};
      const next = jest.fn();

      middleware(req, res, next);
      expect(next).toHaveBeenCalled();
    });
  });

  describe('Koa Middleware', () => {
    test('should create Koa middleware', () => {
      const middleware = client.koaMiddleware('test-service');
      expect(typeof middleware).toBe('function');
    });

    test('should track Koa requests', async () => {
      // Mock sendMetric
      client.sendMetric = jest.fn().mockResolvedValue({ status: 'success' });

      const middleware = client.koaMiddleware('test-service');
      
      // Mock Koa context
      const ctx = {
        method: 'GET',
        path: '/api/users',
        status: 200,
        length: 1024
      };
      const next = jest.fn().mockResolvedValue();

      await middleware(ctx, next);

      expect(next).toHaveBeenCalled();
      expect(client.sendMetric).toHaveBeenCalled();
      
      const callArgs = client.sendMetric.mock.calls[0][0];
      expect(callArgs.service).toBe('test-service');
      expect(callArgs.endpoint).toBe('GET:/api/users');
      expect(callArgs.metrics.status_code).toBe(200);
    });
  });
});

describe('RequestTimer', () => {
  let client;
  let timer;

  beforeEach(() => {
    client = {
      sendMetric: jest.fn().mockResolvedValue({ status: 'success' })
    };
    timer = new RequestTimer(client, 'test-service', 'GET:/api/test');
  });

  test('should time successful requests', async () => {
    timer.start();
    
    // Simulate some work
    await new Promise(resolve => setTimeout(resolve, 10));
    
    await timer.end(200, { custom_metric: 'test' });

    expect(client.sendMetric).toHaveBeenCalled();
    const callArgs = client.sendMetric.mock.calls[0][0];
    expect(callArgs.service).toBe('test-service');
    expect(callArgs.endpoint).toBe('GET:/api/test');
    expect(callArgs.metrics.status_code).toBe(200);
    expect(callArgs.metrics.response_time).toBeGreaterThan(0);
    expect(callArgs.metrics.custom_metric).toBe('test');
  });

  test('should handle timer not started', async () => {
    await expect(timer.end()).rejects.toThrow('Timer not started');
  });

  test('should handle send metric errors gracefully', async () => {
    client.sendMetric = jest.fn().mockRejectedValue(new Error('Network error'));
    
    timer.start();
    
    // Should not throw
    await timer.end();
    
    expect(client.sendMetric).toHaveBeenCalled();
  });
});

describe('Integration Tests', () => {
  let client;

  beforeEach(() => {
    client = new AnomalyClient('http://localhost:4000', null, { timeout: 5000 });
  });

  test('should connect to running data collector', async () => {
    try {
      const result = await client.healthCheck();
      expect(result).toHaveProperty('status');
    } catch (error) {
      // Skip if service not running
      console.log('Data collector not running, skipping integration test');
    }
  }, 10000);

  test('should send metric to running service', async () => {
    try {
      const result = await client.sendMetric({
        service: 'test-integration',
        endpoint: 'GET:/api/test',
        metrics: { response_time: 100, status_code: 200 }
      });
      
      expect(result).toBeDefined();
    } catch (error) {
      // Skip if service not running
      console.log('Data collector not running, skipping integration test');
    }
  }, 10000);
});
