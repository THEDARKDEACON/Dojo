# Robot Control Configuration Files

This directory contains configuration files for the robot control system used in Gazebo simulation.

## Configuration Files

### `ros2_controllers.yaml`
**Purpose**: Active ROS2 control configuration for Gazebo simulation
**Used by**: 
- `gazebo.launch.py` - Main Gazebo launch file
- `dojo_robot.gazebo` - URDF Gazebo plugin configuration
- `configuration_manager.py` - Dynamic configuration updates

**Structure**: ROS2 control configuration with sections:
- `controller_manager`: Controller manager settings and controller types
- `diff_drive_controller`: Differential drive controller parameters
- `hardware_interface`: Gazebo hardware interface configuration
- `joint_state_broadcaster`: Joint state publishing configuration

**Key Features**:
- Supports 4-wheel differential drive (front/rear left/right wheels)
- Configurable wheel separation and radius
- Velocity and acceleration limits
- Odometry publishing with covariance
- PID parameters for wheel control
- Dynamic updates from master robot configuration

### Other Control Configuration Files

For reference and template configurations, see:
- `robot_description/config/robot_controllers.yaml` - Reference template for hardware deployments

## Usage Examples

### Loading in Launch Files
```python
# In gazebo.launch.py
config_file = PathJoinSubstitution([
    FindPackageShare('robot_gazebo'),
    'config',
    'ros2_controllers.yaml'
])
```

### URDF Integration
```xml
<!-- In dojo_robot.gazebo -->
<plugin filename="libgazebo_ros2_control.so" name="gazebo_ros2_control">
  <parameters>$(find robot_gazebo)/config/ros2_controllers.yaml</parameters>
</plugin>
```

### Dynamic Configuration Updates
The `configuration_manager.py` automatically updates this file with values from the master `robot_config.yaml`:
- Wheel dimensions (separation, radius)
- Velocity and acceleration limits
- Safety timeouts
- Control parameters

## Key Parameters

### Wheel Configuration
- `wheel_separation`: 0.26m (distance between left and right wheels)
- `wheel_radius`: 0.033m (wheel radius)
- `left_wheel_names`: ['left_wheel_joint'] (left wheel joint names)
- `right_wheel_names`: ['right_wheel_joint'] (right wheel joint names)

### Velocity Limits
- `max_velocity`: 0.5 m/s (linear), 1.0 rad/s (angular)
- `max_acceleration`: 3.0 m/s² (linear), 3.0 rad/s² (angular)
- `cmd_vel_timeout`: 1.0s (command timeout for safety)

### Odometry
- `odom_frame_id`: "odom"
- `base_frame_id`: "base_link"
- `publish_rate`: 50.0 Hz
- Covariance matrices for pose and twist estimation

## Maintenance Guidelines

1. **Primary Configuration**: This file is the primary control configuration for simulation
2. **Dynamic Updates**: Values are automatically updated by configuration_manager.py
3. **Manual Changes**: Manual changes may be overwritten by the configuration manager
4. **Hardware Deployment**: Use robot_description/config/robot_controllers.yaml as template for hardware
5. **Testing**: Always test configuration changes in simulation before hardware deployment

## Troubleshooting

### Common Issues
- **Controller not loading**: Check controller names match URDF joint names
- **Poor odometry**: Adjust wheel separation/radius or covariance values
- **Velocity limits**: Ensure limits match robot capabilities and safety requirements
- **Timeout errors**: Adjust cmd_vel_timeout for network latency

### Validation Commands
```bash
# Check controller status
ros2 control list_controllers

# Monitor joint states
ros2 topic echo /joint_states

# Check odometry
ros2 topic echo /odom

# Test velocity commands
ros2 topic pub /cmd_vel geometry_msgs/Twist "linear: {x: 0.1}"
```