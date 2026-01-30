#!/bin/bash
# Test all SkyMarshal agents with relevant queries
# Usage: ./test_all_agents.sh

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Base directory
AGENTS_DIR="/Users/sharanputhran/Learning/Hackathon/agents"

# Test queries for each agent
declare -A TEST_QUERIES=(
    ["orchestrator"]="Analyze disruption: Flight EY123 from AUH to LHR has a hydraulic system fault causing a 3-hour delay. 615 passengers onboard, 87 at risk of missing connections."

    ["crew_compliance"]="Check FTL compliance: Flight EY123 delayed 3 hours. Current crew duty time: 9.5 hours. Original flight duty period: 11 hours. Proposed new FDP: 14 hours. Captain has 850 flight hours this year."

    ["maintenance"]="Assess airworthiness: Flight EY123 has Hydraulic System 2 fault. System 1 and backup operational. 3-hour repair time estimated. Aircraft: Boeing 787-9. MEL item 29-51-01."

    ["regulatory"]="Check regulatory compliance: Flight EY123 to London Heathrow (LHR). Original arrival: 22:30 local time. With 3-hour delay, new arrival: 01:30 local time. Check curfew restrictions and slot availability."

    ["network"]="Analyze network impact: Flight EY123 delayed 3 hours. 87 passengers connecting to 12 downstream flights at LHR hub. Key connections: EY12 to JFK (35 PAX), EY456 to SYD (22 PAX). Revenue at risk: estimated $450,000."

    ["guest_experience"]="Assess passenger impact: Flight EY123, 615 passengers affected by 3-hour delay. Passenger breakdown: 48 Business Class, 127 elite frequent flyers (Gold/Platinum), 8 special needs (PRM/UMNR). Flight is EU261 eligible. Calculate compensation and service recovery."

    ["cargo"]="Analyze cargo impact: Flight EY123 carrying 12,500 kg cargo. Critical shipments: 1 pharmaceutical (temperature-controlled, time-sensitive), 2 high-value e-commerce (SLA: next-day delivery). Assess offload requirements for 3-hour delay."

    ["finance"]="Calculate financial impact: Flight EY123, 3-hour delay scenario vs cancellation. 615 PAX × €400 EU261. Network impact: $210K. Compare delay costs vs cancellation costs (estimated $1.2M). Provide cost-benefit analysis."

    ["arbitrator"]="Make final decision: Flight EY123 disruption. Safety assessments: Crew APPROVED (within FTL), Maintenance AIRWORTHY_WITH_MEL, Regulatory CURFEW_RISK. Business impacts: Network $450K revenue risk, Guest €246K compensation, Cargo $85K risk, Finance $508K delay cost vs $1.17M cancel. Recommend optimal scenario."

    ["execution"]="Coordinate execution: Implement decision for Flight EY123. Scenario: Expedited hydraulic repair (3 hours), delay flight, protect 65 high-value connections, provide EU261 compensation, arrange meals/hotels for affected passengers. Break down into executable tasks."
)

# Function to test a single agent
test_agent() {
    local agent_name=$1
    local query="${TEST_QUERIES[$agent_name]}"

    echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC} Testing: ${GREEN}${agent_name}${NC} Agent"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"

    echo -e "${YELLOW}Query:${NC} ${query}\n"

    # Navigate to agent directory
    cd "$AGENTS_DIR/$agent_name" || {
        echo -e "${RED}✗ Agent directory not found: $agent_name${NC}"
        return 1
    }

    # Check if dependencies are installed
    if [ ! -d ".venv" ]; then
        echo -e "${YELLOW}Installing dependencies for $agent_name...${NC}"
        uv sync || {
            echo -e "${RED}✗ Failed to install dependencies${NC}"
            return 1
        }
    fi

    # Start agent in background
    echo -e "${YELLOW}Starting agent server...${NC}"
    agentcore dev > "/tmp/${agent_name}_server.log" 2>&1 &
    SERVER_PID=$!

    # Wait for server to start (max 30 seconds)
    echo -e "${YELLOW}Waiting for server to be ready...${NC}"
    for i in {1..30}; do
        if curl -s http://localhost:8080/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Server ready${NC}"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "${RED}✗ Server failed to start within 30 seconds${NC}"
            kill $SERVER_PID 2>/dev/null || true
            return 1
        fi
        sleep 1
    done

    # Invoke agent with test query
    echo -e "\n${YELLOW}Invoking agent...${NC}\n"
    agentcore invoke --dev "$query" || {
        echo -e "${RED}✗ Agent invocation failed${NC}"
        kill $SERVER_PID 2>/dev/null || true
        return 1
    }

    # Stop the server
    echo -e "\n${YELLOW}Stopping server...${NC}"
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true

    echo -e "${GREEN}✓ Test completed for $agent_name${NC}"

    # Small delay between agents
    sleep 2

    return 0
}

# Main execution
main() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}     ${GREEN}SkyMarshal Multi-Agent System - Test Suite${NC}           ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"

    # Check if agentcore is installed
    if ! command -v agentcore &> /dev/null; then
        echo -e "${RED}✗ agentcore CLI not found. Please install:${NC}"
        echo "  pip install bedrock-agentcore-starter-toolkit"
        exit 1
    fi

    # Array of agents to test
    AGENTS=(
        "orchestrator"
        "crew_compliance"
        "maintenance"
        "regulatory"
        "network"
        "guest_experience"
        "cargo"
        "finance"
        "arbitrator"
        "execution"
    )

    # Test each agent
    SUCCESS_COUNT=0
    FAIL_COUNT=0

    for agent in "${AGENTS[@]}"; do
        if test_agent "$agent"; then
            ((SUCCESS_COUNT++))
        else
            ((FAIL_COUNT++))
        fi
    done

    # Summary
    echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}                    ${GREEN}Test Summary${NC}                            ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo -e "${GREEN}✓ Passed:${NC} $SUCCESS_COUNT"
    echo -e "${RED}✗ Failed:${NC} $FAIL_COUNT"
    echo -e "Total Agents: ${#AGENTS[@]}"

    if [ $FAIL_COUNT -eq 0 ]; then
        echo -e "\n${GREEN}🎉 All agents passed testing!${NC}"
        exit 0
    else
        echo -e "\n${YELLOW}⚠️  Some agents failed. Check logs in /tmp/${NC}"
        exit 1
    fi
}

# Run main function
main
