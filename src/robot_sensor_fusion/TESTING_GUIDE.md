# Robot Sensor Fusion - Testing Guide

## Overview

This guide provides instructions for testing the Advanced Multi-Modal Sensor Fusion system to validate its functionality and performance.

## Test Levels

### 1. Unit Tests (Standalone)
### 2. Integration Tests (ROS2)
### 3. System Tests (Full Robot)
### 4. Performance Tests

---

## 1. Unit Tests (Standalone)

### Quick Test

Run the standalone test script:

```bash
python3 src/robot_sensor_fusion/test_ekf_standalone.py
```

**Expected Output:**
```
============================================================
Extended Kalman Filter Test Suite
============================================================
Testing initialization...
✓ Initialization test passed

Testing prediction step...
✓ Prediction test passed

...

============================================================
Test Results: 9 passed, 0 failed
============================================================

✓ All tests passed! Sensor fusion system is working correctly.
```

### Individual Test Functions

Test specific functionality:

```python
# Test EKF initialization
from robot_sensor_fusion.extended_kalman_filter import ExtendedKalmanFilter
import numpy as np

ekf = ExtendedKalmanFilter()
state, cov = ekf.get_state()
print(f"Initial state: {state}")
print(f"Initial covariance trace: {np.trace(cov)}")
```

### Test Coverage

The standalone tests cover:
- ✅ EKF initialization
- ✅ Prediction step
- ✅ LiDAR updates
- ✅ Camera updates
- ✅ IMU updates
- ✅ Odometry updates
- ✅ Multi-sensor fusion
- ✅ Sensor reliability weighting
- ✅ Angle normalization
- ✅ Covariance management
- ✅ Static localization accuracy (±2cm)
- ✅ Dynamic localization accuracy (±5cm)
- ✅ Sensor failure handling
- ✅ Single sensor operation
- ✅ Complete fusion pipeline

---

## 2. Integration Tests (ROS2)

### Prerequisites

Ensure ROS2 is sourced:
```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

### Test 1: Node Launch

Test if the node launches correctly:

```bash
# Launch the node
ros2 launch robot_sensor_fusion sensor_fusion.launch.py
```

**Expected Output:**
```
[INFO] [sensor_fusion_node]: Sensor Fusion Node initialized
[INFO] [sensor_fusion_node]: Waiting for sensor data...
```

### Test 2: Topic Publishing

Verify topics are published:

```bash
# In another terminal
ros2 topic list | grep fused

# Expected output:
# /fused_pose
# /fused_velocity
# /sensor_fusion/status
```

### Test 3: Topic Data Flow

Check if data is flowing:

```bash
# Check fused pose
ros2 topic echo /fused_pose --once

# Check sensor status
ros2 topic echo /sensor_fusion/status --once
```

### Test 4: Sensor Input Simulation

Simulate sensor inputs:

```bash
# Publish fake SLAM pose
ros2 topic pub /slam_pose geometry_msgs/PoseStamped \
  "{header: {frame_id: 'map'}, pose: {position: {x: 1.0, y: 2.0, z: 0.0}}}" \
  --once

# Publish fake IMU data
ros2 topic pub /imu sensor_msgs/Imu \
  "{orientation: {w: 1.0, x: 0.0, y: 0.0, z: 0.0}}" \
  --once

# Check if fused pose updates
ros2 topic echo /fused_pose --once
```

### Test 5: Parameter Configuration

Test parameter changes:

```bash
# Get current parameters
ros2 param list /sensor_fusion_node

# Get specific parameter
ros2 param get /sensor_fusion_node update_rate

# Set parameter
ros2 param set /sensor_fusion_node update_rate 25.0
```

### Test 6: Node Information

Verify node configuration:

```bash
# Get node info
ros2 node info /sensor_fusion_node

# Expected output shows:
# - Subscribers: /slam_pose, /imu, /odom, /visual_odometry/pose
# - Publishers: /fused_pose, /fused_velocity, /sensor_fusion/status
# - Parameters: lidar_timeout, camera_timeout, etc.
```

---

## 3. System Tests (Full Robot)

### Test 1: Integration with SLAM

Launch with SLAM system:

```bash
# Terminal 1: Launch robot with SLAM
ros2 launch robot_gazebo complete_robot_simulation.launch.py

