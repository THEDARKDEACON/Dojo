#!/bin/bash

echo "🔧 Quick Arduino Driver Fix"

# Source ROS 2
source /opt/ros/humble/setup.bash

# Clean and rebuild only robot_hardware
echo "🧹 Cleaning robot_hardware..."
rm -rf build/robot_hardware install/robot_hardware

echo "🔨 Building robot_hardware..."
colcon build --packages-select robot_hardware --symlink-install

if [ $? -eq 0 ]; then
    echo "✅ robot_hardware built successfully"
    
    # Source the workspace
    source install/setup.bash
    
    echo "🚀 Testing Arduino driver..."
    echo "You can now run:"
    echo "  ros2 launch robot_hardware arduino_only.launch.py port:=/dev/ttyACM0 debug:=true"
    echo ""
    echo "In another terminal, test with teleop:"
    echo "  ros2 run teleop_twist_keyboard teleop_twist_keyboard"
else
    echo "❌ Failed to build robot_hardware"
    exit 1
fi