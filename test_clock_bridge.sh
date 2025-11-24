#!/usr/bin/env bash
# Test script to manually start Gazebo and clock bridge

echo "=== Testing Gazebo Clock Bridge ==="
echo "Gazebo version: $(gz sim --versions)"
echo ""

# Start Gazebo in background
echo "Starting Gazebo..."
gz sim -r ~/Downloads/Dojo/install/husarion_gz_worlds/share/husarion_gz_worlds/worlds/office.sdf &
GZ_PID=$!
echo "Gazebo PID: $GZ_PID"

sleep 5

# Check Gazebo topics
echo ""
echo "=== Gazebo Topics ==="
gz topic -l | head -20

# Try to bridge the clock
echo ""
echo "=== Starting Clock Bridge ==="
source install/setup.bash
ros2 run ros_gz_bridge parameter_bridge /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock] &
BRIDGE_PID=$!
echo "Bridge PID: $BRIDGE_PID"

sleep 3

# Check ROS 2 topics
echo ""
echo "=== ROS 2 Topics ==="
ros2 topic list | grep clock

echo ""
echo "=== Testing Clock Publishing ==="
timeout 3 ros2 topic hz /clock || echo "Clock not publishing!"

# Cleanup
echo ""
echo "=== Cleanup ==="
kill $BRIDGE_PID 2>/dev/null
kill $GZ_PID 2>/dev/null
wait $GZ_PID 2>/dev/null

echo "Test complete"
