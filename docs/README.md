# 📖 Dojo Robot Documentation Hub

**Complete guide to building, operating, and extending your autonomous robot**

## 🎯 Quick Navigation

| **Getting Started** | **Advanced Usage** | **Development** |
|-------------------|------------------|----------------|
| [🚀 Quick Start](#quick-start) | [🗺️ Navigation](#navigation) | [🔧 Architecture](#architecture) |
| [⚙️ Installation](#installation) | [👁️ Computer Vision](#computer-vision) | [🧪 Testing](#testing) |
| [🎮 Basic Control](#basic-control) | [🤖 Autonomous Mode](#autonomous-mode) | [🛠️ Customization](#customization) |

---

## 🚀 Quick Start

### One-Command Launch
```bash
# Build and run everything
./build_ros2.sh && source install/setup.bash
ros2 launch complete_robot_simulation.launch.py
```

**What happens:**
1. **Gazebo** spawns your robot in a simulated world
2. **SLAM** starts building a map as you move
3. **Vision** detects objects in real-time
4. **RViz** shows all sensor data and maps
5. **Teleop** window opens for manual control

### First Steps
1. **Drive around** using `i/j/l/k` keys in teleop window
2. **Watch the map build** in RViz as you explore
3. **See object detection** with bounding boxes on camera feed
4. **Switch to autonomous** mode when ready

---

## ⚙️ Installation

### System Requirements
- **Ubuntu 24.04 LTS** (Noble Numbat)
- **ROS2 Jazzy Jalisco**
- **Gazebo Harmonic**
- **4GB+ RAM**, USB 3.0 ports

### Dependencies
```bash
# Core ROS2 packages
sudo apt update
sudo apt install ros-jazzy-desktop python3-colcon-common-extensions

# Robot-specific packages
sudo apt install ros-jazzy-navigation2 ros-jazzy-nav2-bringup
sudo apt install ros-jazzy-slam-toolbox ros-jazebo-ros-pkgs

# Vision dependencies (optional)
./install_vision_deps.sh
```

### Build Process
```bash
# Clone and build
cd Dojo
./build_ros2.sh

# Verify installation
source install/setup.bash
ros2 pkg list | grep robot_
```

---

## 🎮 Basic Control

### Launch Modes

| Mode | Command | Use Case |
|------|---------|----------|
| **Exploration** | `ros2 launch complete_robot_simulation.launch.py` | Build maps, learn environment |
| **Navigation** | `navigation:=true` | Autonomous goal-based movement |
| **Vision Focus** | `vision:=true slam:=false` | Object detection testing |
| **Development** | `gui:=false rviz:=false` | Headless testing |

### Manual Control
```bash
# Teleop keys (in teleop window)
i - forward          u - forward + left turn
j - turn left        o - forward + right turn  
l - turn right       m - backward + left turn
, - backward         . - backward + right turn
k - stop             space - emergency stop
```

### Direct Commands
```bash
# Move forward
ros2 topic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0.3}}'

# Turn in place
ros2 topic pub /cmd_vel geometry_msgs/Twist '{angular: {z: 0.5}}'

# Emergency stop
ros2 topic pub /cmd_vel_safety geometry_msgs/Twist '{linear: {x: 0.0}, angular: {z: 0.0}}'
```

---

## 🗺️ Navigation

### Two-Phase Process

#### Phase 1: Mapping
```bash
# Start with SLAM enabled
ros2 launch complete_robot_simulation.launch.py slam:=true navigation:=false

# Drive around to build map
# Use teleop (i/j/l/k) to explore all areas
# Watch map build in RViz
```

#### Phase 2: Navigation
```bash
# Switch to navigation mode
ros2 launch complete_robot_simulation.launch.py slam:=false navigation:=true

# Set goals in RViz:
# 1. Click "2D Goal Pose" tool
# 2. Click and drag on map
# 3. Watch robot navigate autonomously
```

### Navigation Features
- **Obstacle Avoidance** - Dynamic path replanning around obstacles
- **Recovery Behaviors** - Automatic unstuck maneuvers
- **Safety Systems** - Emergency stop and collision prevention
- **Multi-Goal** - Waypoint following and complex missions

### Monitoring
```bash
# Check navigation status
ros2 topic echo /navigate_to_pose/_action/status

# Monitor planned path
ros2 topic echo /plan

# View current position
ros2 topic echo /amcl_pose
```

---

## 👁️ Computer Vision

### Object Detection System
- **YOLO v8** - State-of-the-art object detection
- **80+ Classes** - People, vehicles, furniture, animals, etc.
- **Real-time** - 30fps detection with bounding boxes
- **Integration** - Seamless with navigation and mapping

### Setup and Usage
```bash
# Install vision dependencies
./install_vision_deps.sh

# Launch with vision enabled
ros2 launch complete_robot_simulation.launch.py vision:=true

# Monitor detections
ros2 topic echo /detections
ros2 topic hz /camera/detection_image
```

### Vision Topics
| Topic | Description | Format |
|-------|-------------|--------|
| `/camera/image_raw` | Raw camera feed | sensor_msgs/Image |
| `/camera/detection_image` | Annotated with boxes | sensor_msgs/Image |
| `/detections` | Detection results | vision_msgs/Detection2DArray |

### Troubleshooting Vision
```bash
# Check camera feed
ros2 topic hz /camera/image_raw

# Verify detection node
ros2 node list | grep vision

# Debug mode
ros2 launch robot_perception vision_detection.launch.py debug_mode:=true
```

---

## 🤖 Autonomous Mode

### Autonomous Exploration
```bash
# Enable autonomous exploration
ros2 launch complete_robot_simulation.launch.py autonomous_exploration:=true

# Robot will:
# - Explore unknown areas automatically
# - Build comprehensive maps
# - Avoid obstacles intelligently
# - Return to start when complete
```

### Behavior Trees
The robot uses Nav2 behavior trees for intelligent decision making:
- **Goal Planning** - Multi-step mission execution
- **Recovery Actions** - Automatic problem resolution
- **Safety Monitoring** - Continuous hazard assessment
- **Adaptive Behavior** - Learning from environment

### Autonomous Features
- **Frontier Exploration** - Systematic area coverage
- **Dynamic Replanning** - Adaptive to environment changes
- **Multi-Robot Ready** - Coordination capabilities
- **Mission Planning** - Complex task execution

---

## 🔧 Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Hardware      │    │   Processing    │    │   Intelligence  │
│                 │    │                 │    │                 │
│ • LiDAR Sensor  │───▶│ • SLAM Mapping  │───▶│ • Path Planning │
│ • Camera        │    │ • Vision AI     │    │ • Behavior Trees│
│ • Encoders      │    │ • Sensor Fusion │    │ • Safety System │
│ • IMU           │    │ • Localization  │    │ • Decision Logic│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                        ┌───────▼───────┐
                        │ Visualization │
                        │ • RViz        │
                        │ • Diagnostics │
                        │ • Monitoring  │
                        └───────────────┘
```

### ROS2 Packages
| Package | Purpose | Key Nodes |
|---------|---------|-----------|
| `robot_description` | Robot model and URDF | robot_state_publisher |
| `robot_gazebo` | Simulation environment | gazebo, spawn_entity |
| `robot_control` | Motion control | diff_drive_controller |
| `robot_navigation` | SLAM and navigation | slam_toolbox, nav2 |
| `robot_perception` | Computer vision | vision_detection_node |
| `robot_bringup` | System orchestration | launch files |

### Data Flow
1. **Sensors** → Raw data (LiDAR scans, camera images)
2. **Processing** → Filtered data (maps, detections, odometry)
3. **Planning** → Commands (velocity, navigation goals)
4. **Control** → Actuators (motor commands, steering)
5. **Feedback** → Sensors (closed-loop control)

---

## 🧪 Testing

### Automated Testing
```bash
# Full system test
./test_essential_functionality.sh

# Specific component tests
python3 test_autonomous_movement_immediate.py
python3 test_lidar_slam_complete.py
```

### Manual Testing
```bash
# Check all topics are publishing
ros2 topic list
ros2 topic hz /scan /camera/image_raw /odom

# Verify transforms
ros2 run tf2_tools view_frames

# Monitor system health
ros2 run rqt_graph rqt_graph
```

### Performance Monitoring
```bash
# System resources
htop
ros2 run rqt_top rqt_top

# Message rates
ros2 topic hz /scan
ros2 topic bw /camera/image_raw

# Latency testing
ros2 topic delay /cmd_vel
```

---

## 🛠️ Customization

### Configuration Management
All robot parameters are centralized in `config/robot_config.yaml`:

```yaml
robot:
  physical_parameters:
    wheel_base: 0.26          # meters
    wheel_radius: 0.033       # meters
    max_linear_velocity: 0.5  # m/s
    max_angular_velocity: 1.0 # rad/s
  
  safety:
    obstacle_stop_distance: 0.3  # meters
    command_timeout: 1.0         # seconds
```

### Adding New Sensors
1. **Update URDF** - Add sensor to robot description
2. **Create Driver** - ROS2 node for sensor communication
3. **Configure Launch** - Add to main launch file
4. **Update Config** - Add parameters to master config

### Custom Behaviors
```python
# Example: Custom navigation behavior
class CustomExplorer:
    def __init__(self):
        self.navigator = BasicNavigator()
        self.goal_publisher = self.create_publisher(PoseStamped, '/goal_pose')
    
    def explore_room(self, room_bounds):
        # Custom exploration logic
        pass
```

### World Creation
```bash
# Create custom Gazebo world
cp src/robot_gazebo/worlds/empty.world src/robot_gazebo/worlds/my_world.world

# Edit world file with Gazebo GUI
gazebo src/robot_gazebo/worlds/my_world.world

# Launch with custom world
ros2 launch complete_robot_simulation.launch.py world:=my_world.world
```

---

## 🚨 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| **Gazebo won't start** | `pkill -f gazebo` then relaunch |
| **No camera feed** | Check `/dev/video*` permissions |
| **SLAM not working** | Verify `/scan` topic has data |
| **Robot won't move** | Check `/cmd_vel` topic and safety systems |
| **Build failures** | `rm -rf build install log && ./build_ros2.sh` |

### Debug Commands
```bash
# Check system status
ros2 doctor
ros2 daemon status

# Monitor specific topics
ros2 topic echo /scan --once
ros2 topic echo /odom --once

# Node diagnostics
ros2 node info /slam_toolbox
ros2 param list /controller_server
```

### Log Analysis
```bash
# ROS2 logs
ros2 log view

# System logs
journalctl -f

# Gazebo logs
tail -f ~/.gazebo/server-*.log
```

---

## 📚 Additional Resources

### External Documentation
- **[ROS2 Jazzy Docs](https://docs.ros.org/en/jazzy/)** - Official ROS2 documentation
- **[Nav2 Documentation](https://navigation.ros.org/)** - Navigation stack guide
- **[Gazebo Tutorials](https://gazebosim.org/tutorials)** - Simulation environment
- **[SLAM Toolbox](https://github.com/SteveMacenski/slam_toolbox)** - SLAM implementation

### Community
- **[ROS Discourse](https://discourse.ros.org/)** - Community forum
- **[GitHub Issues](https://github.com/your-repo/issues)** - Bug reports and features
- **[ROS Answers](https://answers.ros.org/)** - Technical Q&A

### Advanced Topics
- **[Multi-Robot Systems](docs/CUTTING_EDGE_ROADMAP.md#swarm-robotics)** - Coordination and swarms
- **[Machine Learning Integration](docs/CUTTING_EDGE_ROADMAP.md#ai--machine-learning-enhancements)** - AI-powered behaviors
- **[Real Hardware Deployment](docs/CUTTING_EDGE_ROADMAP.md#hardware-integration)** - Physical robot setup

---

**🎯 Ready to build the future of robotics? Your autonomous robot is just getting started!** 🚀