# Dojo Robot Simulation Guide

This guide explains how to use the different simulation options available for the Dojo robot.

## Quick Start

The easiest way to start a simulation is using the provided script:

```bash
# Basic simulation with RViz
./scripts/launch_simulation.sh

# Complete simulation with SLAM, navigation, and perception
./scripts/launch_simulation.sh --complete

# Simulation with custom world
./scripts/launch_simulation.sh --world warehouse.world

# Headless simulation (no GUI)
./scripts/launch_simulation.sh --no-gui
```

## Launch File Options

### 1. Basic Gazebo Simulation

**File**: `src/robot_gazebo/launch/gazebo.launch.py`

**Purpose**: Minimal Gazebo simulation with robot and controllers.

**When to use**:
- Testing basic robot functionality
- Developing and debugging controllers
- Performance testing with minimal overhead

**Features**:
- Gazebo physics simulation
- Robot model with sensors
- ROS 2 Control integration
- Optional RViz visualization

**Example**:
```bash
ros2 launch robot_gazebo gazebo.launch.py rviz:=true world:=empty.world
```

### 2. Primary Simulation

**File**: `src/robot_gazebo/launch/simulation.launch.py`

**Purpose**: Standard simulation setup with visualization enabled by default.

**When to use**:
- General development and testing
- Demonstrating robot capabilities
- Educational purposes

**Features**:
- All features from basic simulation
- RViz enabled by default
- Simplified parameter interface

**Example**:
```bash
ros2 launch robot_gazebo simulation.launch.py world:=office_small.world
```

### 3. Complete Simulation

**File**: `src/robot_gazebo/launch/complete_simulation.launch.py`

**Purpose**: Full-featured simulation environment for autonomous robotics.

**When to use**:
- Testing autonomous navigation
- SLAM and mapping development
- Perception system testing
- Integration testing

**Features**:
- All features from primary simulation
- SLAM Toolbox for mapping
- Nav2 for autonomous navigation
- Perception system integration
- Teleop control capability

**Example**:
```bash
ros2 launch robot_gazebo complete_simulation.launch.py world:=warehouse.world
```

## Available Worlds

The simulation supports multiple pre-configured worlds:

- `empty.world` - Simple empty environment (default)
- `dojo_world.world` - Custom training environment
- `office_small.world` - Small office environment
- `warehouse.world` - Warehouse environment for navigation testing
- `house.world` - Residential environment
- `outdoor.world` - Outdoor environment

## Robot Control

### Teleop Control

Control the robot manually using keyboard:

```bash
# In a new terminal
source install/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

### Autonomous Navigation (Complete Simulation Only)

1. Start the complete simulation
2. In RViz, use the "Nav2 Goal" tool or "2D Goal Pose" tool
3. Click and drag to set a goal pose
4. The robot will automatically navigate to the goal

### SLAM and Mapping (Complete Simulation Only)

1. Start the complete simulation with SLAM enabled
2. Use teleop to drive the robot around
3. Watch the map build in real-time in RViz
4. Save the map when complete:
   ```bash
   ros2 run nav2_map_server map_saver_cli -f my_map
   ```

## Monitoring and Debugging

### Useful Topics

```bash
# Robot state
ros2 topic echo /odom                    # Robot odometry
ros2 topic echo /joint_states           # Joint positions

# Sensor data
ros2 topic echo /scan                    # LiDAR data
ros2 topic echo /camera/image_raw        # Camera feed
ros2 topic echo /camera/camera_info      # Camera parameters

# Navigation (complete simulation)
ros2 topic echo /map                     # SLAM map
ros2 topic echo /global_costmap/costmap  # Navigation costmap
ros2 topic echo /cmd_vel                 # Velocity commands
```

### Useful Services

```bash
# Controller management
ros2 service list | grep controller_manager

# Navigation services (complete simulation)
ros2 service list | grep nav2
```

## Performance Optimization

### For Better Performance

1. **Use headless mode** when GUI is not needed:
   ```bash
   ros2 launch robot_gazebo simulation.launch.py gui:=false rviz:=false
   ```

2. **Reduce sensor update rates** in the URDF configuration

3. **Use simpler worlds** for basic testing

4. **Disable unnecessary features** in complete simulation:
   ```bash
   ros2 launch robot_gazebo complete_simulation.launch.py use_perception:=false use_nav2:=false
   ```

## Troubleshooting

### Common Issues

1. **Gazebo fails to start**
   - Check Gazebo installation: `gazebo --version`
   - Verify environment: `echo $GAZEBO_MODEL_PATH`

2. **Controllers not loading**
   - Check controller configuration files
   - Verify robot description is valid

3. **RViz shows no data**
   - Ensure `use_sim_time` parameter is consistent
   - Check topic names and frame IDs

4. **Navigation not working**
   - Ensure map is being built (drive around first)
   - Check that Nav2 is properly configured
   - Verify goal poses are reachable

### Getting Help

1. Check the logs: `ros2 launch` output shows detailed error messages
2. List active topics: `ros2 topic list`
3. Check node status: `ros2 node list`
4. Monitor TF tree: `ros2 run tf2_tools view_frames`

## Development Tips

1. **Start simple**: Begin with basic simulation, then add features
2. **Use RViz**: Essential for debugging sensor data and robot state
3. **Check parameters**: Use `ros2 param list` and `ros2 param get` to inspect configuration
4. **Monitor performance**: Use `top` or `htop` to monitor CPU usage
5. **Save configurations**: Export RViz configs for different testing scenarios

## Integration with Hardware

The simulation is designed to be compatible with the real robot:

- Same topic names and message types
- Compatible controller configurations
- Identical sensor interfaces
- Consistent coordinate frames

This allows you to develop and test in simulation, then deploy to hardware with minimal changes.