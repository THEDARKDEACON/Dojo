#!/bin/bash

# Exit on error
set -e

echo "Installing build dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool \
    python3-pip \
    python3-rosinstall \
    python3-rosinstall-generator \
    python3-wstool \
    build-essential \
    cmake \
    git \
    python3-colcon-mixin \
    python3-rosdep \
    python3-vcstool \
    wget

# Initialize rosdep if not already done
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    echo "Initializing rosdep..."
    sudo rosdep init || true
fi

# Update rosdep
echo "Updating rosdep..."
rosdep update --rosdistro=$ROS_DISTRO

# Install workspace dependencies
echo "Installing workspace dependencies..."
cd "$(dirname "$0")/.."
rosdep install --from-paths src --ignore-src -r -y --skip-keys="libopencv-dev libopencv-contrib-dev libopencv-imgproc-dev python-opencv python3-opencv"

echo "Dependencies installed successfully!"
echo "You can now build the workspace with: colcon build --symlink-install"
