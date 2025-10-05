#!/bin/bash
# Comprehensive Dependency Installation Script for Dojo Robot
# This script installs all required system and ROS2 dependencies

set -e  # Exit on any error

echo "🚀 Installing Dojo Robot Dependencies"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Detect ROS2 distribution
if [ -z "$ROS_DISTRO" ]; then
    print_warning "ROS_DISTRO not set. Assuming humble..."
    export ROS_DISTRO=humble
fi

print_status "Installing dependencies for ROS2 $ROS_DISTRO"

# Update package lists
print_status "Updating package lists..."
sudo apt update

# Install basic system dependencies
print_status "Installing basic system dependencies..."
sudo apt install -y \
    curl \
    wget \
    git \
    build-essential \
    cmake \
    python3-pip \
    python3-dev \
    python3-setuptools \
    python3-wheel \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# Install ROS2 if not already installed
if ! command -v ros2 &> /dev/null; then
    print_status "ROS2 not found. Installing ROS2 $ROS_DISTRO..."
    
    # Add ROS2 repository
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
    
    sudo apt update
    sudo apt install -y ros-$ROS_DISTRO-desktop
    
    print_success "ROS2 $ROS_DISTRO installed"
else
    print_success "ROS2 already installed"
fi

# Install ROS2 development tools
print_status "Installing ROS2 development tools..."
sudo apt install -y \
    python3-colcon-common-extensions \
    python3-colcon-mixin \
    python3-rosdep \
    python3-vcstool \
    python3-argcomplete

# Install core ROS2 packages
print_status "Installing core ROS2 packages..."
sudo apt install -y \
    ros-$ROS_DISTRO-rclcpp \
    ros-$ROS_DISTRO-rclpy \
    ros-$ROS_DISTRO-std-msgs \
    ros-$ROS_DISTRO-geometry-msgs \
    ros-$ROS_DISTRO-sensor-msgs \
    ros-$ROS_DISTRO-nav-msgs \
    ros-$ROS_DISTRO-diagnostic-msgs \
    ros-$ROS_DISTRO-tf2-ros \
    ros-$ROS_DISTRO-tf2-geometry-msgs \
    ros-$ROS_DISTRO-rcl-interfaces

# Install diagnostic and monitoring packages
print_status "Installing diagnostic and monitoring packages..."
sudo apt install -y \
    ros-$ROS_DISTRO-diagnostic-updater \
    ros-$ROS_DISTRO-robot-state-publisher \
    ros-$ROS_DISTRO-joint-state-publisher

# Install hardware interface packages (optional, for advanced control)
print_status "Installing hardware interface packages..."
sudo apt install -y \
    ros-$ROS_DISTRO-controller-manager \
    ros-$ROS_DISTRO-controller-interface \
    ros-$ROS_DISTRO-hardware-interface \
    ros-$ROS_DISTRO-pluginlib \
    ros-$ROS_DISTRO-realtime-tools || print_warning "Some control packages not available, continuing..."

# Install camera and vision packages
print_status "Installing camera and vision packages..."
sudo apt install -y \
    ros-$ROS_DISTRO-cv-bridge \
    ros-$ROS_DISTRO-image-transport \
    ros-$ROS_DISTRO-camera-info-manager \
    ros-$ROS_DISTRO-image-geometry \
    ros-$ROS_DISTRO-vision-msgs || print_warning "Some vision packages not available, continuing..."

# Install LiDAR packages
print_status "Installing LiDAR packages..."
sudo apt install -y \
    ros-$ROS_DISTRO-laser-geometry \
    ros-$ROS_DISTRO-rplidar-ros || print_warning "Some LiDAR packages not available, continuing..."

# Install navigation packages (optional)
print_status "Installing navigation packages..."
sudo apt install -y \
    ros-$ROS_DISTRO-navigation2 \
    ros-$ROS_DISTRO-nav2-bringup || print_warning "Navigation packages not available, continuing..."

# Install simulation packages
print_status "Installing simulation packages..."
sudo apt install -y \
    ros-$ROS_DISTRO-gazebo-ros-pkgs \
    ros-$ROS_DISTRO-ros2-control \
    ros-$ROS_DISTRO-ros2-controllers || print_warning "Some simulation packages not available, continuing..."

