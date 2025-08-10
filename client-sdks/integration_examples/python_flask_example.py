#!/usr/bin/env python3
"""
Example: Integrating AI Anomaly Detector with Flask application
"""

from flask import Flask, jsonify, request
import time
import random
import sys
import os

# Add the parent directory to the path so we can import the SDK
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from anomaly_client import AnomalyClient, AnomalyMiddleware, RequestTimer

# Initialize Flask app
app = Flask(__name__)

# Initialize Anomaly Detector client
# In production, use environment variables for these values
ANOMALY_DETECTOR_URL = os.getenv('ANOMALY_DETECTOR_URL', 'http://localhost:4000')
API_KEY = os.getenv('ANOMALY_API_KEY', 'demo-api-key')

try:
    anomaly_client = AnomalyClient(ANOMALY_DETECTOR_URL, api_key=API_KEY)
    anomaly_middleware = AnomalyMiddleware(anomaly_client, 'flask-demo-app')
    print(f"✅ Connected to Anomaly Detector at {ANOMALY_DETECTOR_URL}")
except Exception as e:
    print(f"❌ Failed to initialize Anomaly Detector: {e}")
    anomaly_client = None
    anomaly_middleware = None

# Flask request middleware for automatic tracking
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    if anomaly_middleware:
        try:
            duration = (time.time() - request.start_time) * 1000  # Convert to milliseconds
            anomaly_middleware.track_request(
                request.method,
                request.endpoint or request.path,
                response.status_code,
                duration,
                extra_metrics={
                    'content_length': response.content_length or 0,
                    'user_agent': request.headers.get('User-Agent', 'unknown')[:50]
                }
            )
        except Exception as e:
            print(f"Warning: Failed to track request: {e}")
    
    return response

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint"""
    health_data = {
        'status': 'healthy',
        'service': 'flask-demo-app',
        'timestamp': time.time()
    }
    
    # Check anomaly detector connectivity
    if anomaly_client:
        try:
            detector_health = anomaly_client.health_check()
            health_data['anomaly_detector'] = 'connected'
            health_data['detector_status'] = detector_health.get('status', 'unknown')
        except Exception as e:
            health_data['anomaly_detector'] = 'disconnected'
            health_data['detector_error'] = str(e)
    else:
        health_data['anomaly_detector'] = 'not_configured'
    
    return jsonify(health_data)

# API endpoints with different response patterns
@app.route('/api/users')
def get_users():
    """Simulate user listing with variable response times"""
    # Simulate variable response time
    delay = random.uniform(0.1, 0.5)
    time.sleep(delay)
    
    users = [
        {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
        {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},
        {'id': 3, 'name': 'Charlie', 'email': 'charlie@example.com'}
    ]
    
    return jsonify({
        'users': users,
        'count': len(users),
        'response_time': delay
    })

@app.route('/api/orders')
def get_orders():
    """Simulate order listing with occasional errors"""
    # 5% chance of error to test anomaly detection
    if random.random() < 0.05:
        return jsonify({'error': 'Database connection timeout'}), 500
    
    # Simulate slower query
    time.sleep(random.uniform(0.2, 0.8))
    
    orders = [
        {'id': 101, 'user_id': 1, 'amount': 25.99, 'status': 'completed'},
        {'id': 102, 'user_id': 2, 'amount': 15.50, 'status': 'pending'},
        {'id': 103, 'user_id': 1, 'amount': 99.99, 'status': 'completed'}
    ]
    
    return jsonify({
        'orders': orders,
        'total_amount': sum(order['amount'] for order in orders)
    })

@app.route('/api/business-metrics')
def business_metrics():
    """Send business metrics to anomaly detector"""
    if not anomaly_client:
        return jsonify({'error': 'Anomaly detector not configured'}), 503
    
    try:
        # Simulate daily revenue calculation
        daily_revenue = random.uniform(45000, 55000)
        
        # Send business metric
        result = anomaly_client.send_business_metric(
            'daily_revenue',
            daily_revenue,
            expected_range=[40000, 60000],
            metadata={'currency': 'USD', 'region': 'US-EAST'}
        )
        
        # Send user registration count
        user_registrations = random.randint(50, 150)
        registration_result = anomaly_client.send_business_metric(
            'user_registrations',
            user_registrations,
            expected_range=[75, 125],
            metadata={'period': 'daily'}
        )
        
        return jsonify({
            'daily_revenue': {
                'value': daily_revenue,
                'anomaly_response': result
            },
            'user_registrations': {
                'value': user_registrations,
                'anomaly_response': registration_result
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to send business metrics: {e}'}), 500

@app.route('/api/logs-demo')
def logs_demo():
    """Demonstrate log-based anomaly detection"""
    if not anomaly_client:
        return jsonify({'error': 'Anomaly detector not configured'}), 503
    
    try:
        # Send various log levels
        log_entries = [
            ('INFO', 'User login successful', {'user_id': '12345'}),
            ('WARN', 'Rate limit approached', {'endpoint': '/api/users', 'count': 95}),
            ('ERROR', 'Payment processing failed', {'transaction_id': 'tx_789', 'amount': 99.99})
        ]
        
        results = []
        for level, message, context in log_entries:
            result = anomaly_client.send_log(level, message, 'flask-demo-app', context)
            results.append({
                'level': level,
                'message': message,
                'response': result
            })
        
        return jsonify({
            'message': 'Log entries sent to anomaly detector',
            'entries': results
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to send logs: {e}'}), 500

@app.route('/api/batch-demo')
def batch_demo():
    """Demonstrate batch metric sending"""
    if not anomaly_client:
        return jsonify({'error': 'Anomaly detector not configured'}), 503
    
    try:
        # Create batch of mixed metrics
        batch_metrics = [
            {
                'type': 'application',
                'service': 'flask-demo-app',
                'endpoint': 'GET:/api/users',
                'metrics': {
                    'response_time': random.uniform(100, 300),
                    'status_code': 200,
                    'payload_size': random.randint(1000, 5000)
                }
            },
            {
                'type': 'application',
                'service': 'flask-demo-app',
                'endpoint': 'GET:/api/orders',
                'metrics': {
                    'response_time': random.uniform(200, 800),
                    'status_code': random.choice([200, 200, 200, 500]),  # Occasional error
                    'payload_size': random.randint(2000, 8000)
                }
            },
            {
                'type': 'business',
                'metric_name': 'api_calls_per_minute',
                'value': random.randint(50, 200)
            },
            {
                'type': 'business',
                'metric_name': 'active_users',
                'value': random.randint(100, 500)
            }
        ]
        
        result = anomaly_client.send_batch(batch_metrics)
        
        return jsonify({
            'message': 'Batch metrics sent successfully',
            'batch_size': len(batch_metrics),
            'response': result
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to send batch metrics: {e}'}), 500

# Context manager example
@app.route('/api/timed-operation')
def timed_operation():
    """Demonstrate using RequestTimer context manager"""
    if not anomaly_client:
        return jsonify({'error': 'Anomaly detector not configured'}), 503
    
    try:
        with RequestTimer(anomaly_client, 'flask-demo-app', 'GET:/api/timed-operation'):
            # Simulate some work
            time.sleep(random.uniform(0.1, 0.5))
            
            # Simulate occasional failure
            if random.random() < 0.1:
                raise Exception("Simulated processing error")
            
            return jsonify({
                'message': 'Timed operation completed',
                'data': 'Some processed data'
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n🚀 Starting Flask Demo Application")
    print(f"   - Anomaly Detector: {ANOMALY_DETECTOR_URL}")
    print(f"   - API Key configured: {bool(API_KEY)}")
    print("\nAvailable endpoints:")
    print("   - GET  /health                 - Health check")
    print("   - GET  /api/users              - List users (variable response time)")
    print("   - GET  /api/orders             - List orders (occasional errors)")
    print("   - GET  /api/business-metrics   - Send business metrics")
    print("   - GET  /api/logs-demo          - Send log entries")
    print("   - GET  /api/batch-demo         - Send batch metrics")
    print("   - GET  /api/timed-operation    - Timed operation with context manager")
    print("\nTest the integration:")
    print("   curl http://localhost:5000/health")
    print("   curl http://localhost:5000/api/users")
    print("   curl http://localhost:5000/api/business-metrics")
    print("\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
