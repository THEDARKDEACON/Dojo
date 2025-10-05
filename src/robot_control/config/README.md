# Robot Control Configuration Files

This directory contains configuration files for the robot control system.

## Configuration Files

### `control_params.yaml`
**Purpose**: ROS2 parameters for robot control system nodes
**Used by**: 
- Robot control launch files
- Control system nodes
- Hardware interface components

**Structure**: ROS2 parameter format with node-specific sections
**Key Parameters**:
- `use_sim_time`: Whether to use simulation time
- Node-specific control parameters

### `arduino_config.yaml`
**Purpose**: Configuration for Arduino bridge communication
**Used by**:
- Arduino bridge nodes
- Hardware interface drivers
- Serial communication components

**Key Parameters**:
- `baud_rate`: Serial communication baud rate (115200)
- `debug`: Enable debug output
- `encoder_ticks_per_rev`: Encoder resolution

### `control_controllers.yaml`
**Purpose**: Controller configuration for control system
**Used by**:
- Controller manager
- Control system launch files
- Hardware control interfaces

**Key Parameters**:
- Controller definitions and parameters
- Control loop configurations

### `twist_mux_config.yaml`
**Purpose**: Twist multiplexer configuration
**Used by**:
- Twist mux nodes
- Velocity command routing
- Safety systems

**Key Parameters**:
- Input topic priorities
- Timeout configurations
- Safety parameters

## Usage Examples

### Loading in Launch Files
```python
# Load control parameters
config_file = PathJoinSubstitution([
    FindPackageShare('robot_control'),
    'config',
    'control_params.yaml'
])
```

### Parameter Access in Nodes
```python
# In a ROS2 node
self.declare_parameters_from_file('control_params.yaml')
use_sim_time = self.get_parameter('use_sim_time').value
```

## Maintenance Guidelines

1. **Follow naming conventions**: Use `<functionality>_<type>.yaml` pattern
2. **Add headers**: Include purpose, usage, and package information
3. **Document parameters**: Explain key parameters and their effects
4. **Update references**: Keep launch file references synchronized
5. **Test changes**: Verify functionality after configuration changes