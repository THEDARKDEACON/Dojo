# 🤖 Dojo Robot - Autonomous Navigation & Mapping System

**Professional autonomous mobile robot system with SLAM, Nav2, and 3D reconstruction capabilities**

[![ROS 2 Jazzy](https://img.shields.io/badge/ROS_2-Jazzy-blue)](https://docs.ros.org/en/jazzy/)
[![Gazebo Harmonic](https://img.shields.io/badge/Gazebo-Harmonic-orange)](https://gazebosim.org/)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-green)](https://python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 Overview

Dojo Robot is a complete autonomous navigation and mapping system built for the **Husarion ROSbot XL** platform. It integrates industry-standard ROS 2 packages with custom algorithms to deliver robust autonomous exploration, semantic mapping, and 3D scene reconstruction capabilities.

### Core Features

🗺️ **Autonomous Mapping**
- SLAM-based environment mapping using `slam_toolbox`
- Real-time occupancy grid generation
- Persistent map storage and recall

🎯 **Intelligent Navigation**
- Nav2 stack integration for path planning
- Dynamic obstacle avoidance
- Frontier-based autonomous exploration
- Semantic object navigation

✨ **3D Reconstruction**
- Gaussian Splatting pipeline for photorealistic 3D scenes
- Optimized camera control (exposure locking, slow movement)
- Survey planning with "crab walk" trajectories
- Integrated data collection workflow

🛡️ **Semantic Understanding**
- YOLO-based object detection
- Semantic map management
- Natural language command interface
- Object-centric navigation

📊 **Professional Features**
- Real-time performance monitoring
- Advanced safety systems
- Modular launch system
- Comprehensive configuration options

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Dojo Robot System                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Hardware   │  │  Perception  │  │  Navigation  │ │
│  │              │  │              │  │              │ │
│  │ • LiDAR      │  │ • SLAM       │  │ • Nav2       │ │
│  │ • Cameras    │  │ • YOLO       │  │ • Costmaps   │ │
│  │ • IMU        │  │ • Semantic   │  │ • Planners   │ │
│  │ • Encoders   │  │   Mapping    │  │ • Controllers│ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Autonomy    │  │     3D       │  │  Interface   │ │
│  │              │  │              │  │              │ │
│  │ • Exploration│  │ • Gaussian   │  │ • Dashboard  │ │
│  │ • Survey     │  │   Splat      │  │ • Commands   │ │
│  │ • Object Nav │  │ • Pipeline   │  │ • Monitoring │ │
│  │ • Safety     │  │   Manager    │  │ • Logging    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **OS**: Ubuntu 24.04 (Noble)
- **ROS 2**: Jazzy Jalisco
- **Gazebo**: Harmonic (8.x)
- **Python**: 3.12+
- **Hardware**: Husarion ROSbot XL (or simulation)

### Installation

```bash
# Clone the repository
cd ~/Downloads
git clone <repository-url> Dojo
cd Dojo

# Install dependencies
./scripts/install_dependencies.sh

# Build the workspace
colcon build --symlink-install

# Source the workspace
source install/setup.bash
```

### Launch Options

#### 1. Full System (Simulation)
```bash
ros2 launch launch_dojo_rosbot_xl.py \
    world:=office \
    slam:=true \
    navigation:=true \
    autonomous_exploration:=true \
    gui:=true \
    rviz:=true
```

#### 2. Hardware Deployment
```bash
# On the robot
ros2 launch launch_dojo_rosbot_xl_hardware.py \
    slam:=true \
    navigation:=true \
    autonomous_exploration:=true
```

#### 3. Gaussian Splat Data Collection
```bash
# Start the robot system
ros2 launch launch_dojo_rosbot_xl.py \
    gaussian_splatting:=true

# On laptop, run the pipeline manager
python3 scripts/splat_pipeline_manager.py
```

---

## 📦 Package Structure

```
Dojo/
├── src/
│   ├── rosbot_xl_*/              # ROSbot XL vendor packages
│   ├── robot_navigation/         # Nav2 configs & exploration
│   ├── robot_semantic_slam/      # Semantic SLAM & YOLO
│   ├── robot_gaussian_splat/     # 3D reconstruction
│   ├── robot_gazebo/             # Simulation worlds
│   ├── dojo_navigation/          # Survey planner & algorithms
│   └── dojo_semantic/            # Semantic navigator
├── launch_dojo_rosbot_xl.py      # Main launch file
├── semantic_map.json             # Object database
├── scripts/                      # Utility scripts
├── config/                       # Configuration files
└── DOCS.md                       # Detailed documentation
```

---

## 🎮 Usage Examples

### Autonomous Exploration

```bash
# Launch with autonomous exploration enabled
ros2 launch launch_dojo_rosbot_xl.py \
    world:=office \
    slam:=true \
    navigation:=true \
    autonomous_exploration:=true
```

The robot will:
1. Map the environment using SLAM
2. Detect frontiers (unexplored areas)
3. Navigate to frontiers autonomously
4. Build a complete map of the space

### Semantic Object Navigation

```bash
# Navigate to a specific object
ros2 topic pub /semantic_command std_msgs/msg/String \
    "data: 'go to chair_1'" --once
```

### Survey Scan (for Gaussian Splats)

```bash
# Define room corners and execute survey
ros2 run dojo_navigation survey_planner \
    --room-corners "0,0,5,5"
```

---

## ⚙️ Configuration

### Key Parameters

**Navigation** (`config/nav2_params.yaml`):
- `controller_frequency`: 20 Hz
- `max_vel_x`: 0.5 m/s
- `footprint`: Robot dimensions

**SLAM** (`config/slam_config.yaml`):
- `map_update_interval`: 5.0 s
- `resolution`: 0.05 m
- `scan_topic`: `/scan`

**Exploration** (node parameters):
- `frontier_distance_threshold`: 0.5 m
- `exploration_radius`: 10.0 m
- `goal_tolerance`: 0.3 m

**Gaussian Splat** (survey parameters):
- `max_speed`: 0.2 m/s (prevents blur)
- `crab_angle`: 45° (maximizes parallax)
- `step_size`: 0.5 m (path density)

See [`DOCS.md`](DOCS.md) for complete configuration guide.

---

## 🛠️ Development

### Adding New Features

1. **Create Package**:
   ```bash
   cd src/
   ros2 pkg create --build-type ament_python my_package \
       --dependencies rclpy
   ```

2. **Implement Node**:
   ```python
   # my_package/my_package/my_node.py
   import rclpy
   from rclpy.node import Node
   
   class MyNode(Node):
       def __init__(self):
           super().__init__('my_node')
           # Your code here
   ```

3. **Build & Test**:
   ```bash
   colcon build --packages-select my_package
   source install/setup.bash
   ros2 run my_package my_node
   ```

### Testing

```bash
# Run all tests
colcon test

# Test specific package
colcon test --packages-select robot_navigation

# View test results
colcon test-result --verbose
```

---

## 📚 Documentation

- **[DOCS.md](DOCS.md)** - Complete system documentation
- **[Architecture](docs/ARCHITECTURE.md)** - System design and data flow
- **[API Reference](docs/API.md)** - ROS 2 topics, services, and actions
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Hardware deployment procedures
- **[Parameter Guide](docs/PARAMETER_GUIDE.md)** - Configuration tuning

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Husarion** - ROSbot XL platform and Gazebo worlds
- **ROS 2 Community** - Navigation and SLAM tools
- **Open Robotics** - Gazebo simulator
- **YOLO** - Object detection models

---

## 📧 Contact

For questions, issues, or collaboration:
- Create an issue on GitHub
- Email: [your-email@example.com]

---

**Built with ❤️ using ROS 2 and modern robotics**
