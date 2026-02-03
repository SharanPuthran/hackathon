"""
Utility functions for structured data extraction with model fallback.

This module provides robust extraction functions that automatically retry
with fallback models when throttling errors occur.
"""

import logging
from typing import Any, Type, TypeVar
from pydantic import BaseModel
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


async def extract_with_fallback(
    llm: Any,
    schema: Type[T],
    prompt: str,
    fallback_models: list[str] = None
) -> T:
    """
    Extract structured data with automatic model fallback on throttling.
    
    This function attempts to extract structured data using the provided LLM.
    If throttling occurs, it automatically retries with fallback models.
    
    Args:
        llm: Primary LangChain LLM instance
        schema: Pydantic model class to extract (e.g., FlightInfo)
        prompt: Natural language prompt to extract from
        fallback_models: List of fallback model IDs to try (optional)
        
    Returns:
        Extracted data as instance of schema
        
    Raises:
        Exception: If all models fail or non-throttling error occurs
        
    Example:
        >>> from agents.schemas import FlightInfo
        >>> flight_info = await extract_with_fallback(
        ...     llm=llm,
        ...     schema=FlightInfo,
        ...     prompt="Flight EY123 today had a mechanical failure"
        ... )
    """
    if fallback_models is None:
        fallback_models = [
            "us.amazon.nova-premier-v1:0",
            "us.anthropic.claude-haiku-4-5-20250929-v1:0",
            "us.amazon.nova-pro-v1:0"
        ]
    
    # Try primary model first
    try:
        logger.debug(f"Attempting extraction with primary model: {llm.model_id}")
        structured_llm = llm.with_structured_output(schema)
        result = await structured_llm.ainvoke(prompt)
        logger.debug(f"✅ Extraction successful with primary model")
        return result
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code != 'ThrottlingException':
            # Non-throttling error, re-raise
            logger.error(f"Non-throttling error during extraction: {e}")
            raise
        
        logger.warning(f"⚠️ Primary model throttled, trying fallback models...")
    except Exception as e:
        # Check if it's a throttling exception from botocore
        if 'ThrottlingException' not in str(e):
            logger.error(f"Non-throttling error during extraction: {e}")
            raise
        
        logger.warning(f"⚠️ Primary model throttled, trying fallback models...")
    
    # Try fallback models
    from langchain_aws import ChatBedrock
    
    for model_id in fallback_models:
        try:
            logger.info(f"Trying fallback model: {model_id}")
            fallback_llm = ChatBedrock(
                model_id=model_id,
                region_name="us-east-1",
                model_kwargs={
                    "temperature": 0.3,
                    "max_tokens": 8192
                }
            )
            structured_llm = fallback_llm.with_structured_output(schema)
            result = await structured_llm.ainvoke(prompt)
            logger.info(f"✅ Extraction successful with fallback model: {model_id}")
            return result
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ThrottlingException':
                logger.warning(f"❌ Fallback model {model_id} also throttled")
                continue
            else:
                logger.error(f"Error with fallback model {model_id}: {e}")
                raise
        except Exception as e:
            if 'ThrottlingException' in str(e):
                logger.warning(f"❌ Fallback model {model_id} also throttled")
                continue
            else:
                logger.error(f"Error with fallback model {model_id}: {e}")
                raise
    
    # All models failed
    raise RuntimeError(
        f"All models throttled or unavailable. Tried primary + {len(fallback_models)} fallback models. "
        "Please wait for quota reset or request quota increase."
    )
