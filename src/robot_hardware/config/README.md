# Robot Hardware Configuration Files

This directory contains configuration files for the robot hardware interface system.

## Configuration Files

### `hardware_config.yaml`
**Purpose**: Unified hardware configuration for Dojo Robot
**Used by**:
- Hardware interface nodes
- Device drivers
- Hardware abstraction layer

**Structure**: ROS2 parameter format with driver-specific sections
**Key Sections**:
- `arduino_driver`: Arduino interface configuration
- Device-specific parameters
- Hardware interface settings

### `rosarduino_bridge_config.yaml`
**Purpose**: Configuration for ROS Arduino Bridge interface
**Used by**:
- ROSArduino bridge nodes
- Arduino communication interface
- Hardware bridge components

**Key Parameters**:
- Serial communication settings
- Arduino-specific configurations
- Bridge interface parameters

## Hardware Interface Architecture

The hardware configuration supports multiple interface types:
- **Arduino Bridge**: Direct Arduino communication
- **Hardware Abstraction**: Unified device interface
- **Driver Configuration**: Device-specific settings

## Usage Examples

### Loading Hardware Configuration
```python
# In hardware launch files
hardware_config = PathJoinSubstitution([
    FindPackageShare('robot_hardware'),
    'config',
    'hardware_config.yaml'
])
```

### Arduino Bridge Configuration
```python
# Loading Arduino bridge config
bridge_config = PathJoinSubstitution([
    FindPackageShare('robot_hardware'),
    'config',
    'rosarduino_bridge_config.yaml'
])
```

## Configuration Parameters

### Arduino Driver Parameters
- **Connection Settings**: Baud rate, port configuration
- **Device Settings**: Encoder configuration, motor parameters
- **Communication**: Protocol settings, timeout values

### Hardware Interface Parameters
- **Device Discovery**: Auto-detection settings
- **Safety Parameters**: Emergency stop, limits
- **Calibration**: Sensor calibration values

## Maintenance Guidelines

1. **Hardware Safety**: Always test configuration changes safely
2. **Backup Settings**: Keep working configurations backed up
3. **Documentation**: Document hardware-specific parameters
4. **Testing**: Verify hardware functionality after changes
5. **Compatibility**: Ensure configuration matches physical hardware