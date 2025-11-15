#!/bin/bash
# Basic robot launch without cutting-edge features (to avoid Gazebo crashes)

echo "🚀 Starting Basic Dojo Robot Simulation"
echo "========================================"

# Source ROS 2
source /opt/ros/jazzy/setup.bash

# Source workspace
source install/setup.bash

# Launch with basic features only (no semantic SLAM to avoid crashes)
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    world:=mapping_world \
    slam:=true \
    semantic_slam:=false \
    pointcloud_viz:=false \
    performance_dashboard:=false \
    advanced_safety:=false \
    semantic_interface:=false \
    gui:=true \
    rviz:=true

echo "🏁 Simulation ended"
