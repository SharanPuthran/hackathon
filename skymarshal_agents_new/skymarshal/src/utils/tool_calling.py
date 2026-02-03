"""
Custom tool calling implementation for Bedrock compatibility.

This module provides a workaround for LangChain's create_agent adding extra metadata
fields (like 'index', 'id') to tool results that Bedrock's API validation rejects.

The error: "messages.X.content.Y.tool_result.content.0.text.id: Extra inputs are not permitted"

Solution: Manually implement the tool calling loop with clean message formatting.
"""

import logging
import json
import time
from typing import Any, List, Dict

logger = logging.getLogger(__name__)


async def invoke_with_tools(
    llm: Any,
    system_prompt: str,
    user_message: str,
    tools: List[Any],
    max_iterations: int = 5
) -> Dict[str, Any]:
    """
    Invoke LLM with tools using a custom tool calling loop that avoids extra metadata.
    
    This function manually implements the tool calling loop to ensure clean message
    formatting that Bedrock accepts, without the extra 'index' and 'id' fields that
    LangChain's create_agent adds.
    
    Args:
        llm: ChatBedrock model instance
        system_prompt: System prompt for the agent
        user_message: User message to process
        tools: List of LangChain tools
        max_iterations: Maximum number of tool calling iterations
    
    Returns:
        Dict with final response and metadata
    """
    overall_start = time.time()
    
    # Bind tools to the model
    bind_start = time.time()
    llm_with_tools = llm.bind_tools(tools)
    bind_time = time.time() - bind_start
    logger.info(f"⏱️  Tool binding took {bind_time:.3f}s")
    
    # Initialize messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    iteration = 0
    total_llm_time = 0
    total_tool_time = 0
    
    while iteration < max_iterations:
        iteration += 1
        iter_start = time.time()
        logger.info(f"🔄 Tool calling iteration {iteration}/{max_iterations}")
        
        try:
            # Invoke model
            llm_start = time.time()
            response = await llm_with_tools.ainvoke(messages)
            llm_time = time.time() - llm_start
            total_llm_time += llm_time
            logger.info(f"⏱️  LLM invocation took {llm_time:.3f}s")
            
            # Check if model wants to use tools
            if not response.tool_calls:
                # No more tool calls, return final response
                iter_time = time.time() - iter_start
                total_time = time.time() - overall_start
                logger.info(f"✅ No tool calls in response, returning final answer")
                logger.info(f"⏱️  Iteration {iteration} took {iter_time:.3f}s")
                logger.info(f"⏱️  TOTAL: {total_time:.3f}s (LLM: {total_llm_time:.3f}s, Tools: {total_tool_time:.3f}s, Overhead: {total_time - total_llm_time - total_tool_time:.3f}s)")
                return {
                    "messages": messages + [response],
                    "final_response": response,
                    "iterations": iteration,
                    "timing": {
                        "total": total_time,
                        "llm": total_llm_time,
                        "tools": total_tool_time,
                        "overhead": total_time - total_llm_time - total_tool_time
                    }
                }
            
            logger.info(f"🔧 Model requested {len(response.tool_calls)} tool call(s)")
            
            # Add assistant message with tool calls
            messages.append(response)
            
            # Execute each tool call
            tool_results = []
            for idx, tool_call in enumerate(response.tool_calls, 1):
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call["id"]
                
                logger.info(f"🔧 [{idx}/{len(response.tool_calls)}] Executing tool: {tool_name}")
                logger.debug(f"   Args: {tool_args}")
                
                # Find and execute the tool
                tool_result = None
                tool_exec_start = time.time()
                for tool in tools:
                    if tool.name == tool_name:
                        try:
                            # Execute tool (sync or async)
                            if hasattr(tool, 'ainvoke'):
                                tool_result = await tool.ainvoke(tool_args)
                            else:
                                tool_result = tool.invoke(tool_args)
                            tool_exec_time = time.time() - tool_exec_start
                            total_tool_time += tool_exec_time
                            logger.info(f"⏱️  Tool {tool_name} took {tool_exec_time:.3f}s")
                            logger.debug(f"   Result: {str(tool_result)[:200]}")
                        except Exception as e:
                            tool_exec_time = time.time() - tool_exec_start
                            total_tool_time += tool_exec_time
                            logger.error(f"❌ Tool {tool_name} failed after {tool_exec_time:.3f}s: {e}")
                            tool_result = json.dumps({"error": str(e), "error_type": type(e).__name__})
                        break
                
                if tool_result is None:
                    tool_exec_time = time.time() - tool_exec_start
                    logger.error(f"❌ Tool {tool_name} not found (searched for {tool_exec_time:.3f}s)")
                    tool_result = json.dumps({"error": f"Tool {tool_name} not found"})
                
                # Format tool result message - CLEAN FORMAT for Bedrock
                # Only include required fields, no extra metadata
                tool_results.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_call_id,
                            "content": str(tool_result)
                        }
                    ]
                })
            
            # Add all tool results to messages
            messages.extend(tool_results)
            
            iter_time = time.time() - iter_start
            logger.info(f"⏱️  Iteration {iteration} completed in {iter_time:.3f}s")
            
        except Exception as e:
            iter_time = time.time() - iter_start
            total_time = time.time() - overall_start
            logger.error(f"❌ Error in tool calling loop after {iter_time:.3f}s: {e}")
            logger.info(f"⏱️  TOTAL before error: {total_time:.3f}s (LLM: {total_llm_time:.3f}s, Tools: {total_tool_time:.3f}s)")
            return {
                "messages": messages,
                "error": str(e),
                "error_type": type(e).__name__,
                "iterations": iteration,
                "timing": {
                    "total": total_time,
                    "llm": total_llm_time,
                    "tools": total_tool_time,
                    "overhead": total_time - total_llm_time - total_tool_time
                }
            }
    
    # Max iterations reached
    total_time = time.time() - overall_start
    logger.warning(f"⚠️  Max iterations ({max_iterations}) reached after {total_time:.3f}s")
    logger.info(f"⏱️  TOTAL: {total_time:.3f}s (LLM: {total_llm_time:.3f}s, Tools: {total_tool_time:.3f}s, Overhead: {total_time - total_llm_time - total_tool_time:.3f}s)")
    return {
        "messages": messages,
        "error": "Max iterations reached",
        "iterations": iteration,
        "timing": {
            "total": total_time,
            "llm": total_llm_time,
            "tools": total_tool_time,
            "overhead": total_time - total_llm_time - total_tool_time
        }
    }
