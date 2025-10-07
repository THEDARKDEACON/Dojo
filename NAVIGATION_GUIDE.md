# Robot Navigation Guide

## 🚗 Your Robot Now Has Caster Wheels!

**Improvements Made:**
- ✅ **Front wheels**: 2 powered drive wheels (like before)
- ✅ **Rear wheels**: 2 small caster wheels (spherical, low friction)
- ✅ **Better turning**: No more dragging wheels, smooth rotation
- ✅ **Navigation ready**: Can set goal poses and navigate autonomously

## 🗺️ Two-Phase Navigation Process

### Phase 1: Build a Map with SLAM

```bash
cd Dojo
source install/setup.bash

# Start simulation with SLAM (mapping mode)
ros2 launch complete_simulation_with_navigation.launch.py slam:=true navigation:=false
```

**What this gives you:**
- Gazebo simulation with your improved robot
- SLAM running to build a map
- RViz showing live map building
- Teleop control to drive around

**Drive around to build the map:**
- Use the teleop window (i/j/l/k keys) to explore
- Watch the map build in RViz as you move
- Cover all areas you want to navigate later
- The map will be saved automatically

### Phase 2: Navigate with Goal Poses

Once you have a good map, switch to navigation mode:

```bash
# Stop the current simulation (Ctrl+C)
# Then start with navigation enabled:
ros2 launch complete_simulation_with_navigation.launch.py slam:=false navigation:=true
```

**What this gives you:**
- Your saved map loaded
- Navigation2 stack running
- Goal pose setting in RViz
- Autonomous path planning and following

## 🎯 How to Set Goal Poses

### Method 1: RViz Goal Tool (Easiest)
1. **Open RViz** (should open automatically)
2. **Click the "2D Goal Pose" tool** in the toolbar
3. **Click and drag** on the map where you want the robot to go
4. **Watch the robot navigate** autonomously to the goal

### Method 2: Command Line
```bash
# Set a goal pose (x, y, orientation)
ros2 topic pub /goal_pose geometry_msgs/PoseStamped '{
  header: {frame_id: "map"},
  pose: {
    position: {x: 2.0, y: 1.0, z: 0.0},
    orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}
  }
}'
```

### Method 3: Navigation2 Action
```bash
# Send a navigation goal using the action interface
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose '{
  pose: {
    header: {frame_id: "map"},
    pose: {
      position: {x: 2.0, y: 1.0, z: 0.0},
      orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}
    }
  }
}'
```

## 📊 Monitor Navigation

### Check Navigation Status
```bash
# See if navigation is active
ros2 topic echo /navigate_to_pose/_action/status

# Monitor the planned path
ros2 topic echo /plan

# Check current robot pose
ros2 topic echo /amcl_pose
```

### In RViz You Can See:
- **Green path**: Planned route to goal
- **Red areas**: Obstacles (costmap)
- **Blue areas**: Free space
- **Robot model**: Current position and orientation
- **Goal marker**: Where you set the target

## 🔧 Navigation Features

### Obstacle Avoidance
- **LiDAR data** creates dynamic obstacle detection
- **Costmaps** show safe vs dangerous areas
- **Path replanning** happens automatically if obstacles appear

### Recovery Behaviors
- **Stuck detection**: Robot knows when it's stuck
- **Backup and retry**: Automatic recovery maneuvers
- **Alternative paths**: Finds new routes around obstacles

### Safety Features
- **Emergency stop**: Safety commands have highest priority
- **Collision avoidance**: Won't hit walls or obstacles
- **Timeout handling**: Cancels impossible goals

## 🎮 Control Priority (Twist Mux)

1. **Safety override** (`/cmd_vel_safety`) - Priority 200 (Highest)
2. **Teleop control** (`/cmd_vel_teleop`) - Priority 100 (Medium)
3. **Navigation** (`/cmd_vel_nav`) - Priority 10 (Lowest)

**This means:**
- You can always override with teleop or safety stop
- Navigation only controls when no higher priority commands are active

## 🗂️ File Locations

**Launch Files:**
- `complete_simulation_with_navigation.launch.py` - Main launch file
- `complete_robot_simulation.launch.py` - SLAM-only version

**Configuration:**
- `src/robot_navigation/config/nav2_params.yaml` - Navigation parameters
- `src/robot_gazebo/config/slam_config.yaml` - SLAM configuration
- `src/robot_gazebo/rviz/navigation_with_map.rviz` - RViz config

**Robot Model:**
- `src/robot_description/urdf/robot.urdf.xacro` - Robot with caster wheels

## 🚀 Quick Start Commands

```bash
# 1. Build a map first
ros2 launch complete_simulation_with_navigation.launch.py

# 2. Drive around with teleop to map the area
# (Use i/j/l/k keys in the teleop window)

# 3. Save the map when done
ros2 run nav2_map_server map_saver_cli -f my_map

# 4. Start navigation mode
ros2 launch complete_simulation_with_navigation.launch.py slam:=false navigation:=true

# 5. Set goals in RViz and watch the robot navigate!
```

Your robot now has smooth turning with caster wheels and full autonomous navigation capabilities! 🎉