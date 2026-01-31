"""Script to update all agents to use new create_agent API"""

import re
from pathlib import Path

# Agent directories to update
AGENTS = [
    "maintenance",
    "regulatory", 
    "network",
    "guest_experience",
    "cargo",
    "finance"
]

def update_agent_file(agent_path: Path):
    """Update a single agent file"""
    content = agent_path.read_text()
    
    # Replace imports
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
    
    # Remove validation logic (find and remove the validation block)
    validation_pattern = r'(\s+)# Validate required information.*?return \{[^}]+\}\s+'
    content = re.sub(validation_pattern, '', content, flags=re.DOTALL)
    
    # Update agent creation pattern
    # Old: llm_with_structured_output = llm.with_structured_output(Schema)
    #      graph = create_react_agent(llm_with_structured_output, tools=...)
    # New: agent = create_agent(model=llm, tools=..., response_format=Schema)
    
    # This is complex, so we'll do it manually for each agent
    # For now, just save the import changes
    
    agent_path.write_text(content)
    print(f"✓ Updated imports for {agent_path.parent.name}")

def main():
    src_path = Path("src/agents")
    
    for agent_name in AGENTS:
        agent_file = src_path / agent_name / "agent.py"
        if agent_file.exists():
            try:
                update_agent_file(agent_file)
            except Exception as e:
                print(f"✗ Error updating {agent_name}: {e}")
        else:
            print(f"✗ File not found: {agent_file}")

if __name__ == "__main__":
    main()
