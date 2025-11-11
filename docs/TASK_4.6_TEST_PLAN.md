# Task 4.6 Test Plan - Dashboard Testing and Validation

## Overview
This document provides a comprehensive test plan for validating the Performance Dashboard under various operational scenarios. The tests verify functionality, accuracy, and performance under normal and stress conditions.

## Test Environment

### Prerequisites
```bash
# Ensure system is built
colcon build --packages-select robot_semantic_slam

# Source workspace
source install/setup.bash

# Install stress testing tools (if not already installed)
sudo apt-get install stress-ng htop
```

### Test Configuration
- **ROS2 Distribution**: Jazzy
- **Gazebo**: Harmonic
- **Update Rate**: 1 Hz (default)
- **Test Duration**: 5-10 minutes per scenario

## Test Scenarios

### Test 1: Normal Operation

**Objective**: Verify dashboard functions correctly under normal operating conditions

**Setup:**
```bash
# Launch full system
python3 start_cutting_edge_robot.py
```

**Test Steps:**
1. Launch the robot system
2. Open RViz and add MarkerArray display for `/performance_dashboard`
3. Observe dashboard for 5 minutes
4. Monitor `/performance_metrics_json` topic

**Expected Results:**
- ✅ Dashboard visible at position (5, 5, 2)
- ✅ All sections displayed (System Health, Navigation, Perception, Safety)
- ✅ CPU usage: 30-60%
- ✅ Memory usage: 40-70%
- ✅ Network bandwidth: 1-5 Mbps
- ✅ No alerts generated
- ✅ Progress bars update smoothly
- ✅ Text markers readable and properly positioned

**Validation Commands:**
```bash
# Check dashboard is publishing
ros2 topic hz /performance_dashboard

# View metrics
ros2 topic echo /performance_metrics_json --once

# Verify no alerts
ros2 topic echo /performance_alerts --once
```

**Success Criteria:**
- [ ] Dashboard renders without errors
- [ ] All metrics within normal ranges
- [ ] Update rate stable at ~1 Hz
- [ ] No visual artifacts or overlapping text

---

### Test 2: High CPU Load (Stress Test)

**Objective**: Verify alert system triggers correctly under high CPU load

**Setup:**
```bash
# Launch system
python3 start_cutting_edge_robot.py

# In separate terminal, monitor CPU
htop
```

**Test Steps:**
1. Observe baseline CPU usage
2. Start CPU stress test:
   ```bash
   stress-ng --cpu 4 --timeout 60s
   ```
3. Monitor dashboard for alert indicators
4. Observe alert clearance after stress ends

**Expected Results:**
- ✅ CPU usage rises to 80%+ (WARNING alert)
- ✅ CPU usage may reach 90%+ (CRITICAL alert)
- ✅ Orange/red progress bar for CPU
- ✅ Alert beacon appears above dashboard
- ✅ Alert banner shows "⚠️ ALERT(S) ACTIVE" or "🚨 CRITICAL ALERT"
- ✅ Console logs show warning/error messages
- ✅ `/performance_alerts` topic publishes alerts
- ✅ Alerts clear when CPU load returns to normal

**Validation Commands:**
```bash
# Monitor alerts in real-time
ros2 topic echo /performance_alerts

# Check CPU metric
ros2 topic echo /performance_metrics_json | grep cpu_usage

# View logs
ros2 log list | grep performance_dashboard
```

**Success Criteria:**
- [ ] WARNING alert triggers at 80% CPU
- [ ] CRITICAL alert triggers at 90% CPU
- [ ] Visual indicators appear in RViz
- [ ] Alerts logged to console
- [ ] Alerts clear when load reduces
- [ ] No false positives after clearance

**Test Results Template:**
```
Test Start Time: ___________
Baseline CPU: ____%
Peak CPU: ____%
WARNING Alert Time: ___________
CRITICAL Alert Time: ___________
Alert Clear Time: ___________
Visual Indicators: [ ] Beacon [ ] Banner [ ] Details
Console Logs: [ ] WARNING [ ] CRITICAL
Test Status: [ ] PASS [ ] FAIL
Notes: _____________________
```

