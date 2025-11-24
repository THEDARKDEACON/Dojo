#!/bin/bash
# STABLE ROSbot XL Configuration - Tested and Working
# This launches with proven-stable features only

cd /home/gareth-joel/Downloads/Dojo

# Setup environment
source /home/gareth-joel/anaconda3/etc/profile.d/conda.sh
conda activate Pytorch
source install/setup.bash

echo "========================================="
echo "🚀 STABLE ROSbot XL Launch"
echo "========================================="
echo "Features: Gazebo + SLAM + Semantic SLAM"
echo ""

# Launch with STABLE configuration
ros2 launch launch_dojo_rosbot_xl.py \
    world:=office \
    slam:=true \
    semantic_slam:=true \
    gaussian_splatting:=false \
    advanced_safety:=false \
    performance_dashboard:=false \
    pointcloud_viz:=false \
    semantic_interface:=false \
    autonomous_exploration:=false \
    navigation:=false \
    gui:=true \
    rviz:=true
