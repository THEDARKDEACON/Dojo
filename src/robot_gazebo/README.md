# Robot Gazebo Simulation

This package provides the Gazebo simulation environment for the robot, including sensor plugins, world files, and launch configurations.

## Features

- Gazebo simulation with ROS 2 Control integration
- Support for multiple sensor configurations
- Pre-configured worlds for testing
- RViz visualization configurations
- Controller configurations for simulation

## Package Structure

> **Note**: This package has been cleaned and streamlined. See [CLEANUP_CHANGES_LOG.md](../../CLEANUP_CHANGES_LOG.md) for details on removed files.

```
robot_gazebo/
├── CMakeLists.txt          - Build configuration
├── package.xml             - Package metadata and dependencies
├── README.md               - This documentation
├── config/                 - Configuration files
│   ├── gazebo_controllers.yaml  - Controller configurations
│   ├── ekf_config.yaml         - Extended Kalman Filter settings
│   └── slam_config.yaml        - SLAM configuration
├── launch/                 - Streamlined launch files
│   ├── gazebo.launch.py         - Basic Gazebo startup
│   ├── simulation.launch.py     - Primary simulation launcher
│   └── complete_simulation.launch.py - Full-featured simulation
├── rviz/                   - Single comprehensive RViz config
│   └── simulation.rviz          - Gazebo simulation visualization
├── scripts/                - Utility scripts
│   └── spawn_robot.py          - Robot spawning script
└── worlds/                 - Gazebo world files (50+ environments)
    ├── empty.world             - Default empty world
    ├── warehouse.world         - Warehouse environment
    ├── office_small.world      - Small office environment
    └── ...                     - Additional test environments
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

### Launch File Options

This package provides three main launch files for different simulation scenarios:

#### 1. Basic Gazebo Simulation (`gazebo.launch.py`)

**Purpose**: Launches basic Gazebo simulation with robot, controllers, and optional RViz.
**Use when**: You need a simple simulation setup for testing basic robot functionality.

```bash
# Basic launch
ros2 launch robot_gazebo gazebo.launch.py

# With RViz
ros2 launch robot_gazebo gazebo.launch.py rviz:=true

# Different world
ros2 launch robot_gazebo gazebo.launch.py world:=dojo_world.world

# Headless mode
ros2 launch robot_gazebo gazebo.launch.py gui:=false
```

**Parameters**:
- `world`: Gazebo world file (default: empty.world)
- `gui`: Start Gazebo GUI (default: true)
- `rviz`: Start RViz (default: false)
- `use_sim_time`: Use simulation clock (default: true)
- `spawn_x/y/z`: Robot spawn position (default: 0.0, 0.0, 0.1)
- `spawn_yaw`: Robot spawn orientation (default: 0.0)

#### 2. Primary Simulation (`simulation.launch.py`)

**Purpose**: Primary simulation launcher that includes the basic Gazebo simulation with RViz enabled by default.
**Use when**: You want a standard simulation setup with visualization.

```bash
# Standard simulation with RViz
ros2 launch robot_gazebo simulation.launch.py

# Different world
ros2 launch robot_gazebo simulation.launch.py world:=office_small.world

# Without RViz
ros2 launch robot_gazebo simulation.launch.py rviz:=false
```

**Parameters**:
- `world`: Gazebo world file (default: empty.world)
- `gui`: Start Gazebo GUI (default: true)
- `rviz`: Start RViz (default: true)
- `use_sim_time`: Use simulation clock (default: true)
- `spawn_x/y/z`: Robot spawn position
- `spawn_yaw`: Robot spawn orientation

#### 3. Complete Simulation (`complete_simulation.launch.py`)

**Purpose**: Full-featured simulation with SLAM, navigation, perception, and teleop capabilities.
**Use when**: You need a comprehensive simulation environment for testing autonomous navigation and perception.

```bash
# Complete simulation with all features
ros2 launch robot_gazebo complete_simulation.launch.py

# Complete simulation with specific world
ros2 launch robot_gazebo complete_simulation.launch.py world:=warehouse.world

# Complete simulation without perception
ros2 launch robot_gazebo complete_simulation.launch.py use_perception:=false

# Headless complete simulation
ros2 launch robot_gazebo complete_simulation.launch.py gui:=false
```

**Parameters**:
- `world`: Gazebo world file (default: empty.world)
- `gui`: Start Gazebo GUI (default: true)
- `use_sim_time`: Use simulation clock (default: true)
- `use_rviz`: Launch RViz (default: true)
- `use_slam`: Launch SLAM Toolbox (default: true)
- `use_nav2`: Launch Nav2 navigation (default: true)
- `use_perception`: Launch perception system (default: true)
- `use_teleop`: Enable teleop keyboard (default: true)

### Quick Start Examples

```bash
# Simple robot testing
ros2 launch robot_gazebo gazebo.launch.py rviz:=true

# Standard development workflow
ros2 launch robot_gazebo simulation.launch.py

# Full autonomous robot testing
ros2 launch robot_gazebo complete_simulation.launch.py

# Performance testing (headless)
ros2 launch robot_gazebo simulation.launch.py gui:=false rviz:=false
```

### RViz Visualization

RViz configurations include:
- Robot model visualization
- LIDAR point cloud
- Camera feed
- TF frames
- Navigation data (in complete simulation)
- SLAM map data (in complete simulation)

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

The package provides one comprehensive RViz configuration (consolidated from multiple previous configs):

- **`simulation.rviz`** - Complete Gazebo simulation visualization
  - Shows robot model with all sensors (laser, camera)
  - Displays odometry and TF frames
  - Includes map visualization for SLAM/navigation
  - Shows navigation path planning and costmaps
  - Consolidated features from previous `full_simulation.rviz` and `complete_simulation.rviz`
  - **Use when**: Running any Gazebo simulation scenario

#### Usage Example

```bash
# Launch RViz with simulation configuration
ros2 run rviz2 rviz2 -d src/robot_gazebo/rviz/simulation.rviz

# Or use with launch files (RViz enabled by default in simulation.launch.py)
ros2 launch robot_gazebo simulation.launch.py
```

#### Removed Configurations
The following RViz configurations were consolidated into `simulation.rviz`:
- `full_simulation.rviz` - Merged into main simulation config
- `complete_simulation.rviz` - Features integrated into main config
- `robot_simulation.rviz` - Moved to robot_description package

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