# Terminal 2: Launch sensor fusion
ros2 launch robot_sensor_fusion sensor_fusion.launch.py

# Terminal 3: Monitor fusion
ros2 topic echo /fused_pose
```

**Validation:**
- Fused pose should track SLAM pose
- Covariance should decrease over time
- No sensor timeouts in status

### Test 2: Sensor Failure Simulation

Test graceful degradation:

```bash
# Launch sensor fusion
ros2 launch robot_sensor_fusion sensor_fusion.launch.py

# Monitor status
ros2 topic echo /sensor_fusion/status

# Stop publishing to one sensor (simulate failure)
# Observe status message changes to indicate sensor timeout
```

**Expected Behavior:**
- Status shows "Active sensors: imu, odometry" (without lidar)
- Fused pose continues to publish
- Accuracy degrades but system remains stable

### Test 3: Multi-Sensor Accuracy

Compare fused pose with individual sensors:

```bash
# Record data
ros2 bag record /fused_pose /slam_pose /imu /odom -o test_accuracy

# Move robot around
# Stop recording (Ctrl+C)

# Analyze accuracy
ros2 bag play test_accuracy
# Compare fused_pose with slam_pose
```

### Test 4: Dynamic Performance

Test during robot motion:

```bash
# Launch full system
ros2 launch robot_gazebo complete_robot_simulation.launch.py

# Launch sensor fusion
ros2 launch robot_sensor_fusion sensor_fusion.launch.py

# Command robot to move
ros2 topic pub /cmd_vel geometry_msgs/Twist \
  "{linear: {x: 0.5}, angular: {z: 0.2}}" \
  --rate 10

# Monitor fused pose update rate
ros2 topic hz /fused_pose
# Expected: ~50Hz
```

---

## 4. Performance Tests

### Test 1: Update Rate

Measure actual update rate:

```bash
# Launch sensor fusion
ros2 launch robot_sensor_fusion sensor_fusion.launch.py

# Measure rate
ros2 topic hz /fused_pose

# Expected: ~50Hz (±5Hz)
```

### Test 2: Latency

Measure processing latency:

```bash
# Record timestamps
ros2 topic echo /fused_pose | grep stamp

# Compare with input sensor timestamps
ros2 topic echo /slam_pose | grep stamp

# Latency should be <20ms
```

### Test 3: CPU Usage

Monitor CPU usage:

```bash
# Launch sensor fusion
ros2 launch robot_sensor_fusion sensor_fusion.launch.py

# Monitor CPU
top -p $(pgrep -f sensor_fusion_node)

# Expected: <10% CPU on modern hardware
```

### Test 4: Memory Usage

Monitor memory usage:

```bash
# Check memory
ps aux | grep sensor_fusion_node

# Expected: ~10-20MB RSS
```

### Test 5: Accuracy Benchmark

Run accuracy benchmark:

```python
#!/usr/bin/env python3
"""Accuracy benchmark script."""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
import numpy as np

class AccuracyBenchmark(Node):
    def __init__(self):
        super().__init__('accuracy_benchmark')
        self.errors = []
        self.sub = self.create_subscription(
            PoseWithCovarianceStamped,
            '/fused_pose',
            self.callback,
            10
        )
        self.ground_truth = [1.0, 2.0, 0.5]  # Known position
        
    def callback(self, msg):
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        error = np.sqrt((x - self.ground_truth[0])**2 + 
                       (y - self.ground_truth[1])**2)
        self.errors.append(error)
        
        if len(self.errors) >= 100:
            mean_error = np.mean(self.errors)
            std_error = np.std(self.errors)
            print(f"Mean error: {mean_error*100:.2f}cm")
            print(f"Std error: {std_error*100:.2f}cm")
            rclpy.shutdown()

def main():
    rclpy.init()
    node = AccuracyBenchmark()
    rclpy.spin(node)

if __name__ == '__main__':
    main()
