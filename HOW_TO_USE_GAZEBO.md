# How to Use Your Robot in Gazebo

## 🚗 Your Front-Wheel Drive Robot is Ready!

Your robot now has:
- ✅ **2 powered front wheels** (like a front-wheel drive car)
- ✅ **2 unpowered rear wheels** (get dragged along)
- ✅ **Camera sensor** (publishes to `/camera/image_raw`)
- ✅ **LiDAR sensor** (publishes to `/scan`)
- ✅ **Differential drive control** (responds to `/cmd_vel`)

## 🎮 Launch Options

### Option 1: Complete Simulation (Recommended)
```bash
source install/setup.bash
ros2 launch complete_robot_simulation.launch.py
```
**This gives you:**
- Gazebo GUI (see your robot)
- RViz (see sensor data and maps)
- Teleop keyboard control
- SLAM mapping
- All sensor feeds

### Option 2: Minimal Working Simulation
```bash
source install/setup.bash
ros2 launch minimal_robot_test.launch.py
```
**This gives you:**
- Headless Gazebo (no GUI, but physics works)
- Robot movement testing
- All topics working

### Option 3: Fixed Gazebo Launch
```bash
source install/setup.bash
ros2 launch robot_gazebo gazebo.launch.py gui:=true rviz:=true
```
**This gives you:**
- Fixed Gazebo startup (should work now)
- Gazebo GUI + RViz
- Basic robot simulation

## 🎯 How to Control Your Robot

### Method 1: Teleop Keyboard (Easiest)
When you launch the complete simulation, a terminal window will open with teleop controls:
```
i - move forward
, - move backward  
j - turn left
l - turn right
k - stop
```

### Method 2: Direct Commands
In a new terminal:
```bash
source install/setup.bash

# Move forward
ros2 topic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0.3}, angular: {z: 0.0}}'

# Turn left while moving
ros2 topic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0.2}, angular: {z: 0.5}}'

# Stop
ros2 topic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0.0}, angular: {z: 0.0}}'
```

### Method 3: Through Twist Mux (Priority-based)
```bash
# Teleop control (medium priority)
ros2 topic pub /cmd_vel_teleop geometry_msgs/Twist '{linear: {x: 0.2}, angular: {z: 0.0}}'

# Safety override (highest priority)
ros2 topic pub /cmd_vel_safety geometry_msgs/Twist '{linear: {x: 0.0}, angular: {z: 0.0}}'
```

## 📊 Monitor Your Robot

### Check Robot Status
```bash
# Watch the robot move (odometry)
ros2 topic echo /odom

# See what the camera sees
ros2 topic echo /camera/image_raw

# Monitor LiDAR data
ros2 topic echo /scan

# List all available topics
ros2 topic list
```

### In RViz You Can See:
- **Robot Model**: Your green robot with 4 wheels
- **Camera Feed**: Live camera view
- **LiDAR Data**: Red dots showing laser scan
- **Map Building**: As you drive around, SLAM builds a map
- **Odometry**: Robot's path and position

## 🗺️ Build Maps with SLAM

1. **Launch the complete simulation**
2. **Drive the robot around** using teleop (i, j, l, k keys)
3. **Watch the map build** in RViz as you explore
4. **The LiDAR data** creates the map automatically

## 🔧 Troubleshooting

### If Gazebo doesn't start:
```bash
# Kill any existing Gazebo processes
pkill -f gazebo

# Try the minimal test first
ros2 launch minimal_robot_test.launch.py
```

### If robot doesn't move:
```bash
# Check if differential drive is working
ros2 topic list | grep cmd_vel
ros2 topic echo /odom

# Test direct movement
ros2 topic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0.2}, angular: {z: 0.0}}' --once
```

### If no camera/LiDAR data:
```bash
# Check sensor topics
ros2 topic list | grep -E "(camera|scan)"
ros2 topic hz /camera/image_raw
ros2 topic hz /scan
```

## 🎉 What You Can Do Now

1. **Drive your robot** around in Gazebo
2. **See the camera feed** in RViz
3. **Watch LiDAR data** create maps
4. **Build maps** of the environment
5. **Control with keyboard** or commands
6. **Monitor all sensors** in real-time

Your front-wheel drive robot is now fully functional in Gazebo! 🚗✨