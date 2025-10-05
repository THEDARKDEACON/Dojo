# Robot Description Package

This package contains the URDF/XACRO description of the robot, along with related configuration files for visualization and simulation.

## Package Structure

> **Note**: This package has been cleaned to establish clear URDF hierarchy. See [CLEANUP_CHANGES_LOG.md](../../CLEANUP_CHANGES_LOG.md) for details on removed files.

```
robot_description/
├── CMakeLists.txt          - Build configuration
├── package.xml             - Package metadata and dependencies
├── README.md               - This documentation
├── config/                 - Configuration files
│   ├── README.md               - Configuration documentation
│   └── control_controllers_template.yaml - Controller template
├── launch/                 - Launch files
│   ├── description.launch.py   - Robot description launcher
│   ├── display.launch.py       - RViz display launcher
│   └── robot_state_publisher.launch.py - State publisher
├── rviz/                   - Cleaned RViz configurations
│   ├── robot_display.rviz      - Basic robot visualization
│   └── robot_simulation.rviz   - Simulation visualization
├── scripts/                - Utility scripts
│   └── display_robot.py        - Robot display script
└── urdf/                   - Cleaned URDF hierarchy
    ├── robot.urdf.xacro        - Primary robot description (source)
    ├── robot.urdf              - Compiled version (auto-generated)
    ├── common_properties.xacro - Shared properties and materials
    ├── dojo_robot.gazebo       - Gazebo-specific configurations
    └── sensors/                - Sensor-specific URDF files
        └── rplidar.urdf.xacro  - RPLiDAR sensor description
```

### Removed Files (Cleanup)
The following redundant files were removed during cleanup:
- `robot.urdf.xacro.clean` - Backup file removed
- `dojo_robot.urdf.xacro` - Redundant with main robot description
- `rviz/display.rviz` - Merged into `robot_display.rviz`
- `rviz/robot.rviz` - Consolidated into main configurations

## URDF File Structure

### Primary Files

The robot description follows a clear hierarchy with distinct purposes:

#### `robot.urdf.xacro` - Primary Robot Description Source
- **Purpose**: Main robot description file using xacro macros
- **Usage**: Source file for all robot description compilation
- **Features**: 
  - Parameterized robot dimensions and properties
  - Modular wheel macro for code reuse
  - Integrated Gazebo sensors (camera, LiDAR)
  - Differential drive plugin configuration
- **Compilation**: Automatically compiled to `robot.urdf` by xacro

#### `robot.urdf` - Compiled Robot Description
- **Purpose**: Runtime URDF file used by ROS 2 nodes
- **Usage**: Loaded by robot_state_publisher and Gazebo
- **Generation**: Auto-generated from `robot.urdf.xacro` - **DO NOT EDIT MANUALLY**
- **Update Process**: Run `xacro robot.urdf.xacro > robot.urdf` to regenerate

#### Supporting Files

- **`common_properties.xacro`**: Shared material definitions and properties
- **`dojo_robot.gazebo`**: Gazebo-specific configurations and plugins
- **`sensors/rplidar.urdf.xacro`**: RPLiDAR sensor description and properties

### URDF Maintenance Guidelines

#### Making Changes to Robot Description

1. **Always edit `robot.urdf.xacro`** - Never edit `robot.urdf` directly
2. **Test compilation**: Run `xacro robot.urdf.xacro` to verify syntax
3. **Update compiled version**: Run `xacro robot.urdf.xacro > robot.urdf`
4. **Validate**: Test with `xmllint --noout robot.urdf`
5. **Test loading**: Launch robot_state_publisher to verify

#### File Relationship

```
robot.urdf.xacro (source) 
    ↓ xacro compilation
robot.urdf (runtime)
    ↓ loaded by
robot_state_publisher → RViz/Gazebo
```

#### Xacro Compilation Commands

```bash
# Compile xacro to URDF
xacro src/robot_description/urdf/robot.urdf.xacro > src/robot_description/urdf/robot.urdf

# Validate URDF syntax
xmllint --noout src/robot_description/urdf/robot.urdf

# Test robot description loading
ros2 launch robot_description robot_state_publisher.launch.py
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

The `config/robot_controllers.yaml` file serves as a reference template for controller configurations. The active controller configuration for simulation is located in `robot_gazebo/config/ros2_control.yaml`.

### RViz Configurations

The package provides two RViz configurations for different use cases:

- **`robot_display.rviz`** - Basic robot visualization with TF frames
  - Shows robot model with all links and joints
  - Displays TF frame tree for debugging
  - Includes basic navigation tools (2D pose estimate, goal setting)
  - **Use when**: Debugging robot description, checking TF frames, basic robot visualization

- **`robot_simulation.rviz`** - Comprehensive simulation visualization
  - Includes robot model, laser scan, map, camera feed
  - Shows navigation path planning and robot pose
  - Displays robot footprint and odometry
  - **Use when**: Running full simulation with navigation and perception

#### Usage Examples

```bash
# Launch with basic robot display
ros2 run rviz2 rviz2 -d src/robot_description/rviz/robot_display.rviz

# Launch with simulation configuration
ros2 run rviz2 rviz2 -d src/robot_description/rviz/robot_simulation.rviz
```

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