```

---

## Test Scenarios

### Scenario 1: Normal Operation

**Setup:**
- All sensors active
- Robot stationary

**Expected Results:**
- Static accuracy: ±2cm
- All sensors in status
- Covariance stable

### Scenario 2: LiDAR Failure

**Setup:**
- Stop LiDAR data
- Continue with IMU + Odometry

**Expected Results:**
- Status shows LiDAR timeout
- Fused pose continues
- Accuracy degrades to ±10cm

### Scenario 3: High-Speed Motion

**Setup:**
- Robot moving at max speed
- All sensors active

**Expected Results:**
- Dynamic accuracy: ±5cm
- Update rate maintained at 50Hz
- No sensor timeouts

### Scenario 4: Sensor Noise

**Setup:**
- Add noise to sensor data
- All sensors active

**Expected Results:**
- Fused pose smoother than individual sensors
- Covariance reflects uncertainty
- No divergence

---

## Validation Checklist

### Functional Tests
- [ ] Node launches without errors
- [ ] All topics published
- [ ] Subscribes to all sensor topics
- [ ] Parameters configurable
- [ ] Graceful shutdown

### Accuracy Tests
- [ ] Static localization ±2cm
- [ ] Dynamic localization ±5cm
- [ ] Orientation accuracy ±0.05rad
- [ ] Covariance realistic

### Robustness Tests
- [ ] Handles sensor failures
- [ ] Recovers from failures
- [ ] No crashes or exceptions
- [ ] Stable long-term operation

### Performance Tests
- [ ] Update rate 50Hz
- [ ] Latency <20ms
- [ ] CPU usage <10%
- [ ] Memory usage <20MB

---

## Troubleshooting Tests

### Issue: No fused pose output

**Test:**
```bash
# Check if node is running
ros2 node list | grep sensor_fusion

# Check subscriptions
ros2 node info /sensor_fusion_node

# Check if sensors are publishing
ros2 topic hz /slam_pose
ros2 topic hz /imu
```

### Issue: Poor accuracy

**Test:**
```bash
# Check sensor status
ros2 topic echo /sensor_fusion/status

# Check covariance
ros2 topic echo /fused_pose | grep covariance

# Verify sensor calibration
```

### Issue: High CPU usage

**Test:**
```bash
# Check update rate
ros2 param get /sensor_fusion_node update_rate

# Reduce if needed
ros2 param set /sensor_fusion_node update_rate 25.0
```

---

## Automated Test Suite

Run all tests automatically:

```bash
#!/bin/bash
# run_all_tests.sh

echo "Running Robot Sensor Fusion Test Suite"
echo "========================================"

# Unit tests
echo "1. Running unit tests..."
python3 src/robot_sensor_fusion/test_ekf_standalone.py
if [ $? -ne 0 ]; then
    echo "❌ Unit tests failed"
    exit 1
fi
echo "✅ Unit tests passed"

# Build test
echo "2. Testing build..."
colcon build --packages-select robot_sensor_fusion
if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi
echo "✅ Build passed"

# ROS2 tests
echo "3. Running ROS2 tests..."
colcon test --packages-select robot_sensor_fusion
if [ $? -ne 0 ]; then
    echo "❌ ROS2 tests failed"
    exit 1
fi
echo "✅ ROS2 tests passed"

echo ""
echo "========================================"
echo "✅ All tests passed!"
echo "========================================"
```

---

## Test Reports

After testing, generate a report:

```bash
# Generate test report
colcon test-result --verbose > test_report.txt

# View report
cat test_report.txt
```

---

## Continuous Testing

For development, set up continuous testing:

```bash
# Watch for changes and re-run tests
while inotifywait -r -e modify src/robot_sensor_fusion/; do
    clear
    python3 src/robot_sensor_fusion/test_ekf_standalone.py
done
```

---

## Conclusion

This testing guide covers all aspects of the sensor fusion system:
- ✅ Unit tests for core functionality
- ✅ Integration tests with ROS2
- ✅ System tests with full robot
- ✅ Performance benchmarks
- ✅ Troubleshooting procedures

For any issues, refer to:
- README.md for usage
- INSTALL.md for setup
- TASK_13_TEST_REPORT.md for validation details
