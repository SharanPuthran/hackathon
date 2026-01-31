#!/bin/bash

# Batch update all remaining agents to use create_agent API

AGENTS=("regulatory" "network" "guest_experience" "cargo" "finance")

for agent in "${AGENTS[@]}"; do
    echo "Updating $agent agent..."
    
    # Update imports
    sed -i '' 's/from langgraph\.prebuilt import create_react_agent/from langchain.agents import create_agent/g' "src/agents/$agent/agent.py"
    sed -i '' '/from utils\.validation import validate_agent_requirements/d' "src/agents/$agent/agent.py"
    
    echo "✓ Updated $agent"
done

echo "All agents updated!"