---

### Test 3: High Memory Usage

**Objective**: Verify memory monitoring and alerts

**Setup:**
```bash
# Launch system
python3 start_cutting_edge_robot.py
```

**Test Steps:**
1. Observe baseline memory usage
2. Create memory pressure:
   ```bash
   # Allocate memory (adjust size based on available RAM)
   stress-ng --vm 2 --vm-bytes 2G --timeout 60s
   ```
3. Monitor dashboard for memory alerts
4. Observe alert clearance

**Expected Results:**
- ✅ Memory usage rises above 80% (WARNING)
- ✅ Orange/red progress bar for Memory
- ✅ Alert indicators appear
- ✅ Alerts published and logged
- ✅ Alerts clear when memory freed

**Validation Commands:**
```bash
# Monitor memory
free -h
watch -n 1 free -h

# Check memory metric
ros2 topic echo /performance_metrics_json | grep memory_usage
```

**Success Criteria:**
- [ ] Memory alerts trigger correctly
- [ ] Visual indicators match alert level
- [ ] Memory value accurate (±5%)
- [ ] Alerts clear appropriately

---

### Test 4: Many Detected Objects (100+)

**Objective**: Verify dashboard handles high object detection rates

**Setup:**
```bash
# Launch system in a world with many objects
ros2 launch robot_gazebo gazebo.launch.py world:=warehouse.world

# Launch semantic SLAM
ros2 launch robot_semantic_slam semantic_slam.launch.py

# Launch dashboard
ros2 launch robot_semantic_slam performance_dashboard.launch.py
```

**Test Steps:**
1. Navigate robot through environment
2. Allow YOLO to detect many objects
3. Monitor detection rate metric
4. Observe objects detected count
5. Check for performance degradation

**Expected Results:**
- ✅ Objects detected count increases
- ✅ Detection rate shows objects/second
- ✅ Dashboard remains responsive
- ✅ No lag in visualization
- ✅ Metrics update at 1 Hz consistently

**Validation Commands:**
```bash
# Monitor semantic map
ros2 topic echo /semantic_map | grep -c "class"

# Check detection metrics
ros2 topic echo /performance_metrics_json | grep -E "objects_detected|detection_rate"

# Monitor dashboard update rate
ros2 topic hz /performance_dashboard
```

**Success Criteria:**
- [ ] Handles 100+ objects without errors
- [ ] Detection rate calculated correctly
- [ ] Dashboard update rate stable
- [ ] No memory leaks over time
- [ ] Visual performance acceptable

**Performance Benchmarks:**
| Metric | Target | Actual |
|--------|--------|--------|
| Objects Detected | 100+ | ___ |
| Detection Rate | 1-10/s | ___ |
| Dashboard Hz | ~1 Hz | ___ |
| CPU Impact | <5% | ___ |
| Memory Impact | <100 MB | ___ |

---

### Test 5: Metric Accuracy Validation

**Objective**: Validate dashboard metrics against ground truth

**Setup:**
```bash
# Launch system
python3 start_cutting_edge_robot.py
```

**Test Steps:**

#### 5.1 CPU Usage Accuracy
```bash
# Compare dashboard CPU vs system CPU
# Dashboard:
ros2 topic echo /performance_metrics_json | grep cpu_usage

# Ground truth:
top -bn1 | grep "Cpu(s)"
# or
mpstat 1 1
```

**Expected**: Dashboard CPU within ±5% of system measurement

#### 5.2 Memory Usage Accuracy
```bash
# Dashboard:
ros2 topic echo /performance_metrics_json | grep memory_usage

# Ground truth:
free -h
# Calculate: (used / total) * 100
```

**Expected**: Dashboard memory within ±3% of system measurement

#### 5.3 Network Bandwidth Accuracy
```bash
# Dashboard:
ros2 topic echo /performance_metrics_json | grep network_bandwidth

# Ground truth:
iftop -t -s 10
# or
nload -u M
```

