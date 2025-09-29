# Robot Description Package

This package contains the URDF/XACRO description of the robot, along with related configuration files for visualization and simulation.

## Package Structure

```
robot_description/
├── CMakeLists.txt          - Build configuration
├── package.xml             - Package metadata and dependencies
├── config/                 - Configuration files
│   └── robot_controllers.yaml  - Controller configurations
├── launch/                 - Launch files
│   └── description.launch.py   - Main launch file
├── meshes/                 - 3D mesh files (if any)
├── models/                 - Gazebo model files (if any)
├── rviz/                   - RViz configuration
│   └── robot.rviz             - Default RViz configuration
├── scripts/                - Utility scripts
├── src/                    - Source code (if any)
├── test/                   - Test files
└── urdf/                   - URDF/XACRO files
    ├── robot.urdf.xacro    - Main robot description
    └── macros/             - XACRO macros (if any)
```

## Usage

### Launch the Robot Description

To launch the robot description with RViz:

```bash
ros2 launch robot_description description.launch.py
```

### Launch with Simulation

To launch with Gazebo simulation:

```bash
ros2 launch robot_simulation simulation.launch.py
```

## Configuration

### Controller Parameters

Controller parameters can be modified in `config/robot_controllers.yaml`.

### RViz Configuration

The default RViz configuration is stored in `rviz/robot.rviz`.

## Dependencies

- ROS 2 Humble
- ament_cmake
- robot_state_publisher
- joint_state_publisher
- rviz2
- xacro
- gazebo_ros2_control
- controller_manager
- hardware_interface

## Testing

Run tests with:

```bash
colcon test --packages-select robot_description
```

## License

Apache 2.0