# Install visualization tools
print_status "Installing visualization tools..."
sudo apt install -y \
    ros-$ROS_DISTRO-rviz2 \
    ros-$ROS_DISTRO-rqt \
    ros-$ROS_DISTRO-rqt-common-plugins || print_warning "Some visualization packages not available, continuing..."

# Install system libraries for hardware communication
print_status "Installing system libraries for hardware..."
sudo apt install -y \
    libserial-dev \
    libudev-dev \
    v4l-utils \
    uvcdynctrl \
    guvcview

# Install Python dependencies
print_status "Installing Python dependencies..."
pip3 install --user \
    pyserial \
    opencv-python \
    numpy \
    scipy \
    pyyaml \
    psutil \
    netifaces

# Install additional Python packages for robotics
print_status "Installing additional Python robotics packages..."
pip3 install --user \
    transforms3d \
    matplotlib \
    pillow \
    requests

# Set up udev rules for hardware access
print_status "Setting up udev rules for hardware access..."

# Arduino/Serial devices
sudo tee /etc/udev/rules.d/99-arduino.rules > /dev/null <<EOF
# Arduino devices
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", MODE="0666", GROUP="dialout"
EOF

# LiDAR devices
sudo tee /etc/udev/rules.d/99-lidar.rules > /dev/null <<EOF
# RPLiDAR devices
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{product}=="CP2102 USB to UART Bridge Controller", MODE="0666", GROUP="dialout"
EOF

# Camera devices
sudo tee /etc/udev/rules.d/99-camera.rules > /dev/null <<EOF
# USB cameras
SUBSYSTEM=="video4linux", GROUP="video", MODE="0664"
KERNEL=="video[0-9]*", GROUP="video", MODE="0664"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Add user to necessary groups
print_status "Adding user to hardware access groups..."
sudo usermod -a -G dialout $USER
sudo usermod -a -G video $USER
sudo usermod -a -G plugdev $USER

# Initialize rosdep if not already done
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    print_status "Initializing rosdep..."
    sudo rosdep init
fi

print_status "Updating rosdep..."
rosdep update

# Install workspace dependencies using rosdep
if [ -f "$(dirname "$0")/../src/robot_control/package.xml" ]; then
    print_status "Installing workspace dependencies with rosdep..."
    cd "$(dirname "$0")/.."
    rosdep install --from-paths src --ignore-src -r -y || print_warning "Some rosdep dependencies could not be installed"
fi

# Source ROS2 setup in bashrc if not already done
if ! grep -q "source /opt/ros/$ROS_DISTRO/setup.bash" ~/.bashrc; then
    print_status "Adding ROS2 setup to ~/.bashrc..."
    echo "# ROS2 setup" >> ~/.bashrc
    echo "source /opt/ros/$ROS_DISTRO/setup.bash" >> ~/.bashrc
    echo "export ROS_DOMAIN_ID=0" >> ~/.bashrc
fi

# Create workspace setup script
print_status "Creating workspace setup script..."
cat > "$(dirname "$0")/setup_workspace.sh" << 'EOF'
#!/bin/bash
# Workspace setup script
source /opt/ros/$ROS_DISTRO/setup.bash
if [ -f "install/setup.bash" ]; then
    source install/setup.bash
fi
export ROS_DOMAIN_ID=0
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
EOF

chmod +x "$(dirname "$0")/setup_workspace.sh"

print_success "Dependency installation completed!"
echo ""
echo "📋 Next Steps:"
echo "1. Logout and login again (or restart) to apply group changes"
echo "2. Source ROS2 setup: source /opt/ros/$ROS_DISTRO/setup.bash"
echo "3. Build the workspace: ./build_ros2.sh"
echo "4. Test the installation: python3 scripts/validate_system_structure.py"
echo ""
echo "⚠️  Important Notes:"
echo "- You may need to logout/login for group changes to take effect"
echo "- Some packages may not be available on all Ubuntu versions"
echo "- Check the build output for any remaining dependency issues"
echo ""
print_success "Installation script completed successfully!"