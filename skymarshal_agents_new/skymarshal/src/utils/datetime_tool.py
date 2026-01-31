"""
Date/Time Utility Tool for SkyMarshal Agents

This module provides a simple utility function to get the current UTC datetime.
Agents use this tool to resolve relative dates when needed.

Date parsing from natural language is handled by LangChain structured output,
not by custom parsing functions in this module.
"""

from datetime import datetime, timezone
from langchain_core.tools import tool


def get_current_datetime() -> datetime:
    """
    Get the current UTC datetime.
    
    Used by agents to resolve relative dates and provide context for date extraction.
    
    Returns:
        datetime: Current UTC datetime with timezone info
        
    Example:
        >>> current = get_current_datetime()
        >>> print(current.strftime("%Y-%m-%d"))
        2026-01-31
    """
    return datetime.now(timezone.utc)


@tool
def get_current_datetime_tool() -> str:
    """Returns current UTC datetime for date resolution.
    
    Use this tool when you need to resolve relative dates like 'yesterday', 
    'today', or 'tomorrow', or when you need the current date/time for context.
    
    Returns:
        str: Current UTC datetime in ISO 8601 format (YYYY-MM-DDTHH:MM:SS.ffffff+00:00)
    """
    return get_current_datetime().isoformat()
