"""
Simple Lambda handler for testing streaming Function URL
"""

import json


def lambda_handler(event, context):
    """
    Simple test handler
    """
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "message": "Hello from streaming Lambda!",
            "event": event
        })
    }
