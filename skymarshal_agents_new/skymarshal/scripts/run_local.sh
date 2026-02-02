#!/bin/bash
# Local development script for AgentCore REST API

set -e

echo "🚀 Starting local API development environment..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set local development mode
export LOCAL_MODE=true
export MOCK_AGENTCORE=${MOCK_AGENTCORE:-true}

echo "Local Mode: $LOCAL_MODE"
echo "Mock AgentCore: $MOCK_AGENTCORE"
echo ""

# Start local API server using Python
echo "Starting local API server on http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

python3 -c "
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from api.lambda_handler import lambda_handler
from api.health import health_check_handler

class LocalAPIHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/v1/invoke':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length).decode('utf-8')
            
            event = {
                'body': body,
                'headers': dict(self.headers),
                'requestContext': {'requestId': 'local-test'}
            }
            
            response = lambda_handler(event, None)
            
            self.send_response(response['statusCode'])
            for key, value in response['headers'].items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response['body'].encode('utf-8'))
        else:
            self.send_error(404)
    
    def do_GET(self):
        if self.path == '/api/v1/health':
            event = {}
            response = health_check_handler(event, None)
            
            self.send_response(response['statusCode'])
            for key, value in response['headers'].items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response['body'].encode('utf-8'))
        else:
            self.send_error(404)

server = HTTPServer(('localhost', 8000), LocalAPIHandler)
print('Server running on http://localhost:8000')
server.serve_forever()
"
