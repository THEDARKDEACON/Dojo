# Launch System Architecture

**Project**: Dojo Robot  
**Last Updated**: November 11, 2025

This document describes the complete launch system architecture for the Dojo Robot project, including primary entry points, feature flags, and usage examples.

---

## Table of Contents

1. [Overview](#overview)
2. [Primary Entry Points](#primary-entry-points)
3. [Launch System Hierarchy](#launch-system-hierarchy)
4. [Feature Flags](#feature-flags)
5. [Usage Examples](#usage-examples)
6. [Launch File Reference](#launch-file-reference)
7. [Startup Validation](#startup-validation)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The Dojo Robot launch system is designed with a hierarchical structure that allows flexible configuration while maintaining simplicity for common use cases.

### Design Principles

1. **Single Primary Entry Point**: `complete_simulation.launch.py` for simulation
2. **Feature Flags**: Enable/disable features via launch arguments
3. **Sensible Defaults**: Works out-of-the-box with minimal configuration
4. **Modular Design**: Each subsystem has its own launch file
5. **Validation**: Startup checks ensure system readiness

---

## Primary Entry Points

### 1. Simulation (Primary)

**File**: `src/robot_gazebo/launch/complete_simulation.launch.py`  
**Purpose**: Full-featured robot simulation with all subsystems  
**Status**: ✅ Primary entry point for simulation

**Basic Usage**:
```bash
ros2 launch robot_gazebo complete_simulation.launch.py
```

**With Options**:
```bash
ros2 launch robot_gazebo complete_simulation.launch.py \
    world:=house \
    use_slam:=true \
    use_nav2:=true \
    use_perception:=true \
    use_rviz:=true
```

### 2. Real Robot

**File**: `src/robot_bringup/launch/bringup.launch.py`  
**Purpose**: Launch real robot hardware and systems  
**Status**: ✅ Primary entry point for real robot

**Basic Usage**:
```bash
ros2 launch robot_bringup bringup.launch.py
```

### 3. Cutting-Edge Features (Convenience Wrapper)

**File**: `start_cutting_edge_robot.py` (root directory)  
**Purpose**: Python wrapper for easy launch with all Priority 1 features  
**Status**: ✅ Convenience script for advanced features

**Basic Usage**:
```bash
python3 start_cutting_edge_robot.py
```

**With Options**:
```bash
python3 start_cutting_edge_robot.py mapping_world full
python3 start_cutting_edge_robot.py house demo
python3 start_cutting_edge_robot.py warehouse headless
```

---

## Launch System Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│  PRIMARY ENTRY POINTS                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  complete_simulation.launch.py (SIMULATION)                 │
│  bringup.launch.py (REAL ROBOT)                            │
│  start_cutting_edge_robot.py (CONVENIENCE WRAPPER)         │
│                                                             │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ├─── Gazebo Simulation
                   │    └─── gazebo.launch.py
                   │         ├─── Robot Description
                   │         │    └─── description.launch.py
                   │         └─── Robot Controllers
                   │
                   ├─── Navigation Stack
                   │    ├─── slam.launch.py (SLAM Toolbox)
                   │    ├─── nav2.launch.py (Nav2 Stack)
                   │    ├─── localization.launch.py (AMCL)
                   │    └─── autonomous_exploration.launch.py
                   │
                   ├─── Perception System
                   │    ├─── perception.launch.py
                   │    ├─── object_detector.launch.py (YOLO)
                   │    └─── vision_detection.launch.py
                   │
                   ├─── Semantic SLAM & Advanced Features
                   │    ├─── cutting_edge_features.launch.py (MASTER)
                   │    │    ├─── semantic_slam.launch.py
                   │    │    ├─── semantic_interface.launch.py
                   │    │    ├─── advanced_safety.launch.py
                   │    │    ├─── enhanced_visualization.launch.py
                   │    │    └─── performance_dashboard.launch.py
                   │    │
                   │    └─── Individual Feature Launches
                   │         ├─── semantic_slam.launch.py
                   │         ├─── semantic_interface.launch.py
                   │         ├─── advanced_safety.launch.py
                   │         ├─── enhanced_visualization.launch.py
                   │         └─── performance_dashboard.launch.py
                   │
                   ├─── Control System
                   │    ├─── control.launch.py
                   │    ├─── bypass_mode.launch.py
                   │    └─── safety_system.launch.py
                   │
                   └─── Visualization
                        ├─── rviz.launch.py
                        └─── enhanced_rviz.launch.py
```

---

## Feature Flags

### Complete Simulation Launch Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `world` | string | `empty.world` | Gazebo world file name |
| `use_sim_time` | bool | `true` | Use simulation clock |
| `gui` | bool | `true` | Show Gazebo GUI |
| `use_rviz` | bool | `true` | Launch RViz visualization |
| `use_teleop` | bool | `true` | Enable teleoperation |
| `use_slam` | bool | `true` | Enable SLAM Toolbox |
| `use_nav2` | bool | `true` | Enable Nav2 navigation |
| `use_perception` | bool | `true` | Enable perception system |
| `use_semantic_slam` | bool | `false` | Enable semantic SLAM (Priority 1) |
| `use_advanced_safety` | bool | `false` | Enable advanced safety (Priority 1) |
| `use_enhanced_viz` | bool | `false` | Enable 3D visualization (Priority 1) |
| `use_performance_dashboard` | bool | `false` | Enable performance dashboard (Priority 1) |

### Cutting-Edge Features Launch Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `use_sim_time` | bool | `true` | Use simulation clock |
| `enable_semantic_slam` | bool | `true` | Semantic SLAM with YOLO |
| `enable_semantic_interface` | bool | `true` | Natural language commands |
| `enable_advanced_safety` | bool | `true` | Predictive safety system |
| `enable_enhanced_viz` | bool | `true` | 3D point cloud visualization |
| `enable_performance_dashboard` | bool | `true` | Performance monitoring |

### Bringup Launch Arguments (Real Robot)

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `use_sim_time` | bool | `false` | Use simulation clock |
| `use_rviz` | bool | `true` | Launch RViz |
| `use_hardware` | bool | `true` | Enable hardware interfaces |
| `use_control` | bool | `true` | Enable control system |
| `use_navigation` | bool | `true` | Enable navigation |
| `use_perception` | bool | `true` | Enable perception |

---

## Usage Examples

### Basic Simulation

```bash
# Minimal simulation (empty world, basic features)
ros2 launch robot_gazebo complete_simulation.launch.py

# House environment with all features
ros2 launch robot_gazebo complete_simulation.launch.py world:=house

# Warehouse with SLAM only (no navigation)
ros2 launch robot_gazebo complete_simulation.launch.py \
    world:=warehouse \
    use_nav2:=false

# Headless simulation (no GUI, no RViz)
ros2 launch robot_gazebo complete_simulation.launch.py \
    gui:=false \
    use_rviz:=false
```

### Cutting-Edge Features

```bash
# All Priority 1 features enabled
ros2 launch robot_semantic_slam cutting_edge_features.launch.py

# Semantic SLAM only
ros2 launch robot_semantic_slam semantic_slam.launch.py

# Advanced safety only
ros2 launch robot_semantic_slam advanced_safety.launch.py

# Performance dashboard only
ros2 launch robot_semantic_slam performance_dashboard.launch.py

# Custom feature combination
ros2 launch robot_semantic_slam cutting_edge_features.launch.py \
    enable_semantic_slam:=true \
    enable_advanced_safety:=true \
    enable_enhanced_viz:=false \
    enable_performance_dashboard:=true
```

### Complete System with Cutting-Edge Features

```bash
# Full simulation + all cutting-edge features
ros2 launch robot_gazebo complete_simulation.launch.py \
    world:=house \
    use_semantic_slam:=true \
    use_advanced_safety:=true \
    use_enhanced_viz:=true \
    use_performance_dashboard:=true
```

### Convenience Wrapper

```bash
# Default (mapping_world, full mode)
python3 start_cutting_edge_robot.py

# Specific world
python3 start_cutting_edge_robot.py house

# Specific world and mode
python3 start_cutting_edge_robot.py warehouse full
python3 start_cutting_edge_robot.py office_small demo
python3 start_cutting_edge_robot.py outdoor headless
```

**Modes**:
- `full`: All features, GUI, RViz, autonomous exploration
- `demo`: SLAM, GUI, autonomous exploration (no vision)
- `headless`: All features, no GUI, no RViz (for servers)

### Real Robot

```bash
# Full system
ros2 launch robot_bringup bringup.launch.py

# Without navigation
ros2 launch robot_bringup bringup.launch.py use_navigation:=false

# Minimal (hardware only)
ros2 launch robot_bringup bringup.launch.py \
    use_navigation:=false \
    use_perception:=false \
    use_rviz:=false
```

---

## Launch File Reference

### Core Launch Files

#### 1. complete_simulation.launch.py
**Package**: robot_gazebo  
**Purpose**: Primary simulation entry point  
**Includes**:
- Gazebo world and robot spawning
- SLAM Toolbox
- Nav2 navigation stack
- Perception system
- RViz visualization
- Optional cutting-edge features

**Key Features**:
- ✅ Single command to start full system
- ✅ Configurable via launch arguments
- ✅ Sensible defaults for quick start
- ✅ Modular feature enabling

#### 2. cutting_edge_features.launch.py
**Package**: robot_semantic_slam  
**Purpose**: Master launcher for all Priority 1 features  
**Includes**:
- Semantic SLAM with YOLO
- Natural language interface
- Advanced safety system
- 3D point cloud visualization
- Performance dashboard

**Key Features**:
- ✅ All advanced features in one launch
- ✅ Individual feature flags
- ✅ Integrated with main simulation
- ✅ Can run standalone

#### 3. bringup.launch.py
**Package**: robot_bringup  
**Purpose**: Real robot system startup  
**Includes**:
- Hardware interfaces
- Control system
- Navigation stack
- Perception system
- RViz visualization

**Key Features**:
- ✅ Hardware initialization
- ✅ Safety checks
- ✅ Graceful degradation
- ✅ Status reporting

### Feature-Specific Launch Files

#### Semantic SLAM
- `semantic_slam.launch.py` - Core semantic SLAM with YOLO
- `semantic_interface.launch.py` - Natural language commands

#### Safety
- `advanced_safety.launch.py` - Predictive safety system
- `safety_system.launch.py` - Basic safety supervisor

#### Visualization
- `enhanced_visualization.launch.py` - 3D point clouds
- `performance_dashboard.launch.py` - Performance monitoring
- `rviz.launch.py` - Basic RViz
- `enhanced_rviz.launch.py` - Advanced RViz with 3D features

#### Navigation
- `navigation.launch.py` - Full navigation stack
- `nav2.launch.py` - Nav2 only
- `slam.launch.py` - SLAM Toolbox only
- `localization.launch.py` - AMCL localization
- `autonomous_exploration.launch.py` - Autonomous exploration

#### Perception
- `perception.launch.py` - Full perception system
- `object_detector.launch.py` - YOLO object detection
- `vision_detection.launch.py` - Vision processing

#### Control
- `control.launch.py` - Main control system
- `bypass_mode.launch.py` - Direct motor control
- `configuration_manager.launch.py` - Runtime configuration

---

## Startup Validation

### Automatic Checks

The launch system performs automatic validation:

1. **ROS2 Environment**
   - ✅ ROS2 installation detected
   - ✅ Workspace sourced correctly
   - ✅ Required packages available

2. **Dependencies**
   - ✅ Python packages installed (YOLO, OpenCV, etc.)
   - ✅ ROS2 packages built
   - ✅ Configuration files present

3. **Hardware** (Real Robot Only)
   - ✅ Arduino connection
   - ✅ Camera availability
   - ✅ LiDAR connection

4. **Configuration**
   - ✅ Valid world file
   - ✅ Valid parameter files
   - ✅ Compatible feature combinations

### Startup Report

After launch, the system provides a startup report:

```
🚀 ═══════════════════════════════════════════════════════════════
   DOJO ROBOT SYSTEM STARTUP REPORT
═══════════════════════════════════════════════════════════════ 🚀

✅ SYSTEM STATUS: READY

📦 ACTIVE FEATURES:
   ✅ Gazebo Simulation (world: house.world)
   ✅ SLAM Toolbox
   ✅ Nav2 Navigation
   ✅ Perception System (YOLO)
   ✅ Semantic SLAM
   ✅ Advanced Safety
   ✅ 3D Visualization
   ✅ Performance Dashboard
   ✅ RViz Visualization

🔧 SYSTEM RESOURCES:
   CPU: 45% | Memory: 2.1GB | Network: 15 Mbps

📡 ACTIVE TOPICS:
   /semantic_map
   /performance_metrics
   /safety_status
   /cmd_vel
   /scan
   /camera/image_raw

🎮 READY FOR OPERATION!
```

### Error Handling

If validation fails, the system provides clear error messages:

```
❌ STARTUP FAILED

⚠️ ISSUES DETECTED:
   ❌ World file not found: invalid_world.world
   💡 Available worlds: house, office_small, warehouse, outdoor
   
   ❌ Python package missing: ultralytics
   💡 Install with: pip install ultralytics
   
   ⚠️ High CPU usage detected: 95%
   💡 Close other applications for better performance

🔧 FIX THE ISSUES ABOVE AND TRY AGAIN
```

---

## Troubleshooting

### Common Issues

#### 1. Launch Fails Immediately

**Symptoms**: Launch command exits with error  
**Causes**:
- Workspace not built
- ROS2 not sourced
- Missing dependencies

**Solutions**:
```bash
# Build workspace
colcon build

# Source workspace
source install/setup.bash

# Install dependencies
./scripts/install_dependencies.sh
```

#### 2. Gazebo Doesn't Start

**Symptoms**: No Gazebo window appears  
**Causes**:
- Invalid world file
- Gazebo already running
- Graphics driver issues

**Solutions**:
```bash
# Check world file exists
ls src/robot_gazebo/worlds/

# Kill existing Gazebo
killall gzserver gzclient

# Check graphics
glxinfo | grep OpenGL
```

#### 3. Features Not Working

**Symptoms**: Feature enabled but not functioning  
**Causes**:
- Feature flag not set correctly
- Dependencies missing
- Configuration error

**Solutions**:
```bash
# Verify feature flag
ros2 param list | grep enable

# Check node status
ros2 node list

# View logs
ros2 run rqt_console rqt_console
```

#### 4. Performance Issues

**Symptoms**: Slow operation, lag, high CPU  
**Causes**:
- Too many features enabled
- Insufficient resources
- Gazebo rendering issues

**Solutions**:
```bash
# Disable unnecessary features
ros2 launch robot_gazebo complete_simulation.launch.py \
    use_perception:=false \
    gui:=false

# Use headless mode
python3 start_cutting_edge_robot.py mapping_world headless

# Monitor resources
htop
```

### Debug Mode

Enable debug output for troubleshooting:

```bash
# Set log level to debug
export RCUTILS_CONSOLE_OUTPUT_FORMAT="[{severity}] [{name}]: {message}"
export RCUTILS_LOGGING_USE_STDOUT=1
export RCUTILS_LOGGING_BUFFERED_STREAM=0

# Launch with debug
ros2 launch robot_gazebo complete_simulation.launch.py --log-level debug
```

### Getting Help

1. **Check Documentation**:
   - `docs/IMPLEMENTATION_GUIDE.md`
   - `docs/TROUBLESHOOTING.md`
   - `docs/LAUNCH_SYSTEM_ARCHITECTURE.md` (this file)

2. **View Logs**:
   ```bash
   ros2 run rqt_console rqt_console
   ```

3. **Check System Status**:
   ```bash
   ros2 node list
   ros2 topic list
   ros2 param list
   ```

4. **Report Issues**:
   - Include launch command used
   - Include error messages
   - Include system information (OS, ROS2 version)

---

## Best Practices

### 1. Start Simple

Begin with minimal features and add incrementally:

```bash
# Step 1: Basic simulation
ros2 launch robot_gazebo complete_simulation.launch.py \
    use_nav2:=false \
    use_perception:=false

# Step 2: Add SLAM
ros2 launch robot_gazebo complete_simulation.launch.py \
    use_nav2:=false

# Step 3: Add navigation
ros2 launch robot_gazebo complete_simulation.launch.py

# Step 4: Add cutting-edge features
python3 start_cutting_edge_robot.py
```

### 2. Use Appropriate Modes

Choose the right mode for your use case:

- **Development**: Use `gui:=true` and `use_rviz:=true` for debugging
- **Testing**: Use `headless` mode for automated tests
- **Demos**: Use `demo` mode for presentations
- **Production**: Use minimal features for efficiency

### 3. Monitor Resources

Keep an eye on system resources:

```bash
# Monitor in real-time
watch -n 1 'ros2 topic echo /performance_metrics --once'

# Check specific metrics
ros2 topic echo /performance_metrics | grep cpu_usage
```

### 4. Save Configurations

Create custom launch files for common configurations:

```python
# my_custom_config.launch.py
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                FindPackageShare('robot_gazebo'),
                '/launch/complete_simulation.launch.py'
            ]),
            launch_arguments={
                'world': 'house',
                'use_semantic_slam': 'true',
                'use_advanced_safety': 'true',
                # ... your custom settings
            }.items()
        )
    ])
```

---

## Summary

The Dojo Robot launch system provides:

- ✅ **Single Primary Entry Point**: `complete_simulation.launch.py`
- ✅ **Flexible Configuration**: Feature flags for all subsystems
- ✅ **Sensible Defaults**: Works out-of-the-box
- ✅ **Modular Design**: Each feature can be enabled/disabled
- ✅ **Validation**: Automatic startup checks
- ✅ **Clear Documentation**: Comprehensive usage examples
- ✅ **Troubleshooting**: Common issues and solutions

**Quick Start**:
```bash
# Simulation with all features
python3 start_cutting_edge_robot.py

# Or use ROS2 launch directly
ros2 launch robot_gazebo complete_simulation.launch.py world:=house
```

---

**Document Version**: 1.0  
**Last Updated**: November 11, 2025  
**Maintained By**: Dojo Robot Team
