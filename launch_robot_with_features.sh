#!/bin/bash
"""
Modular Robot Launch Script
Launch the robot with specific advanced features
"""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 MODULAR ROBOT LAUNCH SYSTEM${NC}"
echo "=================================="

# Function to launch in new terminal
launch_in_terminal() {
    local title=$1
    local command=$2
    echo -e "${GREEN}🚀 Launching: $title${NC}"
    gnome-terminal --title="$title" -- bash -c "source install/setup.bash && $command; exec bash" &
    sleep 2
}

# Parse command line arguments
WORLD=${1:-mapping_world}
FEATURES=${2:-basic}

echo -e "${YELLOW}World: $WORLD${NC}"
echo -e "${YELLOW}Features: $FEATURES${NC}"
echo ""

# Launch base robot simulation
echo -e "${BLUE}📡 Starting Base Robot Simulation...${NC}"
launch_in_terminal "Robot Simulation" "ros2 launch complete_robot_simulation.launch.py world:=$WORLD.world"

# Wait for base system to initialize
echo "⏳ Waiting for base system to initialize..."
sleep 10

# Launch features based on selection
case $FEATURES in
    "semantic")
        echo -e "${GREEN}🎯 Launching Semantic SLAM...${NC}"
        launch_in_terminal "Semantic SLAM" "ros2 launch robot_semantic_slam semantic_slam.launch.py"
        ;;
    "visualization")
        echo -e "${GREEN}🎨 Launching Enhanced Visualization...${NC}"
        launch_in_terminal "Enhanced Viz" "ros2 launch robot_semantic_slam enhanced_visualization.launch.py"
        ;;
    "safety")
        echo -e "${GREEN}🛡️ Launching Advanced Safety...${NC}"
        launch_in_terminal "Advanced Safety" "ros2 launch robot_semantic_slam advanced_safety.launch.py"
        ;;
    "interface")
        echo -e "${GREEN}🗣️ Launching Natural Language Interface...${NC}"
        launch_in_terminal "Semantic Interface" "ros2 launch robot_semantic_slam semantic_interface.launch.py"
        ;;
    "all")
        echo -e "${GREEN}🚀 Launching All Advanced Features...${NC}"
        launch_in_terminal "All Features" "ros2 launch robot_semantic_slam cutting_edge_features.launch.py"
        ;;
    "basic")
        echo -e "${YELLOW}📋 Basic robot simulation only${NC}"
        ;;
    *)
        echo -e "${RED}❌ Unknown feature set: $FEATURES${NC}"
        echo "Available options: semantic, visualization, safety, interface, all, basic"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Launch complete!${NC}"
echo ""
echo -e "${BLUE}🎮 CONTROL COMMANDS:${NC}"
echo "  📝 Send text command: ros2 topic pub /text_command std_msgs/String \"data: 'go to chair'\""
echo "  📊 Monitor performance: ros2 topic echo /performance_metrics"
echo "  🗺️ View semantic map: ros2 topic echo /semantic_map"
echo "  🛡️ Safety status: ros2 topic echo /safety_status"
echo ""
echo -e "${BLUE}💬 EXAMPLE COMMANDS:${NC}"
echo "  • 'go to chair' - Navigate to nearest chair"
echo "  • 'find bottle' - Locate bottles in the map"
echo "  • 'explore room' - Start autonomous exploration"
echo "  • 'list objects' - Show detected objects"
echo "  • 'stop' - Emergency stop"
echo ""
echo -e "${YELLOW}Press Ctrl+C in any terminal to shutdown that component${NC}"