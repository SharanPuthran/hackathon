#!/usr/bin/env python3
"""Update all remaining agents to use create_agent API"""

import re
from pathlib import Path

AGENTS_TO_UPDATE = [
    "regulatory",
    "network", 
    "guest_experience",
    "cargo",
    "finance"
]

def update_agent_imports(content: str) -> str:
    """Update imports in agent file"""
    # Replace create_react_agent import
    content = re.sub(
        r'from langgraph\.prebuilt import create_react_agent',
        'from langchain.agents import create_agent',
        content
    )
    
    # Remove validation import
    content = re.sub(
        r'from utils\.validation import validate_agent_requirements\n',
        '',
        content
    )
    
    return content

def update_agent_function(content: str, agent_name: str, schema_name: str) -> str:
    """Update the analyze function to use create_agent"""
    
    # Remove validation block
    validation_pattern = r'(\s+)# Validate required information.*?return \{[^}]+\}\s+\n'
    content = re.sub(validation_pattern, '', content, flags=re.DOTALL)
    
    # Update agent creation
    old_pattern = r'# Configure model with structured output\s+llm_with_structured_output = llm\.with_structured_output\(\s+' + schema_name + r', method="tool_calling", include_raw=False\s+\)\s+# Create (?:LangGraph )?agent.*?\s+graph = create_react_agent\(\s+llm_with_structured_output, tools=mcp_tools \+ db_tools\s+\)'
    
    new_code = f'''# Create agent with structured output
        agent = create_agent(
            model=llm,
            tools=mcp_tools + db_tools,
            response_format={schema_name},
        )'''
    
    content = re.sub(old_pattern, new_code, content, flags=re.DOTALL)
    
    # Update message building
    old_message_pattern = r'message = f""".*?"""'
    new_message = f'''system_message = f"""{{SYSTEM_PROMPT}}

IMPORTANT: 
1. Extract flight and disruption information from the prompt
2. Use database tools to retrieve required operational data
3. Perform {agent_name} analysis
4. If you cannot extract required information, ask for clarification
5. If database tools fail, return a FAILURE response

Provide analysis using the {schema_name} schema."""'''
    
    content = re.sub(old_message_pattern, new_message, content, flags=re.DOTALL)
    
    # Update invocation
    old_invoke = r'result = await graph\.ainvoke\(\{"messages": \[HumanMessage\(content=message\)\]\}\)'
    new_invoke = '''result = await agent.ainvoke({
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
        })'''
    
    content = re.sub(old_invoke, new_invoke, content)
    
    # Remove disruption variable usage
    content = re.sub(r'\s+disruption = payload\.get\("disruption", \{\}\)\s+', '\n        ', content)
    
    return content

def main():
    src_path = Path("src/agents")
    
    schema_map = {
        "regulatory": "RegulatoryOutput",
        "network": "NetworkOutput",
        "guest_experience": "GuestExperienceOutput",
        "cargo": "CargoOutput",
        "finance": "FinanceOutput"
    }
    
    for agent_name in AGENTS_TO_UPDATE:
        agent_file = src_path / agent_name / "agent.py"
        
        if not agent_file.exists():
            print(f"✗ File not found: {agent_file}")
            continue
            
        try:
            content = agent_file.read_text()
            
            # Update imports
            content = update_agent_imports(content)
            
            # Update function (simplified - just do imports for now)
            # Full function update is complex, will do manually
            
            agent_file.write_text(content)
            print(f"✓ Updated imports for {agent_name}")
            
        except Exception as e:
            print(f"✗ Error updating {agent_name}: {e}")

if __name__ == "__main__":
    main()
