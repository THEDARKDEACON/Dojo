# Dojo Robot Configuration Management

This directory contains the unified configuration management system for the Dojo Robot platform.

## Overview

The configuration management system provides a single source of truth for all robot parameters, ensuring consistency across all subsystems and preventing configuration conflicts.

## Files

- `robot_config.yaml` - Master configuration file containing all robot parameters
- Physical parameters (wheel dimensions, velocity limits)
- Hardware settings (Arduino, camera, LiDAR)
- Safety configuration (emergency stops, timeouts)
- System settings (logging, operation modes)

## Configuration Manager

The Configuration Manager (`robot_control.configuration_manager`) provides:

- **Centralized Configuration**: Single master config file for all parameters
- **Validation**: Comprehensive parameter validation against defined schemas
- **Conflict Detection**: Automatic detection of parameter mismatches between files
- **Parameter Propagation**: Automatic updating of subsystem configuration files
- **Environment Support**: Different configurations for development, production, and simulation

## Usage

### Basic Usage

```python
from robot_control.configuration_manager import ConfigurationManager

# Initialize configuration manager
config_manager = ConfigurationManager()

# Get parameters
wheel_base = config_manager.get_parameter('robot.physical_parameters.wheel_base')
arduino_config = config_manager.get_hardware_config()['arduino']

# Validate configuration
validation_result = config_manager.validate_configuration()
if not validation_result.is_valid:
    print("Configuration errors:", validation_result.errors)

# Check for conflicts
conflicts = config_manager.detect_conflicts()
if conflicts:
    print(f"Found {len(conflicts)} configuration conflicts")

# Propagate parameters to subsystem configs
config_manager.propagate_parameters()
```

### ROS2 Node

```bash
# Start configuration manager node
ros2 run robot_control configuration_manager

# Or use launch file
ros2 launch robot_control configuration_manager.launch.py
```

### Testing

```bash
# Run configuration test script
python3 scripts/test_configuration.py
```

## Configuration Structure

### Physical Parameters
- `wheel_base`: Distance between wheels (meters)
- `wheel_radius`: Wheel radius (meters)
- `max_linear_velocity`: Maximum forward/backward speed (m/s)
- `max_angular_velocity`: Maximum rotation speed (rad/s)

### Hardware Configuration
- **Arduino**: Serial port, baud rate, PID parameters
- **Camera**: Resolution, frame rate, device path
- **LiDAR**: Scan frequency, angle ranges, device path

### Safety Configuration
- `emergency_stop_timeout`: Maximum time to stop all motors (seconds)
- `obstacle_stop_distance`: Distance to trigger emergency stop (meters)
- `command_timeout`: Maximum time between velocity commands (seconds)

### System Configuration
- `use_simulation`: Enable/disable simulation mode
- `log_level`: Logging verbosity level
- `required_packages`: List of required ROS2 packages
- `optional_packages`: List of optional ROS2 packages

## Environment Overrides

The system supports environment-specific configuration overrides:

- `development`: Debug logging, conservative safety settings
- `production`: Minimal logging, optimized performance
- `simulation`: Simulation-specific parameters

Set the environment using:
```bash
export ROBOT_ENVIRONMENT=production
```

## Validation Schema

The configuration includes validation rules for:
- Parameter ranges (min/max values)
- Hardware compatibility (supported baud rates, resolutions)
- Safety constraints (minimum distances, maximum timeouts)

## Integration with Existing Systems

The Configuration Manager automatically updates existing configuration files:
- `src/robot_control/config/arduino.yaml`
- `src/robot_control/config/controllers.yaml`
- `src/robot_hardware/config/rosarduino_bridge.yaml`

This ensures backward compatibility while providing centralized management.

## Troubleshooting

### Common Issues

1. **Configuration file not found**
   - Ensure `robot_config.yaml` exists in the workspace `config/` directory
   - Check file permissions

2. **Validation errors**
   - Review parameter ranges in the validation schema
   - Check for typos in parameter names
   - Verify hardware compatibility settings

3. **Configuration conflicts**
   - Run conflict detection: `config_manager.detect_conflicts()`
   - Use parameter propagation: `config_manager.propagate_parameters()`
   - Manually review conflicting files

4. **Missing packages**
   - Install required ROS2 packages
   - Update package lists in system configuration
   - Use optional packages for non-critical components

### Debug Mode

Enable debug logging for detailed information:
```bash
export ROBOT_ENVIRONMENT=development
```

Or set log level in configuration:
```yaml
system:
  log_level: "DEBUG"
  enable_debug_output: true
```