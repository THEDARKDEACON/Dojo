# Robot Control Package

This package provides the control system for the robot, including motor control, odometry, and low-level hardware interfaces.

## Features

- ROS 2 Control integration
- Differential drive controller
- Hardware interface for Arduino
- Simulation support
- Diagnostics and monitoring

## Package Structure

```
robot_control/
├── CMakeLists.txt          - Build configuration
├── package.xml             - Package metadata and dependencies
├── config/                 - Configuration files
│   └── controllers.yaml    - Controller configurations
├── launch/                 - Launch files
│   └── control.launch.py   - Main launch file
├── include/                - C++ headers (if any)
├── src/                    - C++ source files (if any)
├── robot_control/          - Python package
│   ├── __init__.py
│   ├── control_manager.py  - Main control node
│   └── hardware/           - Hardware interfaces
├── scripts/                - Executable scripts
└── test/                   - Test files
```

## Usage

### Launch the Control System

To start the control system:

```bash
ros2 launch robot_control control.launch.py
```

### Launch with Simulation

To launch with Gazebo simulation:

```bash
ros2 launch robot_control control.launch.py use_sim_time:=true
```

### Control the Robot

Publish velocity commands to control the robot:

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "linear:
  x: 0.1
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.1"
```

## Configuration

### Controller Parameters

Controller parameters can be modified in `config/controllers.yaml`.

### Hardware Interface

Configure the hardware interface in `robot_control/hardware/arduino_interface.py`.

## Dependencies

- ROS 2 Humble
- ament_cmake
- controller_interface
- controller_manager
- hardware_interface
- pluginlib
- realtime_tools
- diagnostic_updater

## Testing

Run tests with:

```bash
colcon test --packages-select robot_control
```

## License

Apache 2.0
