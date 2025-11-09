# 🚀 Dojo Robot - Quick Start Guide

Get up and running in 5 minutes!

---

## 1. Build & Launch (30 seconds)

```bash
# Build the project
./build_ros2.sh

# Source the workspace
source install/setup.bash

# Launch complete system
ros2 launch complete_robot_simulation.launch.py
```

**What you get**: Gazebo simulation, SLAM, autonomous exploration, RViz visualization

---

## 2. Add Semantic Features (Optional)

```bash
# In a new terminal
source install/setup.bash
ros2 launch robot_semantic_slam cutting_edge_features.launch.py
```

**What you get**: YOLO object detection, semantic SLAM, natural language commands, advanced safety

---

## 3. Try Natural Language Commands

```bash
# List detected objects
ros2 topic pub /text_command std_msgs/msg/String "data: 'list objects'" --once

# Navigate to an object
ros2 topic pub /text_command std_msgs/msg/String "data: 'go to chair'" --once

# Multi-step navigation
ros2 topic pub /text_command std_msgs/msg/String "data: 'go to chair then table'" --once

# Find objects
ros2 topic pub /text_command std_msgs/msg/String "data: 'find bottle'" --once

# Cancel navigation
ros2 topic pub /text_command std_msgs/msg/String "data: 'cancel navigation'" --once
```

---

## 4. Monitor the System

```bash
# Watch semantic map
ros2 topic echo /semantic_map

# Watch navigation status
ros2 topic echo /navigation_status

# Watch navigation progress
ros2 topic echo /navigation_progress

# Watch annotated camera feed
ros2 run rqt_image_view rqt_image_view /semantic_image
```

---

## 5. Test the System

```bash
# Run comprehensive validation
python3 test_semantic_slam_validation.py

# Run unit tests
cd src/robot_semantic_slam
python3 -m pytest test/ -v
```

---

## Common Launch Configurations

### Basic Simulation
```bash
ros2 launch complete_robot_simulation.launch.py
```

### With Navigation
```bash
ros2 launch complete_robot_simulation.launch.py navigation:=true
```

### Different World
```bash
ros2 launch complete_robot_simulation.launch.py world:=house.world
```

### Headless Mode
```bash
ros2 launch complete_robot_simulation.launch.py gui:=false rviz:=false
```

---

## Troubleshooting

### YOLO Model Not Found
```bash
python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### Nav2 Not Available
```bash
ros2 launch complete_robot_simulation.launch.py navigation:=true
```

### Check System Status
```bash
ros2 node list
ros2 topic list
```

---

## Next Steps

- Read the full [README.md](README.md)
- Check [docs/SEMANTIC_SLAM_QUICK_START.md](docs/SEMANTIC_SLAM_QUICK_START.md)
- Explore [docs/](docs/) for detailed documentation

---

**Need Help?** Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
