# Robot Sensor Fusion

Advanced multi-modal sensor fusion package for robot localization using Extended Kalman Filter (EKF).

## Overview

This package fuses data from multiple sensors to provide accurate, robust localization:

- **LiDAR**: Position estimates from SLAM (reliability: 0.9)
- **Camera**: Visual odometry estimates (reliability: 0.7)
- **IMU**: Orientation and angular velocity (reliability: 0.8)
- **Wheel Odometry**: Velocity estimates (reliability: 0.6)

The EKF combines these measurements with appropriate weighting based on sensor reliability, providing sub-centimeter localization accuracy in optimal conditions.

## Features

- **Extended Kalman Filter**: 6-DOF state estimation [x, y, θ, vx, vy, ω]
- **Sensor Failure Detection**: Automatic timeout detection and graceful degradation
- **Adaptive Reliability**: Adjusts sensor weights based on availability
- **Real-time Performance**: 50Hz update rate
- **Covariance Estimation**: Provides uncertainty estimates for downstream systems

## State Vector

The filter maintains a 6-dimensional state:

```
[x, y, θ, vx, vy, ω]
```

Where:
- `x, y`: Position in map frame (meters)
- `θ`: Orientation/yaw (radians)
- `vx, vy`: Linear velocities (m/s)
- `ω`: Angular velocity (rad/s)

## Topics

### Subscribed Topics

- `/slam_pose` (geometry_msgs/PoseStamped): LiDAR SLAM pose estimates
- `/visual_odometry/pose` (geometry_msgs/PoseStamped): Camera visual odometry
- `/imu` (sensor_msgs/Imu): IMU measurements
- `/odom` (nav_msgs/Odometry): Wheel odometry

### Published Topics

- `/fused_pose` (geometry_msgs/PoseWithCovarianceStamped): Fused pose estimate with covariance
- `/fused_velocity` (geometry_msgs/TwistStamped): Fused velocity estimate
- `/sensor_fusion/status` (std_msgs/String): Active sensor status

## Parameters

- `lidar_timeout` (float, default: 1.0): LiDAR timeout threshold (seconds)
- `camera_timeout` (float, default: 1.0): Camera timeout threshold (seconds)
- `imu_timeout` (float, default: 0.5): IMU timeout threshold (seconds)
- `odom_timeout` (float, default: 0.5): Odometry timeout threshold (seconds)
- `update_rate` (float, default: 50.0): Filter update rate (Hz)

## Usage

### Launch Sensor Fusion

```bash
ros2 launch robot_sensor_fusion sensor_fusion.launch.py
```

### With Custom Configuration

```bash
ros2 launch robot_sensor_fusion sensor_fusion.launch.py config_file:=/path/to/config.yaml
```

### Monitor Fused Pose

```bash
ros2 topic echo /fused_pose
```

### Check Sensor Status

```bash
ros2 topic echo /sensor_fusion/status
```

## Performance

### Target Accuracy

- **Static localization**: ±2cm position accuracy
- **Dynamic localization**: ±5cm position accuracy at maximum speed
- **Update rate**: 50Hz
- **Latency**: <20ms

### Sensor Failure Handling

The system continues to operate with degraded performance when sensors fail:

- **All sensors active**: Optimal accuracy (±2cm)
- **LiDAR only**: Good accuracy (±5cm)
- **IMU + Odometry**: Moderate accuracy (±10cm, drift over time)
- **Single sensor**: Degraded accuracy, warnings issued

## Integration

### With Navigation Stack

The fused pose can be used as input to Nav2:

```yaml
# nav2_params.yaml
robot_base_frame: base_link
global_frame: map
odom_topic: /fused_pose  # Use fused estimate
```

### With SLAM

The sensor fusion can run alongside SLAM, providing a more accurate pose estimate:

```
SLAM → /slam_pose → Sensor Fusion → /fused_pose → Navigation
```

## Development

### Building

```bash
cd /path/to/workspace
colcon build --packages-select robot_sensor_fusion
source install/setup.bash
```

### Testing

```bash
# Run unit tests
colcon test --packages-select robot_sensor_fusion

# View test results
colcon test-result --verbose
```

## Algorithm Details

### Extended Kalman Filter

The EKF operates in two steps:

1. **Prediction**: Uses motion model to predict next state
   ```
   x_k = f(x_{k-1}, u_k) + w_k
   P_k = F P_{k-1} F^T + Q
   ```

2. **Update**: Corrects prediction using sensor measurements
   ```
   K = P H^T (H P H^T + R)^{-1}
   x_k = x_k + K(z_k - h(x_k))
   P_k = (I - K H) P_k
   ```

### Sensor Reliability Weighting

Measurement noise covariance is adjusted by reliability:

```
R_adjusted = R_base / reliability
```

Lower reliability increases measurement noise, reducing the sensor's influence on the estimate.

## Troubleshooting

### No Fused Pose Output

- Check that at least one sensor is publishing data
- Verify topic names match configuration
- Check sensor timeout parameters

### Poor Localization Accuracy

- Verify sensor calibration
- Check for sensor failures in status topic
- Increase update rate if needed
- Verify coordinate frame transformations

### High CPU Usage

- Reduce update rate
- Check for excessive sensor data rates
- Profile with `ros2 run` profiling tools

## References

- Thrun, S., Burgard, W., & Fox, D. (2005). Probabilistic Robotics. MIT Press.
- Kalman, R. E. (1960). A New Approach to Linear Filtering and Prediction Problems.
