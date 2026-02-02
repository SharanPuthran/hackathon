"""
WebSocket client for AgentCore Runtime invocation.

This module provides a client for invoking AgentCore Runtime agents
via WebSocket connections using the AWS SDK.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator, Dict, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, ConnectionError as BotoConnectionError

logger = logging.getLogger(__name__)


class AgentCoreWebSocketClient:
    """
    WebSocket client for AgentCore Runtime invocation.
    
    This client manages WebSocket connections to AgentCore Runtime and handles
    both streaming and buffered response modes.
    
    Attributes:
        runtime_arn: Full ARN of the AgentCore Runtime
        region: AWS region
        client: Boto3 bedrock-agentcore client
    """
    
    def __init__(self, runtime_arn: str, region: str):
        """
        Initialize WebSocket client.
        
        Args:
            runtime_arn: Full ARN of AgentCore Runtime
            region: AWS region
        """
        self.runtime_arn = runtime_arn
        self.region = region
        
        # Configure boto3 client with extended timeouts for AgentCore
        # AgentCore can take 2-5 minutes to process complex disruptions
        config = Config(
            read_timeout=600,  # 10 minutes read timeout
            connect_timeout=30,  # 30 seconds connect timeout
            retries={'max_attempts': 0}  # We handle retries ourselves
        )
        self.client = boto3.client('bedrock-agentcore', region_name=region, config=config)
        self._connection = None
    
    async def invoke(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        timeout: int = 300
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Invoke AgentCore Runtime and stream responses.
        
        This method establishes a WebSocket connection to AgentCore Runtime,
        sends the prompt, and yields response chunks as they arrive.
        
        Args:
            prompt: Disruption description
            session_id: Optional session ID for context
            timeout: Maximum execution time in seconds
            
        Yields:
            Response chunks as dictionaries
            
        Raises:
            TimeoutError: If invocation exceeds timeout
            ConnectionError: If WebSocket connection fails
            
        Examples:
            >>> client = AgentCoreWebSocketClient(runtime_arn, region)
            >>> async for chunk in client.invoke("Flight delayed"):
            ...     print(chunk)
        """
        start_time = time.time()
        
        try:
            # Prepare the payload
            payload = json.dumps({"prompt": prompt}).encode('utf-8')
            
            # Generate session ID if not provided (must be at least 33 characters)
            if not session_id:
                session_id = str(uuid.uuid4()) + "-" + str(uuid.uuid4())
            
            # Invoke the agent runtime
            response = self.client.invoke_agent_runtime(
                agentRuntimeArn=self.runtime_arn,
                runtimeSessionId=session_id,
                payload=payload
            )
            
            # Process streaming response
            if "text/event-stream" in response.get("contentType", ""):
                for line in response["response"].iter_lines(chunk_size=10):
                    # Check timeout
                    if time.time() - start_time > timeout:
                        raise TimeoutError(f"Agent execution exceeded {timeout} second timeout")
                    
                    if line:
                        line_str = line.decode("utf-8")
                        if line_str.startswith("data: "):
                            data = line_str[6:]
                            try:
                                chunk = json.loads(data)
                                yield chunk
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse chunk: {data}")
                                continue
            
            elif response.get("contentType") == "application/json":
                # Handle standard JSON response
                content = []
                for chunk in response.get("response", []):
                    content.append(chunk.decode('utf-8'))
                
                full_response = json.loads(''.join(content))
                yield full_response
            
            else:
                # Handle other content types
                logger.warning(f"Unexpected content type: {response.get('contentType')}")
                yield {"error": "Unexpected response format"}
        
        except BotoConnectionError as e:
            logger.error(f"Connection error: {str(e)}")
            raise ConnectionError(f"Failed to connect to AgentCore Runtime: {str(e)}")
        
        except ClientError as e:
            logger.error(f"AWS client error: {str(e)}")
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            raise ConnectionError(f"AgentCore Runtime error ({error_code}): {error_message}")
        
        except Exception as e:
            logger.error(f"Unexpected error during invocation: {str(e)}")
            raise
    
    async def invoke_buffered(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Invoke AgentCore Runtime and return complete response.
        
        This method collects all streaming chunks and returns the complete
        response as a single dictionary.
        
        Args:
            prompt: Disruption description
            session_id: Optional session ID for context
            timeout: Maximum execution time in seconds
            
        Returns:
            Complete response as dictionary
            
        Raises:
            TimeoutError: If invocation exceeds timeout
            ConnectionError: If WebSocket connection fails
            
        Examples:
            >>> client = AgentCoreWebSocketClient(runtime_arn, region)
            >>> response = await client.invoke_buffered("Flight delayed")
            >>> print(response['assessment'])
        """
        chunks = []
        final_response = {}
        
        async for chunk in self.invoke(prompt, session_id, timeout):
            chunks.append(chunk)
            
            # Check if this is the final response
            if chunk.get("type") == "complete":
                final_response = chunk.get("data", {})
                break
            
            # Check for errors
            if chunk.get("type") == "error":
                error_info = chunk.get("error", {})
                raise ConnectionError(
                    f"AgentCore Runtime error: {error_info.get('message', 'Unknown error')}"
                )
        
        # If no complete message was received, aggregate chunks
        if not final_response and chunks:
            final_response = {
                "status": "success",
                "chunks": chunks,
                "assessment": chunks[-1] if chunks else {}
            }
        
        return final_response
    
    async def invoke_with_retry(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        timeout: int = 300,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Invoke AgentCore Runtime with retry logic.
        
        Retries connection failures with exponential backoff.
        
        Args:
            prompt: Disruption description
            session_id: Optional session ID for context
            timeout: Maximum execution time in seconds
            max_retries: Maximum number of retry attempts
            
        Returns:
            Complete response as dictionary
            
        Raises:
            TimeoutError: If invocation exceeds timeout
            ConnectionError: If all retry attempts fail
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return await self.invoke_buffered(prompt, session_id, timeout)
            
            except ConnectionError as e:
                last_error = e
                if attempt < max_retries:
                    # Exponential backoff: 1s, 2s
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Connection failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {wait_time}s: {str(e)}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All retry attempts failed: {str(e)}")
            
            except TimeoutError:
                # Don't retry timeouts
                raise
        
        # If we get here, all retries failed
        raise ConnectionError(f"Failed after {max_retries + 1} attempts: {str(last_error)}")
    
    async def close(self):
        """
        Close the WebSocket connection.
        
        Ensures proper cleanup of resources.
        """
        # Boto3 client doesn't require explicit closing
        # but we keep this method for interface consistency
        self._connection = None
        logger.debug("WebSocket client closed")
