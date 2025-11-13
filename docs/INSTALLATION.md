# Installation Guide

Complete installation guide for the Dojo Robot system and all its components.

## System Requirements

- Ubuntu 22.04 or later
- ROS 2 Jazzy
- Python 3.10+
- 8GB RAM minimum (16GB recommended)
- NVIDIA GPU (optional, for ML features)

## Base System Installation

### 1. Install ROS 2 Jazzy

```bash
# Add ROS 2 repository
sudo apt update && sudo apt install software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install curl -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

# Add repository to sources list
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Install ROS 2 Jazzy
sudo apt update
sudo apt install ros-jazzy-desktop-full
```

### 2. Install Dependencies

```bash
# Core dependencies
sudo apt install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-pip \
    git \
    wget

# Initialize rosdep
sudo rosdep init
rosdep update
```

### 3. Install Gazebo

```bash
sudo apt install -y \
    ros-jazzy-gazebo-ros-pkgs \
    ros-jazzy-gazebo-ros2-control
```

### 4. Install Navigation Stack

```bash
sudo apt install -y \
    ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup
```

## Vision and Perception Dependencies

```bash
# Install vision dependencies
bash install_vision_deps.sh

# Or manually:
sudo apt install -y \
    ros-jazzy-cv-bridge \
    ros-jazzy-image-transport \
    python3-opencv

pip3 install ultralytics torch torchvision
```

## Priority 2 Features Installation

### Reinforcement Learning Navigation

```bash
# Install RL dependencies
pip3 install stable-baselines3 gymnasium torch

# Build package
colcon build --packages-select robot_rl_navigation
source install/setup.bash
```

**Verification:**
```bash
python3 src/robot_rl_navigation/validate_rl_system.py
```

### Sensor Fusion

```bash
# Install dependencies
pip3 install numpy scipy

# Build package
colcon build --packages-select robot_sensor_fusion
source install/setup.bash
```

**Verification:**
```bash
python3 src/robot_sensor_fusion/test/test_sensor_fusion.py
```

### Multi-Robot Swarm

```bash
# Install DDS dependencies (already included in ROS 2)
# Build package
colcon build --packages-select robot_swarm
source install/setup.bash
```

### Predictive Maintenance

```bash
# Install ML dependencies
pip3 install scikit-learn tensorflow psutil

# Build package
colcon build --packages-select robot_maintenance
source install/setup.bash
```

## Priority 3 Features Installation

### LLM Interface

```bash
# Install LLM dependencies
pip3 install openai anthropic ollama-python transformers

# Build package
colcon build --packages-select robot_llm_interface
source install/setup.bash
```

### Quantum-Inspired Optimization

```bash
# Install optimization dependencies
pip3 install numpy scipy

# Build package
colcon build --packages-select robot_quantum
source install/setup.bash
```

### Neuromorphic Computing

```bash
# Install neuromorphic dependencies
pip3 install numpy

# Build package
colcon build --packages-select robot_neuromorphic
source install/setup.bash
```

### Digital Twin

```bash
# Install simulation dependencies
pip3 install pybullet numpy

# Build package
colcon build --packages-select robot_digital_twin
source install/setup.bash
```

## Build Complete System

```bash
# Clone repository
git clone <repository-url>
cd Dojo

# Install all dependencies
rosdep install --from-paths src --ignore-src -r -y

# Build all packages
colcon build

# Source workspace
source install/setup.bash
```

## Verification

### Test Basic System

```bash
# Launch simulation
ros2 launch robot_gazebo complete_robot_simulation.launch.py

# In another terminal, check topics
ros2 topic list
```

### Test Priority 1 Features

```bash
# Run integration tests
python3 test_priority1_integration.py
```

### Test Priority 2 Features

```bash
# Test RL Navigation
python3 src/robot_rl_navigation/comprehensive_rl_test.py

# Test Sensor Fusion
python3 src/robot_sensor_fusion/test/test_sensor_fusion.py

# Test Swarm
python3 src/robot_swarm/comprehensive_swarm_test.py

# Test Maintenance
python3 src/robot_maintenance/test/test_maintenance_system.py
```

## Troubleshooting

### Build Errors

**Issue:** Package not found
```bash
# Update rosdep
rosdep update
rosdep install --from-paths src --ignore-src -r -y
```

**Issue:** Python module not found
```bash
# Install missing module
pip3 install <module-name>
```

### Runtime Errors

**Issue:** Gazebo not starting
```bash
# Check Gazebo installation
gazebo --version

# Reinstall if needed
sudo apt install --reinstall ros-jazzy-gazebo-ros-pkgs
```

**Issue:** Topics not publishing
```bash
# Check if nodes are running
ros2 node list

# Check topic list
ros2 topic list
```

## Environment Setup

Add to your `~/.bashrc`:

```bash
# ROS 2 Jazzy
source /opt/ros/jazzy/setup.bash

# Dojo workspace
source ~/Dojo/install/setup.bash

# Gazebo models
export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:~/Dojo/src/robot_gazebo/models
```

## Next Steps

After installation:
1. Read [README.md](../README.md) for system overview
2. Follow [QUICKSTART.md](../QUICKSTART.md) for first launch
3. Refer to [docs/TESTING_GUIDE.md](TESTING_GUIDE.md) for testing procedures
4. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues

## Support

For installation issues:
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Review package-specific README files in `src/`
- Consult ROS 2 documentation: https://docs.ros.org/en/jazzy/
