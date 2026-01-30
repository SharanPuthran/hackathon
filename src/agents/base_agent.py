"""Base agent class for SkyMarshal"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import logging
import json

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base agent class with multi-model support"""
    
    def __init__(self, name: str, model_factory, db_manager=None):
        self.name = name
        self.model_provider = model_factory.get_provider(name)
        self.db = db_manager
        self.system_prompt = self._load_system_prompt()
    
    @abstractmethod
    def _load_system_prompt(self) -> str:
        """Load agent-specific system prompt"""
        pass
    
    async def invoke(self, user_prompt: str, context: Dict[str, Any], **kwargs) -> str:
        """Invoke LLM with system + user prompt"""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self._format_prompt(user_prompt, context)}
        ]
        
        # Add model-specific parameters
        invoke_kwargs = {
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.7)
        }
        
        try:
            response = await self.model_provider.invoke(messages, **invoke_kwargs)
            logger.info(f"{self.name} completed invocation")
            return response
        except Exception as e:
            logger.error(f"{self.name} invocation failed: {e}")
            raise
    
    def _format_prompt(self, prompt: str, context: Dict[str, Any]) -> str:
        """Format prompt with context"""
        context_str = json.dumps(context, indent=2, default=str)
        return f"{prompt}\n\nContext:\n{context_str}"
