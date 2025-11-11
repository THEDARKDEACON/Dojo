# 🚨 Dojo Robot Troubleshooting Guide

**Quick solutions for common issues and comprehensive debugging procedures**

## 🎯 Quick Fix Index

| Issue | Quick Solution | Details |
|-------|---------------|---------|
| **Gazebo won't start** | `pkill -f gazebo` | [Gazebo Issues](#gazebo-issues) |
| **Robot won't move** | Check `/cmd_vel` topic | [Movement Issues](#movement-issues) |
| **No camera feed** | Check `/dev/video*` permissions | [Vision Issues](#vision-issues) |
| **SLAM not working** | Verify `/scan` topic | [SLAM Issues](#slam-issues) |
| **Build failures** | Clean build: `rm -rf build install log` | [Build Issues](#build-issues) |
| **Navigation stuck** | Clear costmaps, check obstacles | [Navigation Issues](#navigation-issues) |

---

## 🔧 Common Issues

### Gazebo Issues

#### **Problem: "Address already in use" Error**
```bash
# Quick fix
pkill -f gazebo
pkill -f gzserver
pkill -f gzclient

# Verify processes are killed
ps aux | grep gazebo

# Relaunch
ros2 launch complete_robot_simulation.launch.py
```

#### **Problem: Gazebo crashes on startup**
```bash
# Check Gazebo installation
gz sim --version

# Test minimal Gazebo
gz sim --verbose

# Check graphics drivers
glxinfo | grep OpenGL

# If graphics issues, try software rendering
export LIBGL_ALWAYS_SOFTWARE=1
gz sim
```

#### **Problem: Segmentation fault with Ogre2 rendering (house.world crash)**
**Symptoms**: `Segmentation fault` in `gz::rendering::v8::Ogre2Node::AttachChild`

**Cause**: Compatibility issue between Ogre2 rendering engine and certain world files

**Solutions**:
```bash
# Solution 1: Use stable worlds
ros2 launch robot_gazebo gazebo.launch.py world:=empty.world
ros2 launch robot_gazebo gazebo.launch.py world:=mapping_world.world
ros2 launch robot_gazebo gazebo.launch.py world:=office_small.world

# Solution 2: Clear Gazebo cache
rm -rf ~/.gz/sim/

# Solution 3: Launch without GUI (less rendering load)
ros2 launch robot_gazebo gazebo.launch.py world:=house.world gui:=false

# Solution 4: Update Gazebo
sudo apt update
sudo apt upgrade gz-harmonic
```

**Stable Worlds** (tested and working):
- `empty.world` - Minimal environment
- `minimal.world` - Basic setup
- `mapping_world.world` - Navigation testing
- `office_small.world` - Indoor environment
- `warehouse.world` - Large space

**Problematic Worlds** (may crash with Ogre2):
- `house.world` - Complex models
- Some worlds with external model references

#### **Problem: Robot model crashes Gazebo (Ogre2 sensor attachment failure)**
**Symptoms**: Crash after `Created entity [46] named [zeta]` with `Ogre2Node::AttachChild` error

**Cause**: Robot's sensor plugins (camera/lidar) incompatible with Ogre2 rendering

**Solutions**:
```bash
# Solution 1: Use fixed launch file (rebuild first)
colcon build --packages-select robot_gazebo --symlink-install
source install/setup.bash

# Solution 2: Test Gazebo without robot
gz sim empty.sdf

# Solution 3: Clear all Gazebo cache
rm -rf ~/.gz/

# Solution 4: Check Gazebo version
gz sim --version
# Should be: Gazebo Sim, version 8.x.x

# Solution 5: Reinstall Gazebo Harmonic
sudo apt update
sudo apt install --reinstall ros-jazzy-gz-sim-vendor
```

#### **Problem: gzclient command not found**
**Cause**: Using Gazebo Classic commands with Gazebo Harmonic

**Solution**: Launch file has been fixed to use `gz sim` instead of `gzclient`

#### **Problem: Robot not spawning in Gazebo**
```bash
# Check entity spawning
ros2 topic echo /gazebo/entity_spawn

# Verify robot description
ros2 run robot_state_publisher robot_state_publisher --ros-args -p robot_description:="$(xacro src/robot_description/urdf/robot.urdf.xacro)"

# Check for URDF errors
check_urdf src/robot_description/urdf/robot.urdf
```

### Movement Issues

#### **Problem: Robot doesn't respond to commands**
```bash
# Check command topics
ros2 topic list | grep cmd_vel
ros2 topic echo /cmd_vel

# Test direct movement
ros2 topic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0.2}, angular: {z: 0.0}}' --once

# Check twist mux status
ros2 topic echo /cmd_vel_out
ros2 param list | grep twist_mux
```

#### **Problem: Robot moves erratically**
```bash
# Check controller status
ros2 control list_controllers

# Monitor joint states
ros2 topic echo /joint_states

# Check differential drive parameters
ros2 param get /diff_drive_controller wheel_separation
ros2 param get /diff_drive_controller wheel_radius
```

#### **Problem: Emergency stop activated**
```bash
# Check safety status
ros2 topic echo /safety_status

# Clear emergency stop
ros2 service call /clear_emergency_stop std_srvs/Trigger

# Check for safety violations
ros2 topic echo /safety_violations
```

### Vision Issues

#### **Problem: No camera feed**
```bash
# Check camera devices
ls -la /dev/video*

# Test camera directly
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --list-formats-ext

# Check camera permissions
groups $USER | grep video
sudo usermod -a -G video $USER  # Logout/login required

# Test ROS camera
ros2 run usb_cam usb_cam_node_exe --ros-args -p video_device:=/dev/video0
```

#### **Problem: Vision detection not working**
```bash
# Install vision dependencies
./install_vision_deps.sh

# Check vision node status
ros2 node list | grep vision
ros2 node info /vision_detection_node

# Test detection manually
ros2 topic echo /detections
ros2 topic hz /camera/detection_image

# Debug mode
ros2 launch robot_perception vision_detection.launch.py debug_mode:=true
```

#### **Problem: Poor detection accuracy**
```bash
# Adjust confidence threshold
ros2 param set /vision_detection_node confidence_threshold 0.3

# Check lighting conditions
ros2 topic echo /camera/image_raw --field header

# Verify YOLO model
python3 -c "from ultralytics import YOLO; model = YOLO('yolov8n.pt'); print('Model loaded successfully')"
```

### SLAM Issues

#### **Problem: SLAM not building map**
```bash
# Check LiDAR data
ros2 topic echo /scan --once
ros2 topic hz /scan

# Verify SLAM node
ros2 node list | grep slam
ros2 node info /slam_toolbox

# Check transforms
ros2 run tf2_tools view_frames
ros2 run tf2_ros tf2_echo base_link laser
```

#### **Problem: Map quality is poor**
```bash
# Check SLAM parameters
ros2 param list | grep slam_toolbox

# Adjust scan matching parameters
ros2 param set /slam_toolbox minimum_travel_distance 0.1
ros2 param set /slam_toolbox minimum_travel_heading 0.1

# Check for sensor noise
ros2 topic echo /scan --field ranges | head -20
```

#### **Problem: Localization drift**
```bash
# Check odometry
ros2 topic echo /odom
ros2 topic hz /odom

# Verify wheel parameters
ros2 param get /diff_drive_controller wheel_separation
ros2 param get /diff_drive_controller wheel_radius

# Reset SLAM
ros2 service call /slam_toolbox/clear_changes slam_toolbox/srv/Clear
```

### Navigation Issues

#### **Problem: Robot won't navigate to goal**
```bash
# Check navigation status
ros2 topic echo /navigate_to_pose/_action/status

# Verify map and localization
ros2 topic echo /map --once
ros2 topic echo /amcl_pose

# Check costmaps
ros2 topic echo /local_costmap/costmap
ros2 topic echo /global_costmap/costmap

# Clear costmaps
ros2 service call /local_costmap/clear_entirely_local_costmap nav2_msgs/srv/ClearEntireCostmap
ros2 service call /global_costmap/clear_entirely_global_costmap nav2_msgs/srv/ClearEntireCostmap
```

#### **Problem: Path planning fails**
```bash
# Check planner status
ros2 node info /planner_server

# Test path planning directly
ros2 action send_goal /compute_path_to_pose nav2_msgs/action/ComputePathToPose '{
  goal: {
    pose: {
      position: {x: 2.0, y: 1.0, z: 0.0},
      orientation: {w: 1.0}
    }
  }
}'

# Check planner parameters
ros2 param list | grep planner_server
```

#### **Problem: Robot gets stuck**
```bash
# Check recovery behaviors
ros2 node info /behavior_server

# Trigger manual recovery
ros2 action send_goal /backup nav2_msgs/action/BackUp '{target: {x: -0.5}}'

# Check obstacle detection
ros2 topic echo /scan | grep -E "ranges.*0\.[0-5]"
```

### Build Issues

#### **Problem: Colcon build fails**
```bash
# Clean build environment
rm -rf build/ install/ log/

# Check dependencies
rosdep update
rosdep install --from-paths src --ignore-src -r -y

# Build with verbose output
colcon build --event-handlers console_direct+

# Build specific package
colcon build --packages-select robot_control
```

#### **Problem: Missing dependencies**
```bash
# Check ROS2 installation
ros2 doctor

# Install missing packages
sudo apt update
sudo apt install ros-jazzy-desktop
sudo apt install ros-jazzy-navigation2 ros-jazzy-nav2-bringup
sudo apt install ros-jazzy-slam-toolbox

# Check Python dependencies
pip install -r requirements.txt
```

#### **Problem: Package not found**
```bash
# Source workspace
source install/setup.bash

# Check package installation
ros2 pkg list | grep robot_

# Verify package.xml
find src/ -name "package.xml" -exec xmllint {} \;

# Check CMakeLists.txt
find src/ -name "CMakeLists.txt" -exec grep -l "find_package" {} \;
```

---

## 🔍 Advanced Debugging

### System Diagnostics

#### **Complete System Check**
```bash
#!/bin/bash
# comprehensive_check.sh

echo "=== ROS2 System Check ==="
ros2 doctor

echo "=== Node Status ==="
ros2 node list

echo "=== Topic Status ==="
ros2 topic list
ros2 topic hz /scan /odom /camera/image_raw --window 10

echo "=== Transform Tree ==="
ros2 run tf2_tools view_frames

echo "=== Parameter Check ==="
ros2 param list | head -20

echo "=== Service Status ==="
ros2 service list | head -10

echo "=== Action Status ==="
ros2 action list

echo "=== Hardware Check ==="
ls -la /dev/video* /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || echo "No hardware devices found"

echo "=== System Resources ==="
free -h
df -h
```

#### **Performance Monitoring**
```bash
# Monitor system performance
htop

# Monitor ROS2 performance
ros2 run rqt_top rqt_top

# Check message rates
ros2 topic hz /scan /odom /camera/image_raw

# Monitor bandwidth
ros2 topic bw /camera/image_raw
ros2 topic bw /scan

# Check latency
ros2 topic delay /cmd_vel
```

#### **Network Diagnostics**
```bash
# Check ROS2 network configuration
ros2 daemon status

# Test local communication
ros2 topic pub /test_topic std_msgs/String "data: 'test'" &
ros2 topic echo /test_topic --once
pkill -f "ros2 topic pub"

# Check DDS configuration
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
ros2 doctor --report
```

### Log Analysis

#### **ROS2 Logs**
```bash
# View recent logs
ros2 log view

# Filter logs by severity
ros2 log view --severity WARN

# Node-specific logs
ros2 log view --node /slam_toolbox

# Save logs to file
ros2 log view > robot_logs_$(date +%Y%m%d_%H%M%S).log
```

#### **System Logs**
```bash
# Check system logs
journalctl -f

# ROS2 service logs
journalctl -u ros2-daemon

# Gazebo logs
tail -f ~/.gazebo/server-*.log
tail -f ~/.gazebo/client-*.log
```

#### **Custom Logging**
```python
# Add debug logging to nodes
import rclpy
from rclpy.logging import get_logger

logger = get_logger('debug_node')
logger.set_level(rclpy.logging.LoggingSeverity.DEBUG)

# Log with context
logger.info(f"Robot position: {position}, Goal: {goal}")
logger.warn(f"Obstacle detected at distance: {distance}")
logger.error(f"Navigation failed: {error_message}")
```

---

## 🛠️ Configuration Debugging

### Parameter Validation
```bash
# Check all parameters
ros2 param list

# Validate specific parameters
ros2 param get /diff_drive_controller wheel_separation
ros2 param get /slam_toolbox resolution

# Set parameters for debugging
ros2 param set /slam_toolbox minimum_travel_distance 0.05
ros2 param set /controller_server controller_frequency 10.0
```

### Configuration Files
```bash
# Validate YAML files
python3 -c "import yaml; yaml.safe_load(open('config/robot_config.yaml'))"

# Check URDF syntax
check_urdf src/robot_description/urdf/robot.urdf

# Validate launch files
ros2 launch --show-args complete_robot_simulation.launch.py
```

---

## 🚨 Emergency Procedures

### **Complete System Recovery**
```bash
#!/bin/bash
# emergency_recovery.sh

echo "=== Emergency System Recovery ==="

# 1. Stop all ROS2 processes
echo "Stopping ROS2 processes..."
pkill -f ros2
pkill -f gazebo
sleep 2

# 2. Check hardware connections
echo "Checking hardware..."
ls -la /dev/video* /dev/ttyACM* /dev/ttyUSB* 2>/dev/null

# 3. Clean workspace
echo "Cleaning workspace..."
rm -rf build/ install/ log/

# 4. Rebuild system
echo "Rebuilding system..."
./build_ros2.sh

# 5. Restart system
echo "Restarting system..."
source install/setup.bash
ros2 launch complete_robot_simulation.launch.py &

# 6. Wait and verify
sleep 10
echo "Verifying system..."
ros2 node list
ros2 topic list | head -10

echo "=== Recovery Complete ==="
```

### **Hardware Reset**
```bash
# Reset USB devices
sudo rmmod uvcvideo && sudo modprobe uvcvideo
sudo rmmod cdc_acm && sudo modprobe cdc_acm

# Reset permissions
sudo chmod 666 /dev/video*
sudo chmod 666 /dev/ttyACM*
sudo chmod 666 /dev/ttyUSB*

# Restart udev
sudo systemctl restart udev
```

---

## 📞 Getting Help

### **Community Resources**
- **[ROS Discourse](https://discourse.ros.org/)** - Community forum
- **[GitHub Issues](https://github.com/your-repo/issues)** - Bug reports
- **[ROS Answers](https://answers.ros.org/)** - Technical Q&A
- **[Stack Overflow](https://stackoverflow.com/questions/tagged/ros2)** - Programming help

### **Documentation**
- **[ROS2 Documentation](https://docs.ros.org/en/jazzy/)** - Official docs
- **[Nav2 Documentation](https://navigation.ros.org/)** - Navigation stack
- **[Gazebo Tutorials](https://gazebosim.org/tutorials)** - Simulation help

### **Reporting Issues**
When reporting issues, include:
1. **System info**: `ros2 doctor --report`
2. **Error logs**: `ros2 log view > error_log.txt`
3. **Steps to reproduce**: Exact commands used
4. **Expected vs actual behavior**: What should happen vs what happens
5. **System configuration**: Hardware, OS version, ROS2 distro

---

**🎯 Remember: Most issues have simple solutions. Start with the quick fixes, then dive deeper if needed!** 🚀