#!/bin/bash
# Dependency Check Script for Dojo Robot
# This script checks if all required dependencies are installed

echo "🔍 Checking Dojo Robot Dependencies"
echo "==================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 is installed"
        return 0
    else
        echo -e "${RED}✗${NC} $1 is NOT installed"
        return 1
    fi
}

check_ros_package() {
    if ros2 pkg list | grep -q "^$1$" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} ROS2 package: $1"
        return 0
    else
        echo -e "${RED}✗${NC} ROS2 package: $1 (missing)"
        return 1
    fi
}

check_python_package() {
    if python3 -c "import $1" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Python package: $1"
        return 0
    else
        echo -e "${RED}✗${NC} Python package: $1 (missing)"
        return 1
    fi
}

echo -e "\n${BLUE}System Commands:${NC}"
check_command "ros2"
check_command "colcon"
check_command "python3"
check_command "pip3"
check_command "cmake"
check_command "git"

echo -e "\n${BLUE}Core ROS2 Packages:${NC}"
if command -v ros2 &> /dev/null; then
    check_ros_package "rclpy"
    check_ros_package "std_msgs"
    check_ros_package "geometry_msgs"
    check_ros_package "sensor_msgs"
    check_ros_package "diagnostic_msgs"
    check_ros_package "tf2_ros"
else
    echo -e "${RED}✗${NC} ROS2 not installed - cannot check ROS packages"
fi

echo -e "\n${BLUE}Python Packages:${NC}"
check_python_package "serial"
check_python_package "cv2"
check_python_package "numpy"
check_python_package "yaml"
check_python_package "psutil"

echo -e "\n${BLUE}Hardware Access:${NC}"
# Check user groups
if groups | grep -q "dialout"; then
    echo -e "${GREEN}✓${NC} User in dialout group (serial access)"
else
    echo -e "${RED}✗${NC} User NOT in dialout group (serial access)"
fi

if groups | grep -q "video"; then
    echo -e "${GREEN}✓${NC} User in video group (camera access)"
else
    echo -e "${RED}✗${NC} User NOT in video group (camera access)"
fi

echo -e "\n${BLUE}Hardware Devices:${NC}"
# Check for common hardware
if ls /dev/ttyACM* &>/dev/null || ls /dev/ttyUSB* &>/dev/null; then
    echo -e "${GREEN}✓${NC} Serial devices found: $(ls /dev/tty{ACM,USB}* 2>/dev/null | tr '\n' ' ')"
else
    echo -e "${YELLOW}!${NC} No serial devices found (Arduino/LiDAR may not be connected)"
fi

if ls /dev/video* &>/dev/null; then
    echo -e "${GREEN}✓${NC} Video devices found: $(ls /dev/video* 2>/dev/null | tr '\n' ' ')"
else
    echo -e "${YELLOW}!${NC} No video devices found (camera may not be connected)"
fi

echo -e "\n${BLUE}Build System:${NC}"
if [ -f "build_ros2.sh" ]; then
    echo -e "${GREEN}✓${NC} Build script found"
else
    echo -e "${RED}✗${NC} Build script not found"
fi

if [ -f "package.xml" ] || find src -name "package.xml" -type f | head -1 | grep -q .; then
    echo -e "${GREEN}✓${NC} ROS2 packages found"
else
    echo -e "${RED}✗${NC} No ROS2 packages found"
fi

echo -e "\n${BLUE}Configuration:${NC}"
if [ -f "config/robot_config.yaml" ]; then
    echo -e "${GREEN}✓${NC} Robot configuration found"
else
    echo -e "${RED}✗${NC} Robot configuration not found"
fi

echo -e "\n${BLUE}Environment:${NC}"
if [ -n "$ROS_DISTRO" ]; then
    echo -e "${GREEN}✓${NC} ROS_DISTRO set to: $ROS_DISTRO"
else
    echo -e "${RED}✗${NC} ROS_DISTRO not set"
fi

if [ -n "$AMENT_PREFIX_PATH" ]; then
    echo -e "${GREEN}✓${NC} ROS2 environment sourced"
else
    echo -e "${YELLOW}!${NC} ROS2 environment not sourced (run: source /opt/ros/humble/setup.bash)"
fi

echo -e "\n📋 Summary:"
echo "If you see missing dependencies, run: ./scripts/install_dependencies.sh"
echo "If you see missing groups, logout and login again after running the install script"
echo "If ROS2 environment is not sourced, run: source /opt/ros/humble/setup.bash"