**Expected**: Dashboard bandwidth within ±10% of system measurement

#### 5.4 Detection Rate Accuracy
```bash
# Count detections manually over 10 seconds
ros2 topic echo /semantic_map --once | grep -c "class"
# Wait 10 seconds
ros2 topic echo /semantic_map --once | grep -c "class"
# Calculate: (new_count - old_count) / 10

# Compare to dashboard:
ros2 topic echo /performance_metrics_json | grep detection_rate
```

**Expected**: Dashboard rate matches manual count (±0.5/s)

#### 5.5 Mapping Coverage Accuracy
```bash
# Dashboard:
ros2 topic echo /performance_metrics_json | grep mapping_coverage

# Ground truth:
ros2 topic echo /map --once
# Count known cells (value != -1) vs total cells
```

**Expected**: Dashboard coverage matches calculation (±2%)

**Validation Results Template:**
```
Metric: CPU Usage
Dashboard Value: ____%
Ground Truth: ____%
Difference: ____%
Status: [ ] PASS (±5%) [ ] FAIL

Metric: Memory Usage
Dashboard Value: ____%
Ground Truth: ____%
Difference: ____%
Status: [ ] PASS (±3%) [ ] FAIL

Metric: Network Bandwidth
Dashboard Value: ___ Mbps
Ground Truth: ___ Mbps
Difference: ____%
Status: [ ] PASS (±10%) [ ] FAIL

Metric: Detection Rate
Dashboard Value: ___/s
Ground Truth: ___/s
Difference: ___/s
Status: [ ] PASS (±0.5/s) [ ] FAIL

Metric: Mapping Coverage
Dashboard Value: ____%
Ground Truth: ____%
Difference: ____%
Status: [ ] PASS (±2%) [ ] FAIL
```

---

### Test 6: Long-Running Stability

**Objective**: Verify dashboard stability over extended operation

**Setup:**
```bash
# Launch system
python3 start_cutting_edge_robot.py
```

**Test Steps:**
1. Run system for 1 hour
2. Monitor for memory leaks
3. Check for visualization degradation
4. Verify consistent update rate

**Expected Results:**
- ✅ No memory growth over time
- ✅ Update rate remains stable
- ✅ No marker accumulation
- ✅ No performance degradation

**Validation Commands:**
```bash
# Monitor memory over time
watch -n 60 "ps aux | grep performance_dashboard | grep -v grep"

# Log metrics for analysis
ros2 topic echo /performance_metrics_json >> metrics_log.json

# Check update rate periodically
ros2 topic hz /performance_dashboard
```

**Success Criteria:**
- [ ] Memory usage stable (±10 MB)
- [ ] Update rate stable (±0.1 Hz)
- [ ] No crashes or errors
- [ ] Visual quality maintained

---

### Test 7: Alert System Validation

**Objective**: Comprehensive alert system testing

**Test Steps:**

#### 7.1 Alert Triggering
```bash
# Trigger CPU alert
stress-ng --cpu 4 --timeout 30s

# Verify alert appears
ros2 topic echo /performance_alerts
```

#### 7.2 Alert Levels
- Verify WARNING at 80% threshold
- Verify CRITICAL at 90% threshold
- Verify correct color coding

#### 7.3 Alert Clearance
- Verify alerts clear when metric returns to normal
- Verify visual indicators disappear
- Verify no lingering alerts

#### 7.4 Multiple Simultaneous Alerts
```bash
# Trigger both CPU and memory alerts
stress-ng --cpu 4 --vm 2 --vm-bytes 2G --timeout 30s

# Verify both alerts shown
ros2 topic echo /performance_alerts
```

#### 7.5 Alert Logging
```bash
# Check logs contain alerts
ros2 log list | grep performance_dashboard

# Verify log levels (WARN, ERROR)
# Verify emoji indicators present
```

**Success Criteria:**
- [ ] All alert types trigger correctly
- [ ] Alert levels accurate
- [ ] Multiple alerts handled
- [ ] Alerts clear properly
- [ ] Logging complete and accurate

