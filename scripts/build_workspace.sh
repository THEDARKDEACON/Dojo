#!/bin/bash

# Exit on error
set -e

# Source ROS 2 environment
source /opt/ros/humble/setup.bash

# Build the workspace
echo "Building workspace..."
colcon build \
    --symlink-install \
    --cmake-args \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    --packages-up-to \
        robot_description \
        robot_control \
        robot_navigation \
        robot_gazebo \
        robot_bringup

# Source the workspace
echo "Sourcing the workspace..."
source install/setup.bash

echo "Build completed successfully!"
echo "To use this workspace, run: source install/setup.bash"
