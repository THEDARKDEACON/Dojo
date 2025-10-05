# Robot Mode Switching System

This document describes the new mode-specific configuration system that enables seamless switching between simulation and hardware modes.

## Overview

The robot system now supports automatic mode detection and configuration based on available packages and environment settings. This allows the same codebase to work in both simulation (Gazebo) and hardware modes without manual configuration changes.

## Features

### 1. Automatic Mode Detection
- Detects available ROS2 packages
- Checks for Gazebo installation
- Reads environment variables (`USE_SIMULATION`, `USE_GAZEBO`)
- Automatically selects the best available mode

### 2. Mode-Specific Configuration
- **Simulation Mode**: Uses Gazebo controllers, disables hardware discovery
- **Hardware Mode**: Enables hardware discovery, uses real device drivers
- Automatic parameter selection based on mode
- Validation of mode requirements

### 3. Unified Launch System
- Single launch file works for both modes
- Conditional package loading
- Graceful fallback when packages are missing
- Comprehensive error reporting

## Usage

### Method 1: Using the Launch Helper Script

```bash
# Auto-detect and launch in best available mode
./scripts/launch_robot.py

# Launch in specific mode
./scripts/launch_robot.py simulation
./scripts/launch_robot.py hardware

# Launch with additional components
./scripts/launch_robot.py simulation --perception --navigation
./scripts/launch_robot.py hardware --perception

# List available modes
./scripts/launch_robot.py --list-modes
```

### Method 2: Using ROS2 Launch Directly

```bash
# Launch with auto-detection
ros2 launch robot_bringup bringup.launch.py

# Force specific mode
ros2 launch robot_bringup bringup.launch.py operation_mode:=simulation
ros2 launch robot_bringup bringup.launch.py operation_mode:=hardware

# Launch with specific world (simulation)
ros2 launch robot_bringup bringup.launch.py operation_mode:=simulation world:=office.world

# Enable additional components
ros2 launch robot_bringup bringup.launch.py use_perception:=true use_navigation:=true
```

### Method 3: Using Environment Variables

```bash
# Set simulation mode
export USE_SIMULATION=true
ros2 launch robot_bringup bringup.launch.py

# Set hardware mode
export USE_SIMULATION=false
ros2 launch robot_bringup bringup.launch.py
```

## Configuration System

### Master Configuration File
The system uses `config/robot_config.yaml` as the single source of truth for all parameters. Mode-specific overrides are applied automatically:

```yaml
# Environment-specific overrides
environments:
  simulation:
    system:
      use_simulation: true
      use_sim_time: true
    hardware:
      arduino:
        auto_discover: false
  
  hardware:
    system:
      use_simulation: false
      use_sim_time: false
    hardware:
      arduino:
        auto_discover: true
```

### Configuration Manager
The `ConfigurationManager` class handles:
- Loading master configuration
- Applying mode-specific overrides
- Validating configuration consistency
- Propagating parameters to subsystems

```python
from robot_control.configuration_manager import ConfigurationManager

# Auto-detect mode
config_manager = ConfigurationManager()

# Force specific mode
config_manager = ConfigurationManager(mode='simulation')

# Get mode-specific parameters
launch_params = config_manager.get_launch_parameters()
mode_config = config_manager.get_mode_specific_config()
```

## Package Requirements

### Simulation Mode
- `robot_gazebo` - Gazebo simulation package
- `gazebo_ros` - Gazebo ROS2 integration
- `controller_manager` - ROS2 control framework
- `diff_drive_controller` - Differential drive controller
- Gazebo installation

### Hardware Mode
- `robot_hardware` - Hardware interface package
- `robot_control` - Control system package
- `robot_description` - Robot URDF description

### Optional Packages
- `robot_perception` - Computer vision and AI
- `robot_navigation` - Autonomous navigation
- `robot_sensors` - Additional sensor drivers

## Mode Detection Logic

1. **Environment Variables**: Check `USE_SIMULATION` and `USE_GAZEBO`
2. **Package Availability**: Verify required packages are installed
3. **System Dependencies**: Check for Gazebo installation
4. **Fallback**: Default to hardware mode if simulation not available

## Validation and Error Handling

The system performs comprehensive validation:
- **Package Requirements**: Ensures required packages are available
- **Configuration Consistency**: Validates parameter compatibility
- **Mode Requirements**: Checks mode-specific dependencies
- **Graceful Degradation**: Continues with available components

## Troubleshooting

### Common Issues

1. **"Missing required packages" error**
   - Install missing packages: `sudo apt install ros-$ROS_DISTRO-<package>`
   - Build workspace: `colcon build`

2. **"Gazebo not available" warning**
   - Install Gazebo: `sudo apt install gazebo ros-$ROS_DISTRO-gazebo-ros-pkgs`
   - Check installation: `which gazebo`

3. **"Configuration validation failed"**
   - Check `config/robot_config.yaml` for syntax errors
   - Verify parameter ranges and consistency

4. **Hardware not detected**
   - Check device permissions: `ls -l /dev/ttyACM* /dev/ttyUSB*`
   - Enable hardware discovery in configuration
   - Verify device connections

### Debug Mode

Enable debug logging for detailed information:

```bash
export ROS_LOG_LEVEL=DEBUG
ros2 launch robot_bringup bringup.launch.py
```

### Testing Configuration

Test the configuration system:

```bash
python3 test_mode_switching.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Launch System                            │
├─────────────────────────────────────────────────────────────┤
│  bringup.launch.py                                         │
│  ├── Mode Detection                                        │
│  ├── Package Validation                                    │
│  ├── Configuration Manager                                 │
│  └── Conditional Launch Includes                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                Configuration Manager                        │
├─────────────────────────────────────────────────────────────┤
│  ├── Master Config Loading (robot_config.yaml)            │
│  ├── Mode Detection & Override Application                 │
│  ├── Parameter Validation & Conflict Detection            │
│  └── Parameter Propagation to Subsystems                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────┬─────────────────────────────────────────────┐
│ Simulation Mode │                Hardware Mode                │
├─────────────────┼─────────────────────────────────────────────┤
│ ├── Gazebo      │ ├── Arduino Driver                         │
│ ├── Controllers│ ├── Camera Driver                          │
│ ├── Sim Sensors│ ├── LiDAR Driver                           │
│ └── RViz        │ ├── Hardware Manager                       │
│                 │ └── Safety System                          │
└─────────────────┴─────────────────────────────────────────────┘
```

## Future Enhancements

- **Mixed Mode**: Support for partial simulation (e.g., simulated sensors with real motors)
- **Remote Mode**: Support for remote robot operation
- **Cloud Mode**: Integration with cloud-based simulation
- **Configuration GUI**: Web-based configuration interface
- **Auto-Calibration**: Automatic parameter tuning based on hardware detection