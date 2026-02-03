"""
Script to update all agents to use custom tool calling instead of create_agent.
This fixes the Bedrock API validation error with extra metadata fields.
"""

import re
from pathlib import Path

# Agent files to update
AGENT_FILES = [
    "src/agents/regulatory/agent.py",
    "src/agents/maintenance/agent.py",
    "src/agents/network/agent.py",
    "src/agents/guest_experience/agent.py",
    "src/agents/cargo/agent.py",
    "src/agents/finance/agent.py",
]

def update_imports(content: str) -> str:
    """Update imports to use invoke_with_tools instead of create_agent"""
    # Remove create_agent import
    content = re.sub(
        r'from langchain\.agents import create_agent\n',
        '',
        content
    )
    
    # Add invoke_with_tools import if not present
    if 'from utils.tool_calling import invoke_with_tools' not in content:
        # Find the langchain imports section and add after it
        content = re.sub(
            r'(from langchain_core\.messages import HumanMessage\n)',
            r'\1\nfrom utils.tool_calling import invoke_with_tools',
            content
        )
    
    return content

def update_agent_invocation(content: str) -> str:
    """Replace create_agent and agent.ainvoke with invoke_with_tools"""
    
    # Pattern 1: Find and replace create_agent block
    content = re.sub(
        r'# Create agent.*?\n\s+agent = create_agent\(\s*model=llm,\s*tools=[^,]+,?\s*(?:response_format=[^,]+,?)?\s*\)',
        '# Use custom tool calling to avoid LangChain metadata issues',
        content,
        flags=re.DOTALL
    )
    
    # Pattern 2: Replace agent.ainvoke with invoke_with_tools
    content = re.sub(
        r'result = await agent\.ainvoke\(\{\s*"messages": \[\s*\{"role": "system", "content": SYSTEM_PROMPT\},\s*\{"role": "user", "content": user_message\}\s*\]\s*\}\)',
        '''result = await invoke_with_tools(
                llm=llm,
                system_prompt=SYSTEM_PROMPT,
                user_message=user_message,
                tools=all_tools,
                max_iterations=5
            )''',
        content,
        flags=re.DOTALL
    )
    
    # Pattern 3: Add error handling for tool calling
    # Find the try block after invoke and add error handling
    if 'result = await invoke_with_tools' in content and 'if "error" in result:' not in content:
        content = re.sub(
            r'(result = await invoke_with_tools\([^)]+\))\s*\n',
            r'''\1
        
        # Check for tool calling errors
        if "error" in result:
            error_type = result.get("error_type", "UnknownError")
            logger.error(f"Tool calling failed ({error_type}): {result['error']}")
            
            return {
                "agent_name": agent_name,
                "recommendation": "CANNOT_PROCEED",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": f"Tool calling error: {result['error']}",
                "data_sources": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": result["error"],
                "error_type": error_type
            }
        
''',
            content,
            flags=re.DOTALL
        )
    
    return content

def fix_agent_file(filepath: Path):
    """Fix a single agent file"""
    print(f"Fixing {filepath}...")
    
    content = filepath.read_text()
    
    # Update imports
    content = update_imports(content)
    
    # Update agent invocation
    content = update_agent_invocation(content)
    
    # Write back
    filepath.write_text(content)
    print(f"  ✓ Fixed {filepath}")

def main():
    """Main function"""
    print("🔧 Fixing all agents to use custom tool calling...")
    print()
    
    for agent_file in AGENT_FILES:
        filepath = Path(agent_file)
        if filepath.exists():
            try:
                fix_agent_file(filepath)
            except Exception as e:
                print(f"  ✗ Error fixing {filepath}: {e}")
        else:
            print(f"  ⚠ File not found: {filepath}")
    
    print()
    print("✅ All agents fixed!")
    print()
    print("Next steps:")
    print("1. Restart AgentCore dev server")
    print("2. Run performance tests")

if __name__ == "__main__":
    main()
