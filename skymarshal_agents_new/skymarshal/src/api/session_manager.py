"""
Session management module for API endpoints.
"""

import logging
import time
import uuid
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages agent invocation sessions and history."""
    
    def __init__(self, table_name: str, region: str):
        """Initialize session manager."""
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        
        try:
            self.table.load()
            logger.info(f"Connected to DynamoDB table: {table_name}")
        except ClientError as e:
            logger.error(f"Failed to connect to DynamoDB table {table_name}: {str(e)}")
            raise
    
    def create_session(self) -> str:
        """Create a new session and return UUID v4."""
        session_id = str(uuid.uuid4())
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def save_interaction(
        self,
        session_id: str,
        request_id: str,
        prompt: str,
        response: dict,
        execution_time_ms: int,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> None:
        """Save an interaction to session history."""
        timestamp = int(time.time() * 1000)
        ttl = int(time.time()) + (30 * 24 * 60 * 60)
        
        item = {
            'session_id': session_id,
            'timestamp': timestamp,
            'request_id': request_id,
            'prompt': prompt,
            'response': response,
            'status': status,
            'execution_time_ms': execution_time_ms,
            'ttl': ttl
        }
        
        if error_message:
            item['error_message'] = error_message
        
        try:
            self.table.put_item(Item=item)
            logger.info(f"Saved interaction for session {session_id}")
        except ClientError as e:
            logger.error(f"Failed to save interaction: {str(e)}")
            raise
    
    def get_session_history(self, session_id: str, limit: int = 50) -> List[dict]:
        """Retrieve session history."""
        try:
            response = self.table.query(
                KeyConditionExpression='session_id = :sid',
                ExpressionAttributeValues={':sid': session_id},
                ScanIndexForward=False,
                Limit=limit
            )
            
            interactions = response.get('Items', [])
            logger.info(f"Retrieved {len(interactions)} interactions")
            return interactions
        
        except ClientError as e:
            logger.error(f"Failed to retrieve session history: {str(e)}")
            raise
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions."""
        logger.info("DynamoDB TTL handles automatic session cleanup")
        return 0
