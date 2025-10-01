# Robot Gazebo Simulation

This package provides the Gazebo simulation environment for the robot, including sensor plugins, world files, and launch configurations.

## Features

- Gazebo simulation with ROS 2 Control integration
- Support for multiple sensor configurations
- Pre-configured worlds for testing
- RViz visualization configurations
- Controller configurations for simulation

## Package Structure

```
robot_gazebo/
├── CMakeLists.txt          - Build configuration
├── package.xml             - Package metadata and dependencies
├── config/                 - Configuration files
│   ├── gazebo_controllers.yaml  - Controller configurations
│   └── ...
├── launch/                 - Launch files
│   └── simulation.launch.py  - Main simulation launch file
├── models/                 - Custom Gazebo models
├── rviz/                   - RViz configuration files
├── scripts/                - Utility scripts
└── worlds/                 - Gazebo world files
```

## Prerequisites

- ROS 2 Humble
- Gazebo Fortress or newer
- ROS 2 Control packages
- robot_description package
- robot_control package

## Installation

1. Clone this repository into your ROS 2 workspace
2. Install dependencies:
   ```bash
   rosdep install --from-paths src --ignore-src -r -y
   ```
3. Build the workspace:
   ```bash
   colcon build --packages-select robot_gazebo
   source install/setup.bash
   ```

## Usage

### Basic Simulation

To start the simulation with the default world:

```bash
ros2 launch robot_gazebo simulation.launch.py
```

### Specify a Different World

To use a different world file:

```bash
ros2 launch robot_gazebo simulation.launch.py world:=empty
```

### Simulation with RViz

RViz is launched by default with the simulation. It includes configurations for:
- Robot model visualization
- LIDAR point cloud
- Camera feed
- TF frames
- Navigation data

### Teleoperation

You can control the robot using teleop:

```bash
# Keyboard teleop
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# Or with a joystick
ros2 launch teleop_twist_joy teleop-launch.py
```

## Configuration

### Controllers

Controller parameters can be adjusted in `config/gazebo_controllers.yaml`.

### World Files

Custom world files can be added to the `worlds/` directory. The default world is `empty.world`.

### RViz Configuration

RViz configurations are stored in the `rviz/` directory. The main configuration is `simulation.rviz`.

## Testing

Run the tests with:

```bash
colcon test --packages-select robot_gazebo
```

## Troubleshooting

### Gazebo Not Starting
- Ensure Gazebo is properly installed
- Check that the `GAZEBO_MODEL_PATH` environment variable is set correctly

### Controller Issues
- Verify that the controller parameters match your robot's configuration
- Check the controller manager logs for errors

### Simulation Performance
- Reduce the update rate in the controller configuration
- Use a simpler world for testing

## License

Apache 2.0
