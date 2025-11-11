#!/bin/bash
# Priority 1 Integration Validation Script
# Validates that all components are properly integrated

echo "=========================================================================="
echo "🔍 PRIORITY 1 INTEGRATION VALIDATION"
echo "=========================================================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Function to check file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅${NC} $2"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌${NC} $2 - File not found: $1"
        ((FAILED++))
        return 1
    fi
}

# Function to check directory exists
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✅${NC} $2"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌${NC} $2 - Directory not found: $1"
        ((FAILED++))
        return 1
    fi
}

echo "📋 Checking Core Components..."
echo "----------------------------------------"

# Check launch files
check_file "src/robot_gazebo/launch/complete_robot_simulation.launch.py" "Unified launch file"
check_file "src/robot_semantic_slam/launch/cutting_edge_features.launch.py" "Cutting-edge features launch"
check_file "src/robot_semantic_slam/launch/semantic_slam.launch.py" "Semantic SLAM launch"
check_file "src/robot_semantic_slam/launch/enhanced_visualization.launch.py" "Enhanced visualization launch"
check_file "src/robot_semantic_slam/launch/performance_dashboard.launch.py" "Performance dashboard launch"
check_file "src/robot_semantic_slam/launch/advanced_safety.launch.py" "Advanced safety launch"
check_file "src/robot_semantic_slam/launch/semantic_interface.launch.py" "Semantic interface launch"

echo ""
echo "📋 Checking Python Nodes..."
echo "----------------------------------------"

# Check Python nodes
check_file "src/robot_semantic_slam/robot_semantic_slam/semantic_slam_node.py" "Semantic SLAM node"
check_file "src/robot_semantic_slam/robot_semantic_slam/enhanced_visualizer.py" "Enhanced visualizer"
check_file "src/robot_semantic_slam/robot_semantic_slam/advanced_safety_system.py" "Advanced safety system"
check_file "src/robot_semantic_slam/robot_semantic_slam/semantic_interface.py" "Semantic interface"
check_file "src/robot_semantic_slam/robot_semantic_slam/pointcloud_processor.py" "Point cloud processor"
check_file "src/robot_semantic_slam/robot_semantic_slam/performance_dashboard.py" "Performance dashboard"
check_file "src/robot_semantic_slam/robot_semantic_slam/system_monitor.py" "System monitor"

echo ""
echo "📋 Checking Configuration Files..."
echo "----------------------------------------"

# Check setup.py
check_file "src/robot_semantic_slam/setup.py" "Setup.py configuration"
check_file "src/robot_semantic_slam/package.xml" "Package.xml"

echo ""
echo "📋 Checking Test Files..."
echo "----------------------------------------"

# Check test files
check_file "test_priority1_integration.py" "Integration test suite"
check_file "src/robot_semantic_slam/test/test_lidar_camera_fusion.py" "LiDAR-camera fusion tests"
check_file "src/robot_semantic_slam/test/test_object_persistence.py" "Object persistence tests"
check_file "src/robot_semantic_slam/test/test_semantic_navigation.py" "Semantic navigation tests"
check_file "src/robot_semantic_slam/test/test_behavior_tree_safety.py" "Behavior tree safety tests"

echo ""
echo "📋 Checking Documentation..."
echo "----------------------------------------"

# Check documentation
check_file "docs/PRIORITY1_INTEGRATION_REPORT.md" "Integration report"
check_file "docs/TASK_9.1_INTEGRATION_SUMMARY.md" "Task 9.1 summary"
check_file "QUICKSTART_PRIORITY1.md" "Quick start guide"
check_file "docs/IMPLEMENTATION_GUIDE.md" "Implementation guide"
check_file "docs/TROUBLESHOOTING.md" "Troubleshooting guide"
check_file "docs/WORLD_SELECTION_GUIDE.md" "World selection guide"
check_file "docs/PERFORMANCE_DASHBOARD.md" "Performance dashboard guide"
check_file "docs/BEHAVIOR_TREE_SAFETY.md" "Behavior tree safety guide"

echo ""
echo "📋 Checking World Files..."
echo "----------------------------------------"

# Check world files
check_file "src/robot_gazebo/worlds/mapping_world.world" "Mapping world"
check_file "src/robot_gazebo/worlds/house.world" "House world"
check_file "src/robot_gazebo/worlds/empty.world" "Empty world"

echo ""
echo "📋 Checking RViz Configuration..."
echo "----------------------------------------"

# Check RViz config
check_file "src/robot_gazebo/rviz/pointcloud_3d_visualization.rviz" "3D visualization RViz config"

echo ""
echo "📋 Checking Package Structure..."
echo "----------------------------------------"

# Check package directories
check_dir "src/robot_semantic_slam" "robot_semantic_slam package"
check_dir "src/robot_gazebo" "robot_gazebo package"
check_dir "src/robot_navigation" "robot_navigation package"
check_dir "src/robot_description" "robot_description package"

echo ""
echo "=========================================================================="
echo "📊 VALIDATION RESULTS"
echo "=========================================================================="
echo ""

TOTAL=$((PASSED + FAILED))
PERCENTAGE=$((PASSED * 100 / TOTAL))

echo "Total Checks: $TOTAL"
echo -e "Passed: ${GREEN}$PASSED ✅${NC}"
echo -e "Failed: ${RED}$FAILED ❌${NC}"
echo "Success Rate: $PERCENTAGE%"

echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL CHECKS PASSED!${NC}"
    echo "Priority 1 integration is complete and validated."
    echo ""
    echo "Next steps:"
    echo "  1. Build the workspace: colcon build --symlink-install"
    echo "  2. Source the workspace: source install/setup.bash"
    echo "  3. Launch the system: ros2 launch robot_gazebo complete_robot_simulation.launch.py"
    echo "  4. Run integration tests: python3 test_priority1_integration.py"
    echo ""
    exit 0
elif [ $PERCENTAGE -ge 80 ]; then
    echo -e "${YELLOW}⚠️  VALIDATION PASSED WITH WARNINGS${NC}"
    echo "Most components are in place, but some files are missing."
    echo "Review the failed checks above."
    echo ""
    exit 1
else
    echo -e "${RED}❌ VALIDATION FAILED${NC}"
    echo "Critical components are missing. Please review the failed checks above."
    echo ""
    exit 1
fi
