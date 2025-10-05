#!/bin/bash

echo "🤖 Dojo Robot Front-Wheel Drive Test"
echo "===================================="

# Source the workspace
source install/setup.bash

echo "📋 Available Topics:"
echo "Control Topics:"
echo "  /cmd_vel - Direct robot control"
echo "  /cmd_vel_teleop - Teleop control (through twist_mux)"
echo "  /cmd_vel_nav - Navigation control"
echo "  /cmd_vel_safety - Safety override"
echo ""
echo "Sensor Topics:"
echo "  /camera/image_raw - Camera feed"
echo "  /camera/camera_info - Camera info"
echo "  /scan - LiDAR data"
echo ""
echo "Status Topics:"
echo "  /odom - Robot odometry"
echo "  /joint_states - Joint positions"
echo ""

echo "🎮 Robot Control Commands:"
echo ""
echo "1. Direct Control:"
echo "   ros2 topic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0.2}, angular: {z: 0.0}}'"
echo ""
echo "2. Teleop Control (Recommended):"
echo "   ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r /cmd_vel:=/cmd_vel_teleop"
echo ""
echo "3. Stop Robot:"
echo "   ros2 topic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0.0}, angular: {z: 0.0}}' --once"
echo ""

echo "📊 Monitor Robot:"
echo "   ros2 topic echo /odom"
echo "   ros2 topic echo /scan"
echo "   ros2 topic list"
echo ""

echo "🚀 Launch Full Simulation:"
echo "   ros2 launch robot_gazebo simulation_with_teleop.launch.py"
echo ""

echo "Robot Configuration:"
echo "✅ Front-wheel drive (2 motors + 2 rear casters)"
echo "✅ Camera sensor (/camera/image_raw)"
echo "✅ LiDAR sensor (/scan)"
echo "✅ Twist mux for priority-based control"
echo "✅ SLAM capability for mapping"