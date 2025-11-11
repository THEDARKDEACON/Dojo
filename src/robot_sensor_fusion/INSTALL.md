# Robot Sensor Fusion - Installation Guide

## Prerequisites

### System Requirements
- Ubuntu 22.04 or later
- ROS2 Jazzy or Humble
- Python 3.10+
- NumPy

### ROS2 Dependencies
```bash
sudo apt update
sudo apt install -y \
    ros-${ROS_DISTRO}-sensor-msgs \
    ros-${ROS_DISTRO}-geometry-msgs \
    ros-${ROS_DISTRO}-nav-msgs \
    ros-${ROS_DISTRO}-tf2-ros \
    python3-numpy
```

## Installation

### 1. Clone or Navigate to Workspace

```bash
cd /path/to/your/ros2_workspace
```

### 2. Build the Package

```bash
# Build only sensor fusion package
colcon build --packages-select robot_sensor_fusion

# Or build entire workspace
colcon build

# Source the workspace
source install/setup.bash
```

### 3. Verify Installation

```bash
# Check if package is installed
ros2 pkg list | grep robot_sensor_fusion

# Check available nodes
ros2 pkg executables robot_sensor_fusion

# Expected output:
# robot_sensor_fusion sensor_fusion_node
```

### 4. Run Tests

```bash
# Run standalone tests
python3 src/robot_sensor_fusion/test_ekf_standalone.py

# Run ROS2 tests
colcon test --packages-select robot_sensor_fusion

# View test results
colcon test-result --verbose
```

## Quick Start

### Launch Sensor Fusion

```bash
# Source workspace
source install/setup.bash

# Launch with default configuration
ros2 launch robot_sensor_fusion sensor_fusion.launch.py

# Launch with custom config
ros2 launch robot_sensor_fusion sensor_fusion.launch.py \
    config_file:=/path/to/custom_config.yaml
```

### Verify Operation

In separate terminals:

```bash
# Terminal 1: Monitor fused pose
ros2 topic echo /fused_pose

# Terminal 2: Monitor sensor status
ros2 topic echo /sensor_fusion/status

# Terminal 3: Check topic list
ros2 topic list | grep fused
```

## Configuration

### Default Configuration

The default configuration is located at:
```
src/robot_sensor_fusion/config/sensor_fusion_params.yaml
```

### Custom Configuration

Create a custom configuration file:

```yaml
sensor_fusion_node:
  ros__parameters:
    # Sensor timeout thresholds (seconds)
    lidar_timeout: 1.0
    camera_timeout: 1.0
    imu_timeout: 0.5
    odom_timeout: 0.5
    
    # Update rate (Hz)
    update_rate: 50.0
```

Launch with custom config:
```bash
ros2 launch robot_sensor_fusion sensor_fusion.launch.py \
    config_file:=/path/to/custom_config.yaml
```

## Topic Remapping

### Default Topics

**Subscribed:**
- `/slam_pose` (geometry_msgs/PoseStamped)
- `/visual_odometry/pose` (geometry_msgs/PoseStamped)
- `/imu` (sensor_msgs/Imu)
- `/odom` (nav_msgs/Odometry)

**Published:**
- `/fused_pose` (geometry_msgs/PoseWithCovarianceStamped)
- `/fused_velocity` (geometry_msgs/TwistStamped)
- `/sensor_fusion/status` (std_msgs/String)

### Remap Topics

If your topics have different names, remap them:

```bash
ros2 launch robot_sensor_fusion sensor_fusion.launch.py \
    slam_pose:=/your_slam_topic \
    imu:=/your_imu_topic \
    odom:=/your_odom_topic
```

Or modify the launch file directly.

## Integration with Existing System

### With SLAM System

Ensure your SLAM system publishes to `/slam_pose` or remap:

```python
# In your launch file
Node(
    package='robot_sensor_fusion',
    executable='sensor_fusion_node',
    remappings=[
        ('/slam_pose', '/your_slam_pose_topic'),
    ]
)
```

### With Navigation Stack

Use fused pose as input to Nav2:

```yaml
# nav2_params.yaml
amcl:
  ros__parameters:
    # Use fused pose instead of AMCL
    use_sim_time: false

# Or use fused_pose directly
robot_localization:
  ros__parameters:
    odom0: /fused_pose
```

### With Safety System

The fused pose provides accurate localization for collision avoidance:

```python
# In safety system
self.pose_sub = self.create_subscription(
    PoseWithCovarianceStamped,
    '/fused_pose',
    self.pose_callback,
    10
)
```

