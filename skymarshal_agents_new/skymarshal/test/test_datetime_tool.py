"""
Unit tests for datetime_tool module.

Tests the get_current_datetime function which provides current UTC time for agents.
Date parsing is handled by LangChain structured output, not by custom functions.
"""

import pytest
from datetime import datetime, timezone
from utils.datetime_tool import get_current_datetime, get_current_datetime_tool


class TestGetCurrentDatetime:
    """Tests for get_current_datetime function."""
    
    def test_returns_datetime(self):
        """Should return a datetime object."""
        result = get_current_datetime()
        assert isinstance(result, datetime)
    
    def test_returns_utc_time(self):
        """Should return UTC time with timezone info."""
        result = get_current_datetime()
        # Verify it's a valid datetime
        assert result.year >= 2024
        # Verify it has timezone info (UTC)
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc
    
    def test_returns_current_time(self):
        """Should return a time close to the actual current time."""
        before = datetime.now(timezone.utc)
        result = get_current_datetime()
        after = datetime.now(timezone.utc)
        
        # Result should be between before and after (within a few seconds)
        assert before <= result <= after
    
    def test_consistent_timezone(self):
        """Should always return UTC timezone."""
        result1 = get_current_datetime()
        result2 = get_current_datetime()
        
        assert result1.tzinfo == timezone.utc
        assert result2.tzinfo == timezone.utc


class TestGetCurrentDatetimeTool:
    """Tests for get_current_datetime_tool LangChain Tool decorator."""
    
    def test_tool_has_correct_name(self):
        """Tool should have the correct name."""
        assert get_current_datetime_tool.name == "get_current_datetime_tool"
    
    def test_tool_has_description(self):
        """Tool should have a description."""
        assert get_current_datetime_tool.description
        assert len(get_current_datetime_tool.description) > 0
        assert "UTC" in get_current_datetime_tool.description
        assert "datetime" in get_current_datetime_tool.description.lower()
    
    def test_tool_returns_string(self):
        """Tool should return a string when invoked."""
        result = get_current_datetime_tool.invoke({})
        assert isinstance(result, str)
    
    def test_tool_returns_valid_datetime_string(self):
        """Tool should return a valid ISO format datetime string."""
        result = get_current_datetime_tool.invoke({})
        # Should be parseable as datetime
        parsed = datetime.fromisoformat(result)
        assert isinstance(parsed, datetime)
        assert parsed.tzinfo is not None
    
    def test_tool_returns_utc_timezone(self):
        """Tool should return datetime with UTC timezone."""
        result = get_current_datetime_tool.invoke({})
        parsed = datetime.fromisoformat(result)
        assert parsed.tzinfo == timezone.utc
    
    def test_tool_is_callable(self):
        """Tool should be callable directly."""
        # The @tool decorator creates a callable tool
        result = get_current_datetime_tool.invoke({})
        assert isinstance(result, str)
        # Should be parseable as datetime
        parsed = datetime.fromisoformat(result)
        assert isinstance(parsed, datetime)

