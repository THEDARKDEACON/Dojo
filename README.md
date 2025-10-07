# Dojo Robot Project

A comprehensive ROS2 robot simulation system with SLAM, Navigation, and Vision Detection capabilities.

## Quick Start

### 1. Build the System
```bash
cd Dojo
./build_ros2.sh
```

### 2. Launch Complete Simulation
```bash
source install/setup.bash
ros2 launch complete_robot_simulation.launch.py
```

This launches:
- Gazebo simulation with robot
- SLAM for mapping
- Vision detection with object recognition
- RViz visualization
- Teleop keyboard control

## Launch Options

### Basic Simulation (Default)
```bash
ros2 launch complete_robot_simulation.launch.py
```
- ✅ Gazebo GUI
- ✅ RViz visualization  
- ✅ SLAM mapping
- ✅ Vision detection
- ✅ Teleop control
- ❌ Navigation (use SLAM first)

### Full Autonomous Navigation
```bash
ros2 launch complete_robot_simulation.launch.py navigation:=true
```
- Enables Navigation2 stack for autonomous navigation
- Requires existing map or concurrent SLAM

### Headless Mode (No GUI)
```bash
ros2 launch complete_robot_simulation.launch.py gui:=false rviz:=false
```
- Runs simulation without visual interfaces
- Good for automated testing

### Vision-Only Mode
```bash
ros2 launch complete_robot_simulation.launch.py slam:=false navigation:=false
```
- Focus on vision detection capabilities
- Minimal resource usage

## System Components

- **Gazebo Simulation**: Physics-based robot simulation
- **SLAM**: Real-time mapping using laser scanner
- **Navigation2**: Autonomous path planning and navigation
- **Vision Detection**: YOLO-based object detection with 80 classes
- **RViz**: Comprehensive visualization of all sensors and data
- **Teleop**: Keyboard control for manual robot operation

## Key Topics

- `/camera/image_raw` - Camera feed
- `/camera/detection_image` - Annotated images with bounding boxes
- `/detections` - Object detection results
- `/scan` - Laser scanner data
- `/map` - SLAM-generated map
- `/cmd_vel_teleop` - Teleop commands
- `/odom` - Robot odometry

## Available Launch Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `world` | `empty.world` | Gazebo world file |
| `gui` | `true` | Show Gazebo GUI |
| `rviz` | `true` | Show RViz visualization |
| `teleop` | `true` | Enable keyboard teleop |
| `slam` | `true` | Enable SLAM mapping |
| `navigation` | `false` | Enable autonomous navigation |
| `vision` | `true` | Enable vision detection |

## Troubleshooting

### Gazebo "Address already in use" Error
```bash
pkill -f gazebo
```

### Vision Detection Not Working
- Check if vision_msgs is installed: `apt list --installed | grep vision-msgs`
- Install if missing: `sudo apt install ros-humble-vision-msgs`

### Build Issues
- Clean build: `rm -rf build install log && ./build_ros2.sh`
- Check dependencies: `rosdep install --from-paths src --ignore-src -r -y`

## Project Structure

```
Dojo/
├── src/                          # ROS2 packages
│   ├── robot_description/        # Robot URDF and meshes
│   ├── robot_gazebo/            # Gazebo simulation
│   ├── robot_control/           # Control systems
│   ├── robot_navigation/        # Navigation stack
│   └── robot_perception/        # Vision and sensors
├── complete_robot_simulation.launch.py  # Main launch file
├── build_ros2.sh               # Build script
└── README.md                   # This file
```

## Documentation

- `NAVIGATION_GUIDE.md` - Navigation system usage
- `VISION_DETECTION_GUIDE.md` - Vision detection system
- `HOW_TO_USE_GAZEBO.md` - Gazebo simulation guide
- `TROUBLESHOOTING.md` - Common issues and solutions

## Requirements

- ROS2 Humble
- Gazebo 11
- Python 3.8+
- OpenCV
- YOLO (ultralytics package)

## License

This project is licensed under the Apache 2.0 License.