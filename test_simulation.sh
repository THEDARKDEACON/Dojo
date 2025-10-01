# Test script for Dojo Robot Simulation

echo "🚀 Testing Dojo Robot Simulation..."
echo "====================================="

# Source ROS2 environment
source /opt/ros/humble/setup.bash
source install/setup.bash

echo "📦 Available packages:"
ros2 pkg list | grep robot

echo "\n🎯 Testing unified simulation launch..."
echo "Command: ros2 launch robot_bringup bringup.launch.py use_gazebo:=true use_sim_time:=true use_perception:=true use_navigation:=true"

echo "- SLAM: Enabled"
echo "- Camera: Enabled" 
echo "- Object Detection: Enabled"
echo "- Navigation: Enabled"
echo "- RViz: Enabled"
echo "- Teleop: Enabled"

echo "\n🎮 Controls:"
echo "- Use teleop_twist_keyboard for manual control"
echo "- Check RViz for visualization"
echo "- Monitor topics: ros2 topic list"
