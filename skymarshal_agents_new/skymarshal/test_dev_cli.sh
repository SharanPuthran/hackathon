#!/bin/bash

# Performance test for AgentCore dev mode using CLI
# Run this while agentcore dev is running

echo "================================================================================"
echo "SKYMARSHAL AGENT PERFORMANCE TEST (CLI)"
echo "================================================================================"
echo "Started at: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Test payloads - natural language descriptions with EY flight numbers
# Mix of relative and absolute dates
TEST1="Flight EY101 from JFK to LAX scheduled for tomorrow at 10:00 AM is experiencing severe weather delays at the departure airport. Please analyze the impact and provide recommendations."

TEST2="Flight EY202 from ORD to SFO scheduled for 2026-02-04 at 14:30 has a mechanical issue requiring maintenance inspection. The flight has 180 passengers and 5000 kg of cargo. Analyze the impact and recommend whether to repair or swap aircraft."

TEST3="Flight EY305 departing from Denver (DEN) in 3 hours is affected by a severe snowstorm that has closed the airport. The closure is expected to last 6 hours. Analyze the network impact and provide recovery recommendations."

TEST4="Flight EY450 from AUH to LHR scheduled for 2026-02-05 at 08:15 is delayed by 4 hours due to crew rest requirements. There are 250 passengers on board with 45 connecting flights. What are the implications?"

TEST5="Flight EY789 departing today at 18:00 from SFO to JFK has a cargo loading issue. 8000 kg of priority cargo cannot be loaded due to weight restrictions. Analyze options."

# Function to run test
run_test() {
    local test_name=$1
    local payload=$2
    
    echo "Test: $test_name"
    echo "--------------------------------------------------------------------------------"
    
    start_time=$(date +%s)
    
    # Run the test
    response=$(uv run agentcore invoke --dev "$payload" 2>&1)
    exit_code=$?
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    if [ $exit_code -eq 0 ]; then
        echo "  ✓ Success"
        echo "  Duration: ${duration}s"
        echo "  Response length: ${#response} chars"
        
        # Check for key components
        if echo "$response" | grep -qi "crew\|maintenance\|regulatory\|safety"; then
            echo "  Safety analysis: ✓"
        else
            echo "  Safety analysis: ✗"
        fi
        
        if echo "$response" | grep -qi "network\|guest\|cargo\|finance"; then
            echo "  Business analysis: ✓"
        else
            echo "  Business analysis: ✗"
        fi
        
        if echo "$response" | grep -qi "recommend"; then
            echo "  Recommendations: ✓"
        else
            echo "  Recommendations: ✗"
        fi
        
        # Save response
        echo "$response" > "test_response_${test_name// /_}.txt"
        echo "  Response saved to: test_response_${test_name// /_}.txt"
    else
        echo "  ✗ Failed (exit code: $exit_code)"
        echo "  Duration: ${duration}s"
        echo "  Error: $response"
    fi
    
    echo ""
    
    return $duration
}

# Run tests
echo "Running performance tests..."
echo ""

total_duration=0
test_count=0

run_test "Weather Delay Tomorrow" "$TEST1"
duration1=$?
total_duration=$((total_duration + duration1))
test_count=$((test_count + 1))

run_test "Mechanical Issue Absolute Date" "$TEST2"
duration2=$?
total_duration=$((total_duration + duration2))
test_count=$((test_count + 1))

run_test "Airport Closure Relative Time" "$TEST3"
duration3=$?
total_duration=$((total_duration + duration3))
test_count=$((test_count + 1))

run_test "Crew Rest Delay" "$TEST4"
duration4=$?
total_duration=$((total_duration + duration4))
test_count=$((test_count + 1))

run_test "Cargo Loading Issue Today" "$TEST5"
duration5=$?
total_duration=$((total_duration + duration5))
test_count=$((test_count + 1))

# Summary
echo "================================================================================"
echo "SUMMARY"
echo "================================================================================"
echo ""
echo "Tests Run: $test_count"
echo ""
echo "Timing Statistics:"
echo "  Test 1 (Weather Tomorrow): ${duration1}s"
echo "  Test 2 (Mechanical Absolute): ${duration2}s"
echo "  Test 3 (Airport Closure Relative): ${duration3}s"
echo "  Test 4 (Crew Rest): ${duration4}s"
echo "  Test 5 (Cargo Today): ${duration5}s"
echo "  Total: ${total_duration}s"

if [ $test_count -gt 0 ]; then
    avg_duration=$((total_duration / test_count))
    echo "  Average: ${avg_duration}s"
    
    echo ""
    echo "Performance Assessment:"
    if [ $avg_duration -lt 20 ]; then
        echo "  ✓ EXCELLENT - Average response time < 20s"
    elif [ $avg_duration -lt 30 ]; then
        echo "  ✓ GOOD - Average response time < 30s"
    elif [ $avg_duration -lt 45 ]; then
        echo "  ⚠ ACCEPTABLE - Average response time < 45s"
    else
        echo "  ✗ NEEDS IMPROVEMENT - Average response time > 45s"
    fi
fi

echo ""
echo "Test responses saved to test_response_*.txt files"
echo "================================================================================"
