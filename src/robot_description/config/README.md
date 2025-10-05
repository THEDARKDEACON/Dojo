# Robot Description Configuration Files

This directory contains configuration files for the robot description system.

## Configuration Files

### `control_controllers_template.yaml`
**Purpose**: Reference template for controller configurations
**Used by**: 
- Documentation and reference
- Hardware deployment templates
- Controller configuration examples

**Structure**: ROS2 controller configuration template
**Note**: This is a template file. The active controller configuration for simulation is in `robot_gazebo/config/ros2_controllers.yaml`

**Key Sections**:
- `controller_manager`: Controller manager settings
- `diff_drive_controller`: Differential drive controller template
- `joint_state_broadcaster`: Joint state publishing configuration

## Controller Configuration Architecture

```
Controller Configuration Hierarchy:
├── Template (control_controllers_template.yaml) - Reference/Documentation
└── Active Configs:
    ├── Simulation: robot_gazebo/config/ros2_controllers.yaml
    └── Hardware: (deployed from template)
```

## Usage Examples

### Using as Template
```bash
# Copy template for hardware deployment
cp control_controllers_template.yaml hardware_controllers.yaml
# Edit hardware_controllers.yaml for specific hardware
```

### Reference for Development
```yaml
# Example controller configuration structure
controller_manager:
  ros__parameters:
    update_rate: 100
    joint_state_broadcaster:
      type: joint_state_broadcaster/JointStateBroadcaster
```

## Template Parameters

### Controller Manager
- **Update Rate**: Control loop frequency (100 Hz)
- **Controller Types**: Available controller definitions
- **Hardware Interface**: Controller-hardware mapping

### Differential Drive Controller
- **Wheel Configuration**: Joint names and kinematics
- **Velocity Limits**: Speed and acceleration constraints
- **Odometry Settings**: Frame IDs and covariance
- **PID Parameters**: Control loop gains

### Joint State Broadcaster
- **Joint Names**: Joints to publish state for
- **Publishing Rate**: State update frequency

## Deployment Guidelines

### For Simulation
- Use `robot_gazebo/config/ros2_controllers.yaml`
- Configuration is automatically managed
- Parameters updated from master robot config

### For Hardware
1. Copy template to hardware-specific file
2. Modify parameters for actual hardware
3. Update joint names to match hardware
4. Tune PID parameters for hardware response
5. Test configuration safely

### For Development
- Use template as reference for new controllers
- Follow established parameter structure
- Document custom parameters

## Maintenance Guidelines

1. **Template Integrity**: Keep template as clean reference
2. **Documentation**: Document parameter purposes and ranges
3. **Version Control**: Track changes to template
4. **Hardware Safety**: Test hardware configurations carefully
5. **Synchronization**: Keep template updated with best practices

## Related Files

- **Active Simulation Config**: `robot_gazebo/config/ros2_controllers.yaml`
- **Master Robot Config**: `config/robot_config.yaml`
- **URDF Integration**: `urdf/dojo_robot.gazebo`