#!/bin/bash

# Essential Functionality Test Script - Simplified
# This script runs the comprehensive Python integration test

set -e

echo "=========================================="
echo "Essential Robot Functionality Test"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Running comprehensive system integration test...${NC}"

# Check if ROS2 is sourced
if [ -z "$ROS_DISTRO" ]; then
    echo -e "${YELLOW}Sourcing ROS2 environment...${NC}"
    source /opt/ros/jazzy/setup.bash
fi

# Source workspace if available
if [ -f "install/setup.bash" ]; then
    echo -e "${YELLOW}Sourcing workspace...${NC}"
    source install/setup.bash
fi

# Run the comprehensive integration test
python3 test_system_integration.py

echo -e "${GREEN}Test completed!${NC}"

# Source ROS2 environment
echo "Sourcing ROS2 environment..."
source /opt/ros/jazzy/setup.bash
if [ -f "install/setup.bash" ]; then
    source install/setup.bash
    echo "Sourced workspace setup"
else
    echo -e "${YELLOW}Warning: Workspace not built. Building now...${NC}"
    colcon build --symlink-install
    source install/setup.bash
fi

# Check if Gazebo Harmonic is available
echo "Checking Gazebo Harmonic availability..."
if ! command -v gz &> /dev/null; then
    echo -e "${RED}Error: Gazebo Harmonic (gz) not found${NC}"
    exit 1
fi

echo "Gazebo version:"
gz --version

# Launch simulation in background with minimal configuration
echo -e "\n${YELLOW}Launching robot simulation...${NC}"
echo "Using minimal configuration for testing (no GUI, no vision, no teleop)"

# Launch simulation without GUI and vision to avoid conflicts
ros2 launch complete_robot_simulation.launch.py \
    gui:=false \
    rviz:=false \
    teleop:=false \
    vision:=false \
    slam:=true \
    world:=empty.world &

LAUNCH_PID=$!
echo "Simulation launched with PID: $LAUNCH_PID"

# Wait for simulation to start
echo "Waiting for simulation to initialize..."
sleep 15

# Check if simulation is still running
if ! kill -0 $LAUNCH_PID 2>/dev/null; then
    echo -e "${RED}Error: Simulation failed to start or crashed${NC}"
    exit 1
fi

# Run the validation script
echo -e "\n${YELLOW}Running essential functionality validation...${NC}"
python3 validate_essential_robot_functionality.py &
VALIDATOR_PID=$!

# Wait for validation to complete (timeout after 60 seconds)
timeout 60 wait $VALIDATOR_PID || {
    echo -e "${RED}Validation timed out${NC}"
    kill $VALIDATOR_PID 2>/dev/null || true
    exit 1
}

# Get validation exit code
wait $VALIDATOR_PID
VALIDATION_EXIT_CODE=$?

# Check results
if [ $VALIDATION_EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}✓ Essential functionality validation completed successfully${NC}"
else
    echo -e "\n${RED}✗ Essential functionality validation failed${NC}"
fi

# Additional topic checks
echo -e "\n${YELLOW}Performing additional topic checks...${NC}"

# Check if essential topics exist
echo "Checking topic availability:"
TOPICS_TO_CHECK=("/cmd_vel" "/odom" "/scan" "/camera/image_raw" "/joint_states" "/tf")
ALL_TOPICS_OK=true

for topic in "${TOPICS_TO_CHECK[@]}"; do
    if ros2 topic list | grep -q "^${topic}$"; then
        echo -e "  ${GREEN}✓${NC} $topic - Available"
    else
        echo -e "  ${RED}✗${NC} $topic - Not available"
        ALL_TOPICS_OK=false
    fi
done

# Check topic data rates
echo -e "\nChecking topic data rates (5 second sample):"
for topic in "/odom" "/joint_states" "/tf"; do
    if ros2 topic list | grep -q "^${topic}$"; then
        echo -n "  $topic: "
        RATE=$(timeout 5 ros2 topic hz $topic 2>/dev/null | grep "average rate" | awk '{print $3}' || echo "0")
        if [ "$RATE" != "0" ] && [ -n "$RATE" ]; then
            echo -e "${GREEN}${RATE} Hz${NC}"
        else
            echo -e "${RED}No data${NC}"
            ALL_TOPICS_OK=false
        fi
    fi
done

# Test robot movement capability
echo -e "\n${YELLOW}Testing robot movement capability...${NC}"
echo "Publishing test velocity command..."

# Send a test velocity command
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" &

# Wait a moment then stop
sleep 2
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" &

echo "Movement command sent successfully"

# Final report
echo -e "\n=========================================="
echo "FINAL TEST REPORT"
echo "=========================================="

if [ $VALIDATION_EXIT_CODE -eq 0 ] && [ "$ALL_TOPICS_OK" = true ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo "Essential robot functionality is working correctly"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo "Check the output above for details"
    exit 1
fi