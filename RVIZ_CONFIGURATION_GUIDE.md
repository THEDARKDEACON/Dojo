# RViz Configuration Guide

This document provides a comprehensive guide to the RViz configurations available in the Dojo robot project after the codebase cleanup and consolidation.

## Overview

The project now maintains a streamlined set of RViz configurations, with each package providing a maximum of 2 configurations with distinct, well-defined purposes. This reduces confusion and ensures developers can quickly choose the right visualization setup for their needs.

## Available Configurations

### Robot Description Package (`robot_description`)

#### 1. `robot_display.rviz` - Basic Robot Visualization
**Purpose**: Basic robot model display with TF frame debugging
**Best for**: Robot description development, URDF debugging, TF frame verification

**Features**:
- Robot model visualization with all links and joints
- Complete TF frame tree display
- Basic navigation tools (2D pose estimate, goal setting)
- Grid reference for spatial orientation
- Optimized for robot description debugging

**When to use**:
- Developing or modifying robot URDF files
- Debugging TF frame relationships
- Verifying robot model appearance
- Basic robot visualization without sensors

**Launch command**:
```bash
ros2 run rviz2 rviz2 -d src/robot_description/rviz/robot_display.rviz
```

#### 2. `robot_simulation.rviz` - Comprehensive Simulation View
**Purpose**: Complete simulation visualization with all sensors and navigation
**Best for**: Full simulation testing, navigation development, autonomous behavior testing

**Features**:
- Robot model with all sensor data (laser, camera)
- Map visualization for SLAM and navigation
- Path planning and robot trajectory display
- Robot footprint and pose visualization
- Odometry and localization data
- Camera feed integration
- Navigation goal and pose estimation tools

**When to use**:
- Running full robot simulation
- Testing navigation algorithms
- Developing autonomous behaviors
- Comprehensive system integration testing

**Launch command**:
```bash
ros2 run rviz2 rviz2 -d src/robot_description/rviz/robot_simulation.rviz
```

### Robot Gazebo Package (`robot_gazebo`)

#### 1. `simulation.rviz` - Gazebo Simulation Visualization
**Purpose**: Optimized visualization for Gazebo simulation environments
**Best for**: Gazebo simulation testing, sensor validation, physics simulation

**Features**:
- Robot model optimized for Gazebo rendering
- Laser scan visualization with proper Gazebo topics
- Camera feed from Gazebo sensors
- Odometry data from Gazebo physics
- Map integration for SLAM in simulation
- Path planning visualization
- TF frames with simulation-specific settings

**When to use**:
- Running any Gazebo simulation scenario
- Testing sensor plugins in simulation
- Validating robot behavior in simulated environments
- Performance testing with realistic sensor data

**Launch command**:
```bash
ros2 run rviz2 rviz2 -d src/robot_gazebo/rviz/simulation.rviz
# Or automatically with simulation launch files
ros2 launch robot_gazebo simulation.launch.py
```

### Robot Perception Package (`robot_perception`)

#### 1. `perception.rviz` - Perception System Visualization
**Purpose**: Comprehensive perception system monitoring and debugging
**Best for**: Computer vision development, object detection tuning, sensor fusion testing

**Features**:
- Raw camera feed display
- Object detection results with bounding boxes
- 3D detection markers in robot coordinate frame
- Integrated perception results from sensor fusion
- Robot model for spatial reference
- TF frames for coordinate system debugging
- Multiple image views for different processing stages

**When to use**:
- Developing computer vision algorithms
- Debugging object detection systems
- Testing sensor fusion capabilities
- Monitoring perception system performance
- Validating detection accuracy

**Launch command**:
```bash
ros2 run rviz2 rviz2 -d src/robot_perception/rviz/perception.rviz
# Or with perception system launch
ros2 launch robot_perception perception_system.launch.py rviz:=true
```

## Configuration Selection Guide

### By Development Phase

**Robot Description Development**:
- Use `robot_description/robot_display.rviz`
- Focus on URDF structure and TF frames

**Simulation Development**:
- Use `robot_gazebo/simulation.rviz`
- Comprehensive simulation environment testing

**Navigation Development**:
- Use `robot_description/robot_simulation.rviz`
- Full navigation stack visualization

**Perception Development**:
- Use `robot_perception/perception.rviz`
- Computer vision and sensor processing

### By Use Case

**Basic Robot Visualization**:
```bash
ros2 run rviz2 rviz2 -d src/robot_description/rviz/robot_display.rviz
```

**Full System Testing**:
```bash
ros2 launch robot_gazebo simulation.launch.py  # Includes simulation.rviz
```

**Autonomous Navigation**:
```bash
ros2 run rviz2 rviz2 -d src/robot_description/rviz/robot_simulation.rviz
```

**Computer Vision Development**:
```bash
ros2 run rviz2 rviz2 -d src/robot_perception/rviz/perception.rviz
```

## Integration with Launch Files

### Automatic RViz Launch

Many launch files automatically start RViz with appropriate configurations:

```bash
# Gazebo simulation with RViz
ros2 launch robot_gazebo simulation.launch.py  # Uses simulation.rviz

# Complete simulation with all systems
ros2 launch robot_gazebo complete_simulation.launch.py  # Uses simulation.rviz

# Perception system with visualization
ros2 launch robot_perception perception_system.launch.py rviz:=true  # Uses perception.rviz
```

### Manual RViz Launch

For custom setups or debugging:

```bash
# Launch specific configuration
ros2 run rviz2 rviz2 -d <path_to_config>

# Launch with custom settings
ros2 run rviz2 rviz2 -d src/robot_description/rviz/robot_display.rviz --ros-args -p use_sim_time:=true
```

## Customization Guidelines

### Adding Custom Displays

1. **Start with existing configuration**:
   ```bash
   ros2 run rviz2 rviz2 -d src/robot_description/rviz/robot_display.rviz
   ```

2. **Add required displays** through RViz GUI

3. **Save configuration** with descriptive name

4. **Document purpose** in package README

### Configuration Naming Convention

- Use descriptive names that indicate purpose
- Follow pattern: `<purpose>.rviz`
- Examples: `robot_display.rviz`, `simulation.rviz`, `perception.rviz`

### Maintaining Configurations

1. **Keep configurations minimal** - only include necessary displays
2. **Document each configuration's purpose** in package README
3. **Test configurations** with typical use cases
4. **Update configurations** when adding new sensors or capabilities

## Troubleshooting

### Common Issues

**Configuration not loading**:
- Check file path is correct
- Verify RViz2 is installed
- Ensure all required topics exist

**Missing displays**:
- Check if required nodes are running
- Verify topic names match configuration
- Use `ros2 topic list` to check available topics

**Performance issues**:
- Reduce update rates in configuration
- Disable unnecessary displays
- Use simpler visualization options

### Debug Commands

```bash
# List available topics
ros2 topic list

# Check topic data
ros2 topic echo /topic_name

# Monitor topic rates
ros2 topic hz /topic_name

# Check node status
ros2 node list
ros2 node info /node_name
```

## Best Practices

1. **Choose the right configuration** for your task
2. **Start with provided configurations** before creating custom ones
3. **Document any custom configurations** you create
4. **Test configurations** with real robot data when possible
5. **Keep configurations updated** as system evolves
6. **Use descriptive names** for any new configurations

## Migration from Old Configurations

The cleanup process consolidated multiple redundant configurations. Here's the mapping:

### Robot Description
- `display.rviz` → `robot_display.rviz` (enhanced)
- `dojo_robot.rviz` → **Removed** (merged into robot_display.rviz)
- `robot.rviz` → **Removed** (functionality in robot_simulation.rviz)

### Robot Gazebo
- `full_simulation.rviz` → **Removed** (merged into simulation.rviz)
- `complete_simulation.rviz` → **Removed** (merged into simulation.rviz)
- `robot_simulation.rviz` → **Removed** (redundant with simulation.rviz)

### Robot Perception
- `object_detection.rviz` → **Removed** (merged into perception.rviz)
- `perception_integration.rviz` → **Removed** (merged into perception.rviz)

If you were using any of the removed configurations, use the corresponding consolidated version listed above.