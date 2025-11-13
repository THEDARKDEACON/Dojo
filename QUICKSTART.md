# Dojo Robot - Quick Start Guide

Get up and running with the Dojo Robot system in minutes.

## Prerequisites

- ROS 2 Jazzy installed
- Workspace built: `colcon build && source install/setup.bash`
- See [docs/INSTALLATION.md](docs/INSTALLATION.md) for full setup

## 🚀 Launch Options

### Option 1: Complete System (Recommended)

Launch all features with default world:

```bash
ros2 launch robot_gazebo complete_robot_simulation.launch.py
```

### Option 2: Specific World

```bash
# House environment
ros2 launch robot_gazebo complete_robot_simulation.launch.py world:=house

# Office environment
ros2 launch robot_gazebo complete_robot_simulation.launch.py world:=office_small

# Warehouse environment
ros2 launch robot_gazebo complete_robot_simulation.launch.py world:=warehouse
```

### Option 3: Custom Features

```bash
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    world:=house \
    semantic_slam:=true \
    pointcloud_viz:=true \
    performance_dashboard:=true \
    advanced_safety:=true \
    navigation:=true \
    rviz:=true
```

## 🎮 Control the Robot

### Semantic Navigation

```bash
# Navigate to an object
ros2 topic pub --once /semantic_command std_msgs/String "data: 'go to chair'"

# Find objects
ros2 topic pub --once /semantic_command std_msgs/String "data: 'find bottle'"

# List detected objects
ros2 topic pub --once /semantic_command std_msgs/String "data: 'list objects'"

# Stop navigation
ros2 topic pub --once /semantic_command std_msgs/String "data: 'stop'"
```

### Manual Control

```bash
# Publish velocity commands
ros2 topic pub /cmd_vel geometry_msgs/Twist \
    "{linear: {x: 0.5}, angular: {z: 0.2}}"
```

## 📊 Monitor System

### System Status

```bash
# Overall system health
ros2 topic echo /system_status

# Performance metrics
ros2 topic echo /performance_metrics

# Safety status
ros2 topic echo /safety_status
```

### Semantic Map

```bash
# View detected objects
ros2 topic echo /semantic_map

# View 3D point cloud
ros2 topic echo /pointcloud
```

## 🔧 Priority 2 Features

### Reinforcement Learning Navigation

```bash
# Train RL agent (2-4 hours)
ros2 run robot_rl_navigation train_agent

# Launch with RL navigation
ros2 launch robot_rl_navigation rl_navigation.launch.py
```

### Sensor Fusion

```bash
# Launch sensor fusion
ros2 launch robot_sensor_fusion sensor_fusion.launch.py

# Monitor fused pose
ros2 topic echo /fused_pose
```

### Multi-Robot Swarm

```bash
# Launch with 3 robots
ros2 launch robot_swarm swarm_system.launch.py num_robots:=3

# Monitor swarm status
ros2 topic echo /swarm/status
```

### Predictive Maintenance

```bash
# Launch maintenance system
ros2 launch robot_maintenance maintenance_system.launch.py

# Monitor health
ros2 topic echo /overall_health

# View alerts
ros2 topic echo /health_alerts
```

## 🚀 Priority 3 Features

### LLM Interface

```bash
# Launch with Ollama (local)
ros2 launch robot_llm_interface llm_interface.launch.py llm_provider:=ollama

# Send natural language command
ros2 topic pub /llm/command std_msgs/String \
    "data: 'Go to the kitchen and find a coffee mug'"

# Listen to explanations
ros2 topic echo /llm/explanation
```

### Quantum Planner

```bash
# Launch quantum planner
ros2 run robot_quantum quantum_planner

# Test QUBO solver
python3 src/robot_quantum/robot_quantum/qubo_solver.py
```

### Neuromorphic Computing

```bash
# Launch event-based vision
ros2 run robot_neuromorphic event_vision

# Launch SNN processor
ros2 run robot_neuromorphic snn_processor
```

### Digital Twin

```bash
# Launch digital twin
ros2 run robot_digital_twin digital_twin

# Enable physics simulation
ros2 run robot_digital_twin digital_twin \
    --ros-args -p enable_physics_sim:=true

# Offline mode for testing
ros2 run robot_digital_twin digital_twin \
    --ros-args -p offline_mode:=true
```

## 🧪 Run Tests

### Priority 1 Integration Tests

```bash
# Start system first
ros2 launch robot_gazebo complete_robot_simulation.launch.py

# Run tests in another terminal
python3 test_priority1_integration.py
```

### Priority 2 Tests

```bash
# RL Navigation
python3 src/robot_rl_navigation/comprehensive_rl_test.py

# Sensor Fusion
python3 src/robot_sensor_fusion/test/test_sensor_fusion.py

# Swarm
python3 src/robot_swarm/comprehensive_swarm_test.py

# Maintenance
python3 src/robot_maintenance/test/test_maintenance_system.py
```

## 📈 View Visualizations

When RViz launches, you'll see:

1. **3D Point Cloud** - Real-time environment mapping
2. **Semantic Map** - Detected objects with labels
3. **Performance Dashboard** - System metrics
4. **Safety Zones** - Threat visualization
5. **Robot Model** - Current state
6. **SLAM Map** - Occupancy grid

## 🔧 Troubleshooting

### System Not Starting

```bash
# Source ROS 2
source /opt/ros/jazzy/setup.bash

# Rebuild workspace
colcon build

# Source workspace
source install/setup.bash
```

### No Objects Detected

- Check camera: `ros2 topic echo /camera/image_raw`
- YOLO model downloads on first run (may take time)
- Verify lighting in simulation

### Performance Issues

```bash
# Check metrics
ros2 topic echo /performance_metrics

# Reduce features
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    pointcloud_viz:=false \
    performance_dashboard:=false
```

## 📚 Next Steps

1. **Explore Features**: Try different semantic commands
2. **Test Worlds**: Launch in different environments
3. **Run Tests**: Execute integration tests
4. **Read Docs**: Check [README.md](README.md) for details
5. **Advanced Features**: Try Priority 2 and 3 features

## 📖 Documentation

- [README.md](README.md) - System overview
- [docs/INSTALLATION.md](docs/INSTALLATION.md) - Installation guide
- [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) - Testing procedures
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Common issues
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guidelines

## 🆘 Getting Help

If you encounter issues:

1. Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
2. Review system logs: `ros2 log`
3. Run integration tests
4. Check package-specific README files in `src/`

---

**Happy Robot Building! 🤖**
