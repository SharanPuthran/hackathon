#!/usr/bin/env python3
"""
Test tool result formatting to debug Bedrock validation error.
"""

import asyncio
import boto3
from langchain.tools import tool
from langchain_aws import ChatBedrock


@tool
def test_tool(input_text: str) -> str:
    """A simple test tool."""
    return f"Processed: {input_text}"


async def test_tool_invocation():
    """Test tool invocation with Bedrock."""
    
    print("Testing tool invocation with Bedrock...")
    
    # Create model
    llm = ChatBedrock(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
        model_kwargs={
            "temperature": 0.1,
            "max_tokens": 1000
        }
    )
    
    # Bind tool
    llm_with_tools = llm.bind_tools([test_tool])
    
    try:
        # Invoke with a prompt that should trigger tool use
        response = await llm_with_tools.ainvoke("Use the test_tool with input 'hello world'")
        print(f"Response: {response}")
        print(f"Response type: {type(response)}")
        print(f"Response content: {response.content}")
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print(f"Tool calls: {response.tool_calls}")
            
    except Exception as e:
        print(f"Error: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_tool_invocation())
