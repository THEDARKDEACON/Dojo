# Robot Topics and Control Guide

## Robot Configuration
- **Drive System**: Front-wheel drive (2 motorized wheels + 2 rear casters)
- **Sensors**: Camera + LiDAR
- **Control**: Twist mux for multiple command sources

## Control Topics

### Primary Control
- **`/cmd_vel`** - Main robot control input (geometry_msgs/Twist)
  - Used by: Gazebo differential drive plugin
  - Controls: Linear velocity (x) and angular velocity (z)

### Twist Mux Inputs (Priority-based)
- **`/cmd_vel_teleop`** - Teleop keyboard control (Priority: 100)
- **`/cmd_vel_nav`** - Navigation commands (Priority: 10) 
- **`/cmd_vel_safety`** - Safety override commands (Priority: 200 - Highest)

### Odometry
- **`/odom`** - Robot odometry (nav_msgs/Odometry)
  - Provides: Position, orientation, velocities
  - Frame: odom -> base_link

## Sensor Topics

### Camera
- **`/camera/image_raw`** - Raw camera images (sensor_msgs/Image)
- **`/camera/camera_info`** - Camera calibration info (sensor_msgs/CameraInfo)

### LiDAR
- **`/scan`** - Laser scan data (sensor_msgs/LaserScan)
  - Range: 0.1m to 12.0m
  - 360° coverage
  - Update rate: 10 Hz

## SLAM and Mapping Topics

### SLAM Toolbox
- **`/map`** - Generated map (nav_msgs/OccupancyGrid)
- **`/slam_toolbox/scan_visualization`** - SLAM scan visualization
- **`/slam_toolbox/graph_visualization`** - SLAM graph visualization
- **`/slam_toolbox/feedback`** - SLAM feedback messages
- **`/slam_toolbox/update`** - Map update notifications

## Transform Topics
- **`/tf`** - Dynamic transforms
- **`/tf_static`** - Static transforms

## System Topics
- **`/robot_description`** - Robot URDF description
- **`/joint_states`** - Joint positions and velocities
- **`/clock`** - Simulation time (when use_sim_time=true)

## How to Control the Robot

### 1. Teleop Control
```bash
# Start teleop keyboard
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r /cmd_vel:=/cmd_vel_teleop

# Controls:
# i - forward
# , - backward  
# j - turn left
# l - turn right
# k - stop
```

### 2. Direct Command
```bash
# Move forward
ros2 topic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0.2}, angular: {z: 0.0}}'

# Turn in place
ros2 topic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0.0}, angular: {z: 0.5}}'

# Stop
ros2 topic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0.0}, angular: {z: 0.0}}'
```

### 3. Through Twist Mux (Recommended)
```bash
# Teleop control (medium priority)
ros2 topic pub /cmd_vel_teleop geometry_msgs/Twist '{linear: {x: 0.2}, angular: {z: 0.0}}'

# Navigation control (low priority)
ros2 topic pub /cmd_vel_nav geometry_msgs/Twist '{linear: {x: 0.1}, angular: {z: 0.2}}'

# Safety override (highest priority)
ros2 topic pub /cmd_vel_safety geometry_msgs/Twist '{linear: {x: 0.0}, angular: {z: 0.0}}'
```

## Monitoring Topics

### Check Robot Status
```bash
# List all topics
ros2 topic list

# Monitor odometry
ros2 topic echo /odom

# Monitor laser scan
ros2 topic echo /scan

# Check camera feed
ros2 topic echo /camera/image_raw

# Monitor twist mux status
ros2 topic echo /cmd_vel
```

### Debugging
```bash
# Check transform tree
ros2 run tf2_tools view_frames

# Monitor joint states
ros2 topic echo /joint_states

# Check robot description
ros2 topic echo /robot_description
```

## Launch Commands

### Full Simulation with All Features
```bash
ros2 launch robot_gazebo simulation_with_teleop.launch.py gui:=true rviz:=true teleop:=true slam:=true
```

### Headless Simulation (No GUI)
```bash
ros2 launch robot_gazebo simulation_with_teleop.launch.py gui:=false rviz:=false teleop:=false slam:=true
```

### Basic Simulation (Minimal)
```bash
ros2 launch robot_gazebo gazebo.launch.py world:=empty.world gui:=true rviz:=true use_config_manager:=false
```

## Robot Physical Configuration

### Front-Wheel Drive Setup
- **Front wheels**: 2 motorized wheels (differential drive)
  - Left motor: `base_front_left_wheel_joint`
  - Right motor: `base_front_right_wheel_joint`
  - Wheel separation: 0.26m
  - Wheel diameter: 0.065m

- **Rear wheels**: 2 passive caster wheels
  - Small spherical casters for stability
  - No motors, just support

### Sensor Placement
- **Camera**: Front of robot on top floor
- **LiDAR**: Center top of robot
- **Base**: Main robot chassis

This configuration provides realistic front-wheel drive behavior similar to many real robots with two drive motors and passive rear support.