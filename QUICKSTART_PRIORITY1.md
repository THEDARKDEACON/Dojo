# Quick Start Guide - Priority 1 Features

## 🚀 Launch the Complete System

### Option 1: Full System (Recommended)

Launch all Priority 1 features with default world:

```bash
ros2 launch robot_gazebo complete_robot_simulation.launch.py
```

### Option 2: Specific World

Launch with a specific environment:

```bash
# House environment
ros2 launch robot_gazebo complete_robot_simulation.launch.py world:=house

# Office environment
ros2 launch robot_gazebo complete_robot_simulation.launch.py world:=office_small

# Warehouse environment
ros2 launch robot_gazebo complete_robot_simulation.launch.py world:=warehouse
```

### Option 3: Custom Configuration

Enable/disable specific features:

```bash
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    world:=house \
    semantic_slam:=true \
    pointcloud_viz:=true \
    performance_dashboard:=true \
    advanced_safety:=true \
    semantic_interface:=true \
    navigation:=true \
    rviz:=true
```

## 📊 Monitor System Status

### Check System Health

```bash
# Watch system status
ros2 topic echo /system_status

# Check performance metrics
ros2 topic echo /performance_metrics

# Monitor safety status
ros2 topic echo /safety_status
```

### View Semantic Map

```bash
# See detected objects
ros2 topic echo /semantic_map

# List all objects
ros2 topic pub --once /semantic_command std_msgs/String "data: 'list objects'"
```

## 🎮 Control the Robot

### Semantic Navigation Commands

```bash
# Navigate to an object
ros2 topic pub --once /semantic_command std_msgs/String "data: 'go to chair'"

# Find objects
ros2 topic pub --once /semantic_command std_msgs/String "data: 'find bottle'"

# Multi-step navigation
ros2 topic pub --once /semantic_command std_msgs/String "data: 'go to chair then table then door'"

# Find nearby objects
ros2 topic pub --once /semantic_command std_msgs/String "data: 'find nearby'"

# Stop navigation
ros2 topic pub --once /semantic_command std_msgs/String "data: 'stop'"
```

### Manual Control

```bash
# Teleop keyboard (if enabled)
# Use arrow keys to control the robot
# Space to stop
```

## 🧪 Run Integration Tests

### Automated Tests

```bash
# Start the system first
ros2 launch robot_gazebo complete_robot_simulation.launch.py

# In another terminal, run tests
python3 test_priority1_integration.py
```

### Expected Output

```
🧪 Priority 1 Integration Test initialized
⏳ Waiting 5 seconds for system initialization...

================================================================================
🚀 STARTING PRIORITY 1 INTEGRATION TESTS
================================================================================

📋 TEST 1: Semantic SLAM Integration
------------------------------------------------------------
✅ Semantic map is being published
✅ Object data structure is correct

📋 TEST 2: 3D Point Cloud Visualization
------------------------------------------------------------
✅ Point cloud is being published

📋 TEST 3: Performance Dashboard
------------------------------------------------------------
✅ Performance dashboard is active
✅ All required metrics are present

📋 TEST 4: Advanced Safety System
------------------------------------------------------------
✅ Safety system is active

📋 TEST 5: Feature Combination
------------------------------------------------------------
✅ All Priority 1 features are active simultaneously
✅ Command interface is functional

================================================================================
📊 TEST RESULTS SUMMARY
================================================================================

Total Tests: 9
Passed: 9 ✅
Failed: 0 ❌
Pass Rate: 100.0%

🎉 INTEGRATION TEST PASSED! Priority 1 features are working well.
```

## 📈 View Visualizations

### RViz Displays

When RViz launches, you should see:

1. **3D Point Cloud** - Real-time and accumulated views
2. **Semantic Map** - Detected objects with bounding boxes
3. **Performance Dashboard** - System metrics panel
4. **Safety Zones** - Threat visualization
5. **Robot Model** - Current robot state
6. **SLAM Map** - Occupancy grid

### Performance Dashboard

The dashboard shows:
- CPU Usage (%)
- Memory Usage (MB)
- Detection Rate (objects/sec)
- Navigation Efficiency (%)
- Safety Level
- Active Threats

## 🔧 Troubleshooting

### System Not Starting

```bash
# Check if ROS 2 is sourced
source /opt/ros/jazzy/setup.bash

# Build the workspace
colcon build --symlink-install

# Source the workspace
source install/setup.bash
```

### No Objects Detected

- Ensure camera is working: `ros2 topic echo /camera/image_raw`
- Check YOLO model is loaded (first run downloads model)
- Verify lighting in simulation world

### Point Cloud Not Visible

- Check topic: `ros2 topic echo /pointcloud`
- Verify RViz config loaded correctly
- Ensure LiDAR is publishing: `ros2 topic echo /scan`

### Performance Issues

```bash
# Check resource usage
ros2 topic echo /performance_metrics

# Reduce features if needed
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    pointcloud_viz:=false \
    performance_dashboard:=false
```

### Navigation Not Working

- Ensure Nav2 is enabled: `navigation:=true`
- Check if goal is reachable
- Verify semantic map has objects: `ros2 topic echo /semantic_map`

## 📚 Additional Resources

- **Full Documentation**: `docs/PRIORITY1_INTEGRATION_REPORT.md`
- **Troubleshooting**: `docs/TROUBLESHOOTING.md`
- **World Selection**: `docs/WORLD_SELECTION_GUIDE.md`
- **Performance Dashboard**: `docs/PERFORMANCE_DASHBOARD.md`
- **Safety System**: `docs/BEHAVIOR_TREE_SAFETY.md`

## 🎯 Example Workflow

### Complete Demo Session

```bash
# 1. Launch system
ros2 launch robot_gazebo complete_robot_simulation.launch.py world:=house

# 2. Wait for initialization (30 seconds)

# 3. Check system status
ros2 topic echo /system_status

# 4. List detected objects
ros2 topic pub --once /semantic_command std_msgs/String "data: 'list objects'"

# 5. Navigate to an object
ros2 topic pub --once /semantic_command std_msgs/String "data: 'go to chair'"

# 6. Monitor performance
ros2 topic echo /performance_metrics

# 7. Check safety status
ros2 topic echo /safety_status
```

## ⚡ Performance Tips

### Optimize for Speed

```bash
# Disable GUI for headless operation
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    gui:=false \
    rviz:=false
```

### Optimize for Quality

```bash
# Enable all features with navigation
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    navigation:=true \
    autonomous_exploration:=true
```

### Balance Performance and Features

```bash
# Core features only
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    semantic_slam:=true \
    advanced_safety:=true \
    pointcloud_viz:=false \
    performance_dashboard:=false
```

## 🎓 Learning Path

1. **Start Simple**: Launch with default settings
2. **Explore Features**: Try different semantic commands
3. **Monitor System**: Watch topics and metrics
4. **Test Worlds**: Try different environments
5. **Run Tests**: Execute integration tests
6. **Customize**: Adjust parameters for your needs

## 💡 Tips and Tricks

- Use `ros2 topic list` to see all available topics
- Use `ros2 node list` to see all running nodes
- Use `ros2 topic hz <topic>` to check publishing rate
- Use `ros2 topic bw <topic>` to check bandwidth usage
- Check logs with `ros2 log` for debugging

## 🆘 Getting Help

If you encounter issues:

1. Check the troubleshooting guide
2. Review system monitor output
3. Run integration tests
4. Check ROS 2 logs
5. Verify all dependencies are installed

---

**Happy Robot Building! 🤖**