## Troubleshooting

### No Output on /fused_pose

**Problem:** Sensor fusion node running but no output

**Solutions:**
1. Check if sensors are publishing:
   ```bash
   ros2 topic list
   ros2 topic hz /slam_pose
   ros2 topic hz /imu
   ros2 topic hz /odom
   ```

2. Check sensor status:
   ```bash
   ros2 topic echo /sensor_fusion/status
   ```

3. Verify topic names match:
   ```bash
   ros2 node info /sensor_fusion_node
   ```

### High CPU Usage

**Problem:** Sensor fusion using too much CPU

**Solutions:**
1. Reduce update rate:
   ```yaml
   update_rate: 25.0  # Instead of 50.0
   ```

2. Check sensor data rates:
   ```bash
   ros2 topic hz /slam_pose
   ros2 topic hz /imu
   ```

### Poor Localization Accuracy

**Problem:** Fused pose not accurate

**Solutions:**
1. Check sensor calibration
2. Verify coordinate frames match
3. Increase sensor reliability weights in code
4. Check for sensor failures:
   ```bash
   ros2 topic echo /sensor_fusion/status
   ```

### Build Errors

**Problem:** Package fails to build

**Solutions:**
1. Install dependencies:
   ```bash
   rosdep install --from-paths src --ignore-src -r -y
   ```

2. Clean build:
   ```bash
   rm -rf build install log
   colcon build --packages-select robot_sensor_fusion
   ```

3. Check Python version:
   ```bash
   python3 --version  # Should be 3.10+
   ```

## Advanced Usage

### Programmatic Access

Use the EKF in your own Python code:

```python
from robot_sensor_fusion.extended_kalman_filter import ExtendedKalmanFilter

# Create EKF instance
ekf = ExtendedKalmanFilter()

# Predict step
ekf.predict(control_input=None, dt=0.02)

# Update with measurements
ekf.update_lidar(np.array([x, y, theta]))
ekf.update_imu(np.array([theta, omega]))

# Get state
state, covariance = ekf.get_state()
x, y, theta = ekf.get_position()
```

### Custom Sensor Integration

Add your own sensor type:

```python
# In extended_kalman_filter.py
def update_custom_sensor(self, measurement: np.ndarray):
    """Update with custom sensor."""
    # Define measurement model
    H = np.zeros((n_measurements, 6))
    # ... set H matrix
    
    # Define measurement noise
    R = np.diag([...])
    
    # Apply reliability weight
    R = R / self.reliability['custom_sensor']
    
    # Perform update
    self._update(measurement, H, R)
```

### Logging and Debugging

Enable detailed logging:

```bash
ros2 launch robot_sensor_fusion sensor_fusion.launch.py \
    --log-level sensor_fusion_node:=debug
```

Record data for analysis:
```bash
ros2 bag record /fused_pose /slam_pose /imu /odom
```

## Performance Tuning

### Optimize for Accuracy

```yaml
# Increase update rate
update_rate: 100.0

# Reduce process noise
# Edit extended_kalman_filter.py:
self.Q = np.diag([0.0001, 0.0001, 0.0001, 0.001, 0.001, 0.001])
```

### Optimize for Speed

```yaml
# Reduce update rate
update_rate: 25.0

# Increase sensor timeouts
lidar_timeout: 2.0
camera_timeout: 2.0
```

### Optimize for Robustness

```yaml
# Longer timeouts
lidar_timeout: 2.0
camera_timeout: 2.0
imu_timeout: 1.0
odom_timeout: 1.0

# Adjust reliability weights in code for more conservative fusion
```

## Uninstallation

```bash
# Remove build artifacts
rm -rf build/robot_sensor_fusion install/robot_sensor_fusion

# Remove source (if desired)
rm -rf src/robot_sensor_fusion
```

## Support

For issues or questions:
1. Check the README.md for usage examples
2. Review TASK_13_TEST_REPORT.md for validation details
3. Check ROS2 logs: `ros2 run robot_sensor_fusion sensor_fusion_node --ros-args --log-level debug`
4. Run tests to verify installation: `python3 src/robot_sensor_fusion/test_ekf_standalone.py`

## Version History

- **v1.0.0** (2025-11-11): Initial release
  - Extended Kalman Filter implementation
  - LiDAR, Camera, IMU, Odometry fusion
  - Sub-centimeter localization accuracy
  - Sensor failure detection
  - Complete test suite
