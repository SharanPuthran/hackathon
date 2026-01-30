"""Model provider abstraction for multi-provider support"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import json
import logging
import boto3
from botocore.config import Config
import os

logger = logging.getLogger(__name__)


class ModelProvider(ABC):
    """Abstract base class for model providers"""
    
    @abstractmethod
    async def invoke(self, messages: List[Dict], **kwargs) -> str:
        pass


class BedrockClaude(ModelProvider):
    """AWS Bedrock Claude model provider"""
    
    def __init__(self, model_id: str, client):
        self.model_id = model_id
        self.client = client
    
    async def invoke(self, messages: List[Dict], **kwargs) -> str:
        """Invoke Claude via Bedrock"""
        
        # Format messages for Claude
        system_prompt = ""
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.7),
            "system": system_prompt,
            "messages": user_messages
        }
        
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
        except Exception as e:
            logger.error(f"Bedrock Claude invocation failed: {e}")
            raise


class BedrockNova(ModelProvider):
    """AWS Bedrock Amazon Nova model provider"""

    def __init__(self, model_id: str, client):
        self.model_id = model_id
        self.client = client

    async def invoke(self, messages: List[Dict], **kwargs) -> str:
        """Invoke Nova via Bedrock"""

        # Format messages for Nova - content must be an array
        formatted_messages = []
        for msg in messages:
            if msg["role"] != "system":  # Nova doesn't use system messages separately
                content = msg["content"]
                # Ensure content is an array
                if isinstance(content, str):
                    content = [{"text": content}]
                formatted_messages.append({
                    "role": msg["role"],
                    "content": content
                })

        # Nova models have specific parameter requirements
        request_body = {
            "messages": formatted_messages,
            "inferenceConfig": {
                "maxTokens": kwargs.get("max_tokens", 4096),
                "temperature": kwargs.get("temperature", 0.7)
            }
        }

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            response_body = json.loads(response['body'].read())
            return response_body['output']['message']['content'][0]['text']
        except Exception as e:
            logger.error(f"Bedrock Nova invocation failed: {e}")
            raise


class BedrockGemini(ModelProvider):
    """AWS Bedrock Google Gemini model provider"""
    
    def __init__(self, model_id: str, client):
        self.model_id = model_id
        self.client = client
    
    async def invoke(self, messages: List[Dict], **kwargs) -> str:
        """Invoke Gemini via Bedrock"""
        
        # Format messages for Gemini
        system_prompt = ""
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": kwargs.get("max_tokens", 8192),
            "temperature": kwargs.get("temperature", 0.7),
            "system": system_prompt,
            "messages": user_messages
        }
        
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
        except Exception as e:
            logger.error(f"Bedrock Gemini invocation failed: {e}")
            raise


class BedrockOpenAI(ModelProvider):
    """AWS Bedrock OpenAI model provider"""
    
    def __init__(self, model_id: str, client):
        self.model_id = model_id
        self.client = client
    
    async def invoke(self, messages: List[Dict], **kwargs) -> str:
        """Invoke OpenAI via Bedrock"""
        
        # Format messages for OpenAI
        system_prompt = ""
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.7),
            "system": system_prompt,
            "messages": user_messages
        }
        
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
        except Exception as e:
            logger.error(f"Bedrock OpenAI invocation failed: {e}")
            raise


class ModelFactory:
    """Factory for creating model providers - All via AWS Bedrock"""
    
    def __init__(self, bedrock_client):
        self.bedrock_client = bedrock_client
        self.providers = {}
    
    def get_provider(self, agent_name: str) -> ModelProvider:
        """Get model provider for specific agent - All via Bedrock"""
        
        if agent_name in self.providers:
            return self.providers[agent_name]
        
        from src.config import AGENT_MODEL_MAP
        
        model_config = AGENT_MODEL_MAP.get(agent_name)
        if not model_config:
            raise ValueError(f"No model configuration for agent: {agent_name}")
        
        model_id = model_config["model_id"]
        provider_type = model_config["provider"]
        
        # All models via Bedrock
        if provider_type != "bedrock":
            raise ValueError(f"Only Bedrock provider supported. Got: {provider_type}")
        
        # Route to appropriate Bedrock model handler
        if "claude" in model_id:
            provider = BedrockClaude(model_id, self.bedrock_client)
        elif "nova" in model_id:
            provider = BedrockNova(model_id, self.bedrock_client)
        elif "gemini" in model_id or "google" in model_id:
            provider = BedrockGemini(model_id, self.bedrock_client)
        elif "gpt" in model_id or "openai" in model_id:
            provider = BedrockOpenAI(model_id, self.bedrock_client)
        else:
            raise ValueError(f"Unsupported Bedrock model: {model_id}")
        
        self.providers[agent_name] = provider
        logger.info(f"Created Bedrock provider for {agent_name}: {model_id}")
        return provider


def create_bedrock_client(region='us-east-1'):
    """Create AWS Bedrock runtime client using SSO credentials"""

    config = Config(
        region_name=region,
        retries={'max_attempts': 3, 'mode': 'adaptive'},
        read_timeout=300,
        connect_timeout=60
    )

    # Use boto3.Session() to automatically pick up SSO credentials
    session = boto3.Session()

    bedrock_runtime = session.client(
        service_name='bedrock-runtime',
        config=config,
        region_name=region
    )

    return bedrock_runtime