---

## Test Execution Checklist

### Pre-Test
- [ ] System built successfully
- [ ] All dependencies installed
- [ ] Test tools available (stress-ng, htop)
- [ ] RViz configured with MarkerArray display
- [ ] Baseline metrics recorded

### During Test
- [ ] Test 1: Normal Operation - PASS/FAIL
- [ ] Test 2: High CPU Load - PASS/FAIL
- [ ] Test 3: High Memory Usage - PASS/FAIL
- [ ] Test 4: Many Objects (100+) - PASS/FAIL
- [ ] Test 5: Metric Accuracy - PASS/FAIL
- [ ] Test 6: Long-Running Stability - PASS/FAIL
- [ ] Test 7: Alert System - PASS/FAIL

### Post-Test
- [ ] All tests documented
- [ ] Issues logged
- [ ] Performance data collected
- [ ] Test report generated

## Known Issues and Limitations

### Current Limitations
1. **Network Bandwidth**: May show spikes during topic bursts
2. **Detection Rate**: Depends on YOLO performance and scene complexity
3. **Mapping Coverage**: Accuracy depends on map resolution

### Acceptable Tolerances
- CPU/Memory: ±5%
- Network: ±10%
- Detection Rate: ±0.5/s
- Mapping Coverage: ±2%

## Test Results Summary

**Test Date**: ___________
**Tester**: ___________
**System Version**: ___________

| Test | Status | Notes |
|------|--------|-------|
| 1. Normal Operation | ⬜ PASS ⬜ FAIL | |
| 2. High CPU Load | ⬜ PASS ⬜ FAIL | |
| 3. High Memory Usage | ⬜ PASS ⬜ FAIL | |
| 4. Many Objects | ⬜ PASS ⬜ FAIL | |
| 5. Metric Accuracy | ⬜ PASS ⬜ FAIL | |
| 6. Long-Running | ⬜ PASS ⬜ FAIL | |
| 7. Alert System | ⬜ PASS ⬜ FAIL | |

**Overall Status**: ⬜ ALL PASS ⬜ SOME FAIL

**Issues Found**: ___________

**Recommendations**: ___________

## Automated Testing Script

```bash
#!/bin/bash
# dashboard_test.sh - Automated dashboard testing

echo "=== Performance Dashboard Test Suite ==="
echo "Starting tests at $(date)"

# Test 1: Normal Operation
echo "Test 1: Normal Operation"
timeout 60s ros2 topic hz /performance_dashboard
if [ $? -eq 0 ]; then
    echo "✓ Test 1 PASS"
else
    echo "✗ Test 1 FAIL"
fi

# Test 2: CPU Stress
echo "Test 2: CPU Stress Test"
stress-ng --cpu 4 --timeout 30s &
sleep 5
ALERTS=$(ros2 topic echo /performance_alerts --once 2>/dev/null)
if [[ $ALERTS == *"CPU"* ]]; then
    echo "✓ Test 2 PASS - CPU alert triggered"
else
    echo "✗ Test 2 FAIL - No CPU alert"
fi
wait

# Test 3: Metric Accuracy
echo "Test 3: Metric Accuracy"
DASH_CPU=$(ros2 topic echo /performance_metrics_json --once | grep -oP '"cpu_usage":\s*\K[0-9.]+')
SYS_CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
echo "Dashboard CPU: $DASH_CPU%, System CPU: $SYS_CPU%"

echo "=== Tests Complete at $(date) ==="
```

## Conclusion

This test plan provides comprehensive validation of the Performance Dashboard across multiple scenarios. Execute all tests and document results to ensure the dashboard meets all requirements and performs reliably under various conditions.

## Related Documentation

- [Performance Dashboard Guide](PERFORMANCE_DASHBOARD.md)
- [Task 4.2 Summary](TASK_4.2_SUMMARY.md)
- [Task 4.5 Summary](TASK_4.5_SUMMARY.md) - Alert System
