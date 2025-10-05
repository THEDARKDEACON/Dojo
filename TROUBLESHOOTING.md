# Dojo Robot Troubleshooting Guide

This guide provides detailed troubleshooting procedures for the Dojo Robot's hardware discovery, safety systems, and configuration management features.

## Table of Contents

1. [Hardware Discovery Issues](#hardware-discovery-issues)
2. [Safety System Problems](#safety-system-problems)
3. [Configuration Management Issues](#configuration-management-issues)
4. [Build and Dependency Problems](#build-and-dependency-problems)
5. [Performance and Monitoring](#performance-and-monitoring)
6. [Emergency Procedures](#emergency-procedures)

## Hardware Discovery Issues

### Arduino Auto-Discovery Problems

#### Symptom: Arduino not detected during hardware discovery

**Diagnostic Steps:**
```bash
# 1. Check hardware discovery status
ros2 topic echo /hardware_discovery_status

# 2. List available serial devices
ls -la /dev/tty{ACM,USB}*

# 3. Check USB permissions
groups $USER | grep dialout

# 4. Test manual Arduino connection
ros2 run robot_control arduino_bridge --port /dev/ttyACM0 --test
```

**Common Causes and Solutions:**

1. **USB Permission Issues**
   ```bash
   # Add user to dialout group
   sudo usermod -a -G dialout $USER
   # Logout and login again, or restart
   ```

2. **Wrong Arduino Firmware**
   - Ensure ROSArduinoBridge firmware is loaded on Arduino
   - Check firmware version compatibility
   ```bash
   # Upload correct firmware
   arduino-cli compile --fqbn arduino:avr:uno firmware/arduino/ROSArduinoBridge/
   arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno firmware/arduino/ROSArduinoBridge/
   ```

3. **USB Cable Issues**
   - Try different USB cable (ensure data transfer capability)
   - Test with different USB port
   - Check cable connection integrity

4. **Device Conflict**
   ```bash
   # Check if device is in use by another process
   sudo lsof /dev/ttyACM0
   
   # Kill conflicting processes if found
   sudo pkill -f "ttyACM0"
   ```

#### Symptom: Arduino connects but communication fails

**Diagnostic Steps:**
```bash
# 1. Check Arduino status
ros2 topic echo /arduino_status

# 2. Monitor raw serial communication
ros2 run robot_control arduino_bridge --debug --port /dev/ttyACM0

# 3. Test baud rate settings
ros2 param get /arduino_driver baud_rate
```

**Solutions:**
1. **Baud Rate Mismatch**
   - Verify Arduino firmware baud rate matches configuration
   - Default should be 115200
   
2. **Communication Timeout**
   - Increase timeout in configuration
   - Check for electromagnetic interference

3. **Hardware Reset Issues**
   - Add delay after connection establishment
   - Check Arduino power supply stability

### Camera Auto-Discovery Problems

#### Symptom: Camera not detected or wrong capabilities reported

**Diagnostic Steps:**
```bash
# 1. List video devices
ls -la /dev/video*

# 2. Check camera capabilities
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --list-formats-ext

# 3. Test camera discovery
ros2 run robot_control camera_driver --test-capabilities

# 4. Check camera status
ros2 topic echo /camera_status
```

**Common Solutions:**

1. **Video Device Permissions**
   ```bash
   # Add user to video group
   sudo usermod -a -G video $USER
   ```

2. **Multiple Camera Devices**
   - Some cameras create multiple `/dev/video*` devices
   - Discovery system automatically selects the correct one
   - Manual override available in configuration

3. **Unsupported Camera Format**
   - Check supported formats with `v4l2-ctl`
   - Update camera configuration for supported format
   - Common formats: MJPEG, YUYV

4. **USB Bandwidth Issues**
   - Lower resolution or frame rate
   - Use USB 3.0 port for high-resolution cameras
   - Check USB hub power delivery

#### Symptom: Camera detected but no image data

**Diagnostic Steps:**
```bash
# 1. Test camera directly
ros2 run robot_control camera_driver --test-stream

# 2. Check image topics
ros2 topic list | grep image
ros2 topic hz /image_raw

# 3. Monitor camera health
ros2 topic echo /camera_status
```

**Solutions:**
1. **Driver Configuration Issues**
   - Verify camera parameters in configuration
   - Check resolution and format compatibility
   
2. **USB Power Issues**
   - Use powered USB hub
   - Check cable quality and length

### LiDAR Auto-Discovery Problems

#### Symptom: LiDAR not detected during discovery

**Diagnostic Steps:**
```bash
# 1. Check serial devices
ls -la /dev/ttyUSB*

# 2. Test LiDAR communication
ros2 run robot_control lidar_driver --test-connection

# 3. Check LiDAR status
ros2 topic echo /lidar_status

# 4. Monitor discovery process
ros2 topic echo /hardware_discovery_status | grep -i lidar
```

**Common Solutions:**

1. **Power Supply Issues**
   - LiDAR requires 5V, 1.5A minimum
   - Use external power adapter if needed
   - Check power LED on LiDAR unit

2. **USB-Serial Converter Issues**
   - Some LiDAR units use specific USB-serial chips
   - Install appropriate drivers (CP210x, FTDI, etc.)
   ```bash
   # Check USB device recognition
   lsusb | grep -i "serial\|cp210\|ftdi"
   ```

3. **Communication Protocol Mismatch**
   - Verify LiDAR model compatibility
   - Check baud rate settings (usually 115200 or 256000)

#### Symptom: LiDAR detected but not spinning or no scan data

**Diagnostic Steps:**
```bash
# 1. Check scan data
ros2 topic echo /scan --once

# 2. Monitor LiDAR health
ros2 topic echo /lidar_status

# 3. Check motor control
ros2 run robot_control lidar_driver --test-motor
```

**Solutions:**
1. **Motor Power Issues**
   - Check motor power supply (usually 5V)
   - Verify motor control signal

2. **Scan Frequency Configuration**
   - Adjust scan frequency in configuration
   - Some models have specific frequency requirements

## Safety System Problems

### Emergency Stop Issues

#### Symptom: Emergency stop not activating when triggered

**Diagnostic Steps:**
```bash
# 1. Check safety supervisor status
ros2 topic echo /safety_status

# 2. Test emergency stop trigger
ros2 topic pub /emergency_stop_request std_msgs/Bool "data: true"

# 3. Monitor emergency stop status
ros2 topic echo /emergency_stop_status

# 4. Check safety violations
ros2 topic echo /safety_violations
```

**Solutions:**
1. **Safety Supervisor Not Running**
   ```bash
   # Check if safety supervisor is active
   ros2 node list | grep safety_supervisor
   
   # Restart safety system
   ros2 launch robot_control safety_system.launch.py
   ```

2. **Component Not Responding to Emergency Stop**
   - Check component integration with safety system
   - Verify emergency stop callback implementation
   - Test individual component emergency stop response

3. **Safety Configuration Issues**
   - Verify safety parameters in master configuration
   - Check emergency stop timeout settings

#### Symptom: Cannot clear emergency stop

**Diagnostic Steps:**
```bash
# 1. Check current safety status
ros2 topic echo /safety_status

# 2. View active safety violations
ros2 topic echo /safety_violations

# 3. Attempt to clear emergency stop
ros2 service call /clear_emergency_stop std_srvs/Trigger
```

**Solutions:**
1. **Active Safety Violations**
   - Resolve all safety violations before clearing
   - Check obstacle detection, hardware errors, etc.

2. **Manual Confirmation Required**
   - Emergency stop clearing requires explicit operator confirmation
   - Use service call, not topic publication

3. **Hardware Still in Error State**
   - Check hardware status of all components
   - Ensure all devices are healthy before clearing

### Watchdog Timer Issues

#### Symptom: Frequent watchdog timeouts

**Diagnostic Steps:**
```bash
# 1. Check watchdog status
ros2 topic echo /watchdog_status

# 2. Monitor component health
ros2 topic echo /component_health

# 3. Check system performance
htop
ros2 run rqt_top rqt_top
```

**Solutions:**
1. **System Performance Issues**
   - Check CPU and memory usage
   - Reduce system load
   - Optimize node performance

2. **Network Latency**
   - Check network connectivity
   - Reduce message rates if needed
   - Use local communication when possible

3. **Component Hanging**
   - Identify hanging components
   - Restart problematic nodes
   - Check for deadlocks or infinite loops

#### Symptom: Watchdog not detecting actual failures

**Diagnostic Steps:**
```bash
# 1. Check watchdog configuration
ros2 param list | grep watchdog

# 2. Test watchdog sensitivity
ros2 run robot_control watchdog_system --test

# 3. Monitor watchdog intervals
ros2 topic echo /watchdog_status --field data
```

**Solutions:**
1. **Watchdog Interval Too Long**
   - Reduce watchdog interval in configuration
   - Balance between sensitivity and false positives

2. **Component Not Sending Heartbeats**
   - Verify component watchdog integration
   - Check heartbeat message publication

### Velocity Limiting Issues

#### Symptom: Robot moving too slowly or commands ignored

**Diagnostic Steps:**
```bash
# 1. Compare input and filtered commands
ros2 topic echo /cmd_vel &
ros2 topic echo /cmd_vel_filtered

# 2. Check velocity limits
ros2 param get /safety_supervisor max_linear_velocity
ros2 param get /safety_supervisor max_angular_velocity

# 3. Check safety status
ros2 topic echo /safety_status
```

**Solutions:**
1. **Velocity Limits Too Restrictive**
   - Adjust velocity limits in configuration
   - Consider safety requirements vs. performance needs

2. **Safety System Active**
   - Check for active safety violations
   - Resolve obstacle detection or hardware issues

3. **Command Timeout**
   - Increase command timeout if needed
   - Ensure continuous command publication

## Configuration Management Issues

### Configuration Validation Failures

#### Symptom: System fails to start due to configuration errors

**Diagnostic Steps:**
```bash
# 1. Run configuration validation
ros2 run robot_control configuration_manager --validate

# 2. Check validation report
ros2 topic echo /configuration_validation_report

# 3. Check for conflicts
ros2 topic echo /configuration_conflicts
```

**Solutions:**
1. **Parameter Conflicts**
   - Review conflicting parameters in validation report
   - Ensure consistency across configuration sections
   - Use master configuration as single source of truth

2. **Invalid Parameter Values**
   - Check parameter ranges and types
   - Verify physical parameter accuracy (wheel base, radius, etc.)

3. **Missing Required Parameters**
   - Add missing parameters to master configuration
   - Check parameter schema requirements

### Parameter Propagation Issues

#### Symptom: Changes to master config not reflected in components

**Diagnostic Steps:**
```bash
# 1. Check parameter propagation status
ros2 topic echo /configuration_status

# 2. Verify parameter values
ros2 param list | grep robot_config
ros2 param get /arduino_driver wheel_base

# 3. Force parameter reload
ros2 service call /reload_configuration std_srvs/Trigger
```

**Solutions:**
1. **Configuration Manager Not Running**
   ```bash
   # Start configuration manager
   ros2 launch robot_control configuration_manager.launch.py
   ```

2. **Component Not Subscribing to Parameter Updates**
   - Verify component parameter update callbacks
   - Restart components if needed

3. **Parameter Update Timing Issues**
   - Add delays between parameter updates
   - Check parameter update order

## Build and Dependency Problems

### Legacy Package Conflicts

#### Symptom: Build fails due to conflicting packages

**Diagnostic Steps:**
```bash
# 1. Check for legacy packages in workspace
find . -name "package.xml" | grep -E "(arduino_bridge|ros2arduino_bridge|robot_sensors)"

# 2. Check colcon build output for conflicts
colcon build 2>&1 | grep -i conflict
```

**Solutions:**
1. **Legacy Packages Removed**
   ```bash
   # Note: backup_packages directory has been removed during codebase cleanup
   # If you encounter legacy package issues, check BACKUP_PACKAGES_REMOVAL_LOG.md
   ```

2. **Use Package Exclusion**
   ```bash
   # Build with package exclusion
   colcon build --packages-skip ros2arduino_bridge arduino_bridge robot_sensors
   ```

3. **Clean Build Environment**
   ```bash
   # Clean and rebuild
   rm -rf build/ install/ log/
   ./build_ros2.sh
   ```

### Dependency Issues

#### Symptom: Missing dependencies during build

**Diagnostic Steps:**
```bash
# 1. Check dependency installation
./scripts/ensure_build_deps.sh

# 2. Verify ROS2 packages
apt list --installed | grep ros-humble

# 3. Check Python dependencies
pip list | grep -E "(opencv|serial|numpy)"
```

**Solutions:**
1. **Install Missing System Dependencies**
   ```bash
   # Update package lists
   sudo apt update
   
   # Install ROS2 dependencies
   sudo apt install ros-humble-desktop python3-colcon-common-extensions
   
   # Install hardware dependencies
   sudo apt install python3-serial python3-opencv
   ```

2. **Install Python Dependencies**
   ```bash
   # Install from requirements file
   pip install -r requirements.txt
   
   # Or install individually
   pip install opencv-python pyserial numpy
   ```

## Performance and Monitoring

### System Performance Issues

#### Symptom: High CPU usage or slow response

**Diagnostic Steps:**
```bash
# 1. Monitor system resources
htop
iotop

# 2. Check ROS2 node performance
ros2 run rqt_top rqt_top

# 3. Monitor message rates
ros2 topic hz /cmd_vel
ros2 topic hz /scan
ros2 topic hz /image_raw
```

**Solutions:**
1. **Reduce Message Rates**
   - Lower camera frame rate
   - Reduce LiDAR scan frequency
   - Optimize topic publication rates

2. **Optimize Node Performance**
   - Use efficient data structures
   - Minimize processing in callbacks
   - Consider multi-threading for heavy processing

3. **Hardware Upgrades**
   - Use faster SD card (Class 10 or better)
   - Increase RAM if possible
   - Use USB 3.0 devices when available

### Network Performance Issues

#### Symptom: High network latency or dropped messages

**Diagnostic Steps:**
```bash
# 1. Monitor network usage
iftop
nethogs

# 2. Check ROS2 network configuration
ros2 daemon status
ros2 doctor

# 3. Test network connectivity
ping localhost
```

**Solutions:**
1. **Use Local Communication**
   - Prefer intra-process communication when possible
   - Use shared memory for large data transfers

2. **Optimize Network Configuration**
   - Configure ROS2 DDS settings
   - Use appropriate QoS settings for topics

## Emergency Procedures

### Complete System Recovery

If the system becomes unresponsive or unsafe:

1. **Immediate Safety Actions**
   ```bash
   # Hardware emergency stop (if available)
   # Press physical emergency stop button
   
   # Software emergency stop
   ros2 topic pub /emergency_stop_request std_msgs/Bool "data: true"
   
   # Kill all ROS2 processes
   pkill -f ros2
   ```

2. **System Restart Procedure**
   ```bash
   # 1. Stop all ROS2 processes
   pkill -f ros2
   
   # 2. Check hardware connections
   ls /dev/tty{ACM,USB}* /dev/video*
   
   # 3. Validate configuration
   ros2 run robot_control configuration_manager --validate
   
   # 4. Restart system
   ros2 launch robot_bringup bringup.launch.py
   ```

3. **Hardware Reset Procedure**
   ```bash
   # 1. Power cycle Arduino
   # Disconnect and reconnect USB cable
   
   # 2. Reset camera
   # Disconnect and reconnect camera USB
   
   # 3. Reset LiDAR
   # Power cycle LiDAR unit
   
   # 4. Restart discovery
   ros2 launch robot_control configuration_manager.launch.py
   ```

### Data Recovery

If configuration or log data is corrupted:

1. **Configuration Recovery**
   ```bash
   # Restore default configuration
   cp config/robot_config.yaml.default config/robot_config.yaml
   
   # Validate restored configuration
   ros2 run robot_control configuration_manager --validate
   ```

2. **Log Analysis**
   ```bash
   # Check system logs
   journalctl -u robot-startup.service
   
   # Check ROS2 logs
   ros2 log view
   
   # Analyze crash dumps
   ls /var/crash/
   ```

### Contact Information

For additional support:
- Check GitHub issues: [Repository Issues](https://github.com/your-repo/issues)
- Documentation: [Project Wiki](https://github.com/your-repo/wiki)
- Community Forum: [ROS2 Discourse](https://discourse.ros.org/)

---

**Remember**: Always prioritize safety. When in doubt, trigger emergency stop and seek assistance.