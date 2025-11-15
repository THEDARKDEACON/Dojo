# Dojo Robot Launch System Guide

## Quick Reference

### Simplest Way to Launch
```bash
./launch_dojo_robot.py
```

### Launch with Different World
```bash
./launch_dojo_robot.py house
./launch_dojo_robot.py empty
./launch_dojo_robot.py warehouse
```

### Full Control Launch
```bash
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    world:=mapping_world \
    gaussian_splatting:=true \
    semantic_slam:=true \
    advanced_safety:=true
```

## Launch System Architecture

### Main Entry Points

1. **`launch_dojo_robot.py`** - Simple Python launcher
   - Best for: Quick testing and demos
   - Features: Auto-sources ROS2, simple world selection
   - Usage: `./launch_dojo_robot.py [world_name]`

2. **`complete_robot_simulation.launch.py`** - Main orchestrator
   - Best for: Full control over features
   - Features: All launch arguments, modular design
   - Usage: `ros2 launch robot_gazebo complete_robot_simulation.launch.py [args]`

3. **`cutting_edge_features.launch.py`** - Feature aggregator
   - Best for: Launching only AI features without simulation
   - Features: All cutting-edge features in one launch
   - Usage: `ros2 launch robot_semantic_slam cutting_edge_features.launch.py`

## Available Launch Arguments

### World Selection
- `world` - Gazebo world name (default: `mapping_world`)
  - Options: `house`, `empty`, `minimal`, `warehouse`, `office_small`, etc.

### Core Features
- `slam` - Enable SLAM mapping (default: `true`)
- `navigation` - Enable Nav2 navigation (default: `false`)
- `gui` - Show Gazebo GUI (default: `true`)
- `rviz` - Launch RViz visualization (default: `true`)

### Cutting-Edge Features
- `semantic_slam` - YOLO object detection and semantic mapping (default: `true`)
- `gaussian_splatting` - 3D Gaussian Splatting reconstruction (default: `true`)
- `pointcloud_viz` - 3D point cloud visualization (default: `true`)
- `performance_dashboard` - Real-time system monitoring (default: `true`)
- `advanced_safety` - Behavior tree safety system (default: `true`)
- `semantic_interface` - Natural language commands (default: `true`)

### Optional Features
- `autonomous_exploration` - Frontier-based exploration (default: `false`)
- `vision` - Vision/perception systems (default: `true`)

## Common Launch Scenarios

### 1. Full System (All Features)
```bash
ros2 launch robot_gazebo complete_robot_simulation.launch.py
```
Launches everything with defaults.

### 2. Minimal System (Testing)
```bash
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    world:=empty \
    semantic_slam:=false \
    gaussian_splatting:=false \
    advanced_safety:=false \
    gui:=false
```
Minimal system for quick testing.

### 3. Reconstruction Focus
```bash
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    world:=house \
    gaussian_splatting:=true \
    pointcloud_viz:=true \
    semantic_slam:=false
```
Focus on 3D reconstruction without semantic features.

### 4. Navigation Focus
```bash
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    world:=warehouse \
    navigation:=true \
    autonomous_exploration:=true \
    semantic_slam:=true
```
Full navigation and exploration setup.

### 5. Headless (No GUI)
```bash
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    gui:=false \
    rviz:=false
```
For remote servers or CI/CD.

## Individual Feature Launches

### Launch Only Gaussian Splatting
```bash
ros2 launch robot_gaussian_splat gaussian_splatting.launch.py \
    camera_topic:=/camera/image_raw \
    pointcloud_topic:=/scan
```

### Launch Only Semantic SLAM
```bash
ros2 launch robot_semantic_slam semantic_slam.launch.py
```

### Launch Only Advanced Safety
```bash
ros2 launch robot_semantic_slam advanced_safety.launch.py
```

### Launch Only Performance Dashboard
```bash
ros2 launch robot_semantic_slam performance_dashboard.launch.py
```

## Startup Sequence

When launching the complete system, components start in this order:

1. **T+0s**: Gazebo simulation
2. **T+3s**: SLAM Toolbox
3. **T+5s**: Cutting-edge features (semantic SLAM, Gaussian Splatting, etc.)
4. **T+7s**: RViz visualization
5. **T+8s**: Nav2 navigation (if enabled)
6. **T+10s**: Autonomous exploration (if enabled)

This timing ensures stable initialization.

## Troubleshooting

### Issue: Package not found
```bash
# Solution: Build and source workspace
colcon build --symlink-install
source install/setup.bash
```

### Issue: Gazebo crashes on startup
```bash
# Solution: Use empty world for testing
ros2 launch robot_gazebo complete_robot_simulation.launch.py world:=empty
```

### Issue: Too many features, system slow
```bash
# Solution: Disable heavy features
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    gaussian_splatting:=false \
    semantic_slam:=false
```

### Issue: YOLO model not found
```bash
# Solution: Download model
python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

## Feature Dependencies

Some features depend on others:

- **Semantic Interface** requires **Semantic SLAM**
- **Advanced Safety** works best with **Semantic SLAM**
- **Autonomous Exploration** requires **Navigation**
- **Gaussian Splatting** requires camera and LiDAR topics

## Performance Tips

### For Best Performance
```bash
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    world:=empty \
    gui:=false
```

### For Best Visuals
```bash
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    world:=house \
    gaussian_splatting:=true \
    pointcloud_viz:=true \
    rviz:=true
```

### For Development
```bash
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    world:=minimal \
    performance_dashboard:=true
```

## Checking What's Running

```bash
# List all nodes
ros2 node list

# Check topics
ros2 topic list

# Monitor system
ros2 topic echo /performance_metrics
ros2 topic echo /system_status
```

## Stopping the System

- Press `Ctrl+C` in the terminal
- All nodes will shut down gracefully
- Gaussian Splatting models are auto-saved

## Next Steps

After launching:
1. Check RViz for visualization
2. Monitor performance dashboard
3. Send commands via `/text_command` topic
4. Save Gaussian Splat models via service calls

See README.md for detailed usage examples.
