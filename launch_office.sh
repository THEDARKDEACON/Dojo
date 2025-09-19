#!/bin/bash

echo "🏢 Launching Dojo Robot in Office Environment"
echo "=============================================="

echo "Starting simulation with:"
echo "• World: office_small.world"
echo "• SLAM mapping enabled"
echo "• Camera and LiDAR active"
echo "• Teleop control available"

echo ""
echo "Controls:"
echo "• i = forward"
echo "• j = turn left" 
echo "• l = turn right"
echo "• k = stop"
echo "• , = backward"

echo ""
echo "🚀 Launching..."

ros2 launch robot_gazebo complete_simulation.launch.py world:=office_small.world