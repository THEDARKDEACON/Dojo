# Bypass Mode Usage Guide

## Overview

The Arduino Integration Bypass Mode provides a simplified motion control path that bypasses complex safety and hardware management systems in the Dojo robot. This mode enables direct Arduino communication similar to the working robosync system while maintaining essential safety controls.

## Quick Start

### Basic Usage

```bash
# Launch bypass mode with default settings
ros2 launch robot_control bypass_mode.launch.py

# Launch with custom Arduino port
ros2 launch robot_control bypass_mode.launch.py arduino_port:=/dev/ttyUSB0

# Launch with debug logging enabled
ros2 launch robot_control bypass_mode.launch.py debug:=true
```

### Sending Motion Commands

```bash
# Send forward motion command
ros2 topic pub /cmd_vel geometry_msgs/Twist "linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}"

# Send rotation command
ros2 topic pub /cmd_vel geometry_msgs/Twist "linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}"

# Stop robot
ros2 topic pub /cmd_vel geometry_msgs/Twist "linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}"
```

## Configuration

### Physical Parameters (Robosync-Compatible)

The bypass mode uses robosync-compatible physical parameters:

- **Wheel Base**: 0.19m (distance between wheels)
- **Wheel Radius**: 0.035m (wheel radius)
- **Encoder Ticks**: 20 ticks per revolution
- **Baud Rate**: 115200 (Arduino communication)

### PID Parameters (Robosync Values)

- **Kp**: 20.0 (Proportional gain)
- **Kd**: 12.0 (Derivative gain)
- **Ki**: 0.0 (Integral gain)
- **Ko**: 50 (Output scaling)

## Mode Switching

### Enable Bypass Mode

```bash
# Enable bypass mode via service call
ros2 service call /set_bypass_mode std_srvs/SetBool "data: true"
```

### Disable Bypass Mode

```bash
# Disable bypass mode and restore normal operation
ros2 service call /set_bypass_mode std_srvs/SetBool "data: false"
```

### Check Bypass Status

```bash
# Monitor bypass mode status
ros2 topic echo /bypass_status
```

## Monitoring and Diagnostics

### Status Topics

- `/bypass_status` - Current bypass mode status and diagnostics
- `/odom` - Odometry data from Arduino encoders
- `/arduino_diagnostics` - Arduino communication health

### Debug Information

```bash
# View Arduino communication logs
ros2 topic echo /arduino_debug

# Monitor encoder raw data
ros2 topic echo /encoder_raw

# Check safety override status
ros2 topic echo /safety_override_status
```

## Safety Features

### Emergency Stop

Even in bypass mode, emergency stop functionality is preserved:

```bash
# Trigger emergency stop
ros2 topic pub /emergency_stop std_msgs/Bool "data: true"

# Clear emergency stop
ros2 topic pub /emergency_stop std_msgs/Bool "data: false"
```

### Safety Systems Disabled in Bypass Mode

- EmergencyStopHandler automatic triggers
- SafetySupervisor velocity limiting
- Hardware discovery timeouts
- Camera/LiDAR dependency checks

### Safety Systems Preserved

- Manual emergency stop button
- Emergency stop service calls
- Basic velocity limits (configurable)

## Troubleshooting

### Arduino Connection Issues

1. **Check Arduino Port**:
   ```bash
   ls /dev/tty*
   # Look for /dev/ttyACM0, /dev/ttyUSB0, etc.
   ```

2. **Verify Arduino Firmware**:
   - Ensure ROSArduinoBridge firmware is loaded
   - Check baud rate is set to 115200

3. **Test Serial Communication**:
   ```bash
   # Test direct serial communication
   screen /dev/ttyACM0 115200
   # Send: e (should return encoder values)
   ```

### Motion Issues

1. **Check Command Velocity**:
   ```bash
   ros2 topic echo /cmd_vel
   ```

2. **Monitor Arduino Commands**:
   ```bash
   ros2 topic echo /arduino_debug
   ```

3. **Verify Encoder Feedback**:
   ```bash
   ros2 topic echo /odom
   ```

### Mode Switching Problems

1. **Check Bypass Status**:
   ```bash
   ros2 topic echo /bypass_status
   ```

2. **Verify Safety Override**:
   ```bash
   ros2 topic echo /safety_override_status
   ```

3. **Restart Bypass Mode**:
   ```bash
   ros2 service call /set_bypass_mode std_srvs/SetBool "data: false"
   ros2 service call /set_bypass_mode std_srvs/SetBool "data: true"
   ```

## Integration with Main System

### Using Bypass Mode in Complete Simulation

```bash
# Launch complete simulation with bypass mode enabled
ros2 launch complete_robot_simulation.launch.py bypass_mode:=true

# Launch with bypass mode and no GUI
ros2 launch complete_robot_simulation.launch.py bypass_mode:=true gui:=false
```

### Configuration Files

- `bypass_config.yaml` - Main bypass mode configuration
- `arduino_config.yaml` - Arduino-specific settings (overridden in bypass mode)
- `robot_config.yaml` - Robot physical parameters (overridden in bypass mode)

## Performance Expectations

- **Command Latency**: < 50ms from cmd_vel to Arduino
- **Odometry Rate**: 20Hz (matching robosync)
- **Arduino Communication**: 115200 baud, ROSArduinoBridge protocol
- **Mode Switch Time**: < 2 seconds

## Limitations

1. **Reduced Safety**: Some safety systems are disabled
2. **Hardware Dependency**: Requires Arduino with ROSArduinoBridge firmware
3. **Limited Sensors**: Camera/LiDAR not required but may not function optimally
4. **Manual Configuration**: Physical parameters must match actual hardware

## Support

For issues with bypass mode:

1. Check this documentation
2. Review log files for error messages
3. Test Arduino communication directly
4. Verify physical parameter configuration
5. Ensure ROSArduinoBridge firmware compatibility