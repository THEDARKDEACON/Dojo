# Safety System Operation and Recovery Guide

This guide provides detailed information about the Dojo Robot's integrated safety system, including operation procedures, recovery protocols, and troubleshooting.

## Table of Contents

1. [Safety System Overview](#safety-system-overview)
2. [Emergency Stop Procedures](#emergency-stop-procedures)
3. [Safety Monitoring](#safety-monitoring)
4. [Recovery Procedures](#recovery-procedures)
5. [Watchdog System](#watchdog-system)
6. [Velocity Limiting](#velocity-limiting)
7. [Safety Configuration](#safety-configuration)
8. [Troubleshooting Safety Issues](#troubleshooting-safety-issues)

## Safety System Overview

The Dojo Robot implements a multi-layered safety system designed to prevent accidents and ensure safe operation in all conditions.

### Safety Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SAFETY SUPERVISOR                        │
│              (Central Safety Coordination)                  │
├─────────────────────────────────────────────────────────────┤
│  Emergency Stop  │  Velocity Limiting  │  Obstacle Detection │
│    Coordination  │   & Filtering       │   & Avoidance       │
├─────────────────────────────────────────────────────────────┤
│  Watchdog Timers │  Hardware Health    │  Command Timeout    │
│   & Monitoring   │    Monitoring       │    Detection        │
├─────────────────────────────────────────────────────────────┤
│                    HARDWARE DRIVERS                         │
│           (Arduino, Camera, LiDAR with Safety)              │
└─────────────────────────────────────────────────────────────┘
```

### Safety Layers

1. **Hardware Layer**: Physical emergency stops, hardware interlocks
2. **Driver Layer**: Device-specific safety checks and limits
3. **Control Layer**: Command filtering, velocity limiting, timeout detection
4. **Supervisor Layer**: System-wide safety coordination and monitoring
5. **Application Layer**: High-level safety logic and user interfaces

## Emergency Stop Procedures

### Triggering Emergency Stop

#### Software Emergency Stop
```bash
# Immediate emergency stop
ros2 topic pub /emergency_stop_request std_msgs/Bool "data: true"

# Check emergency stop status
ros2 topic echo /emergency_stop_status
```

#### Hardware Emergency Stop
- Physical emergency stop button (if installed)
- Power disconnection
- USB device disconnection (triggers automatic safety response)

### Emergency Stop Behavior

When emergency stop is activated:

1. **Immediate Actions** (< 0.5 seconds):
   - All motor commands stopped
   - Arduino receives stop command
   - Camera and LiDAR continue operation for monitoring

2. **System State Changes**:
   - Emergency stop flag set system-wide
   - All motion commands rejected
   - Safety violations logged
   - Diagnostic information published

3. **Component Responses**:
   - Arduino: Motors stopped, encoders continue
   - Camera: Continues operation for safety monitoring
   - LiDAR: Continues scanning for obstacle detection
   - Navigation: Path planning suspended

### Emergency Stop Status Monitoring

```bash
# Monitor emergency stop status
ros2 topic echo /emergency_stop_status

# Check safety violations
ros2 topic echo /safety_violations

# View detailed safety status
ros2 topic echo /safety_status
```

**Status Messages:**
- `NORMAL`: System operating normally
- `EMERGENCY_STOP_ACTIVE`: Emergency stop engaged
- `SAFETY_VIOLATION`: Safety condition violated
- `RECOVERY_PENDING`: Waiting for manual confirmation to resume

## Safety Monitoring

### Real-Time Safety Status

The safety system continuously monitors:

1. **Hardware Health**:
   - Device connectivity and communication
   - Hardware error conditions
   - Power supply status

2. **Operational Safety**:
   - Velocity limit compliance
   - Command timeout detection
   - Obstacle proximity

3. **System Health**:
   - Watchdog timer status
   - Component response times
   - Communication integrity

### Safety Status Topics

```bash
# Overall safety status
ros2 topic echo /safety_status

# Hardware health monitoring
ros2 topic echo /component_health

# Active safety violations
ros2 topic echo /safety_violations

# Watchdog status
ros2 topic echo /watchdog_status
```

### Safety Diagnostics

```bash
# Comprehensive diagnostics
ros2 topic echo /diagnostics

# Safety-specific diagnostics
ros2 topic echo /diagnostics | grep -i safety

# Hardware diagnostics
ros2 topic echo /diagnostics | grep -i hardware
```

## Recovery Procedures

### Clearing Emergency Stop

Emergency stop can only be cleared after:
1. All safety violations are resolved
2. Hardware is confirmed operational
3. Manual operator confirmation is provided

#### Step-by-Step Recovery

1. **Check Safety Status**
   ```bash
   # Verify no active violations
   ros2 topic echo /safety_violations
   
   # Check hardware health
   ros2 topic echo /component_health
   ```

2. **Resolve Safety Violations**
   - Remove obstacles from robot path
   - Fix hardware connection issues
   - Resolve communication problems

3. **Verify Hardware Operation**
   ```bash
   # Check Arduino status
   ros2 topic echo /arduino_status
   
   # Verify camera operation
   ros2 topic echo /camera_status
   
   # Check LiDAR functionality
   ros2 topic echo /lidar_status
   ```

4. **Clear Emergency Stop**
   ```bash
   # Clear emergency stop (requires manual confirmation)
   ros2 service call /clear_emergency_stop std_srvs/Trigger
   ```

5. **Verify Normal Operation**
   ```bash
   # Check safety status
   ros2 topic echo /safety_status
   
   # Test basic movement (low velocity)
   ros2 topic pub /cmd_vel geometry_msgs/Twist "linear: {x: 0.1}"
   ```

### Automatic Recovery Features

The system includes automatic recovery for:

1. **USB Device Reconnection**:
   - Automatic detection of reconnected devices
   - Automatic driver restart
   - Health status verification

2. **Communication Recovery**:
   - Automatic retry of failed communications
   - Timeout-based recovery procedures
   - Graceful degradation when recovery fails

3. **Hardware Error Recovery**:
   - Automatic hardware reset procedures
   - Component restart capabilities
   - Error state clearing

## Watchdog System

### Watchdog Operation

The watchdog system monitors critical components and triggers safety responses when components become unresponsive.

#### Monitored Components

1. **Arduino Driver**: Motor control and sensor communication
2. **Camera Driver**: Image acquisition and processing
3. **LiDAR Driver**: Scan data acquisition
4. **Safety Supervisor**: Safety system coordination
5. **Hardware Manager**: Device health monitoring

#### Watchdog Configuration

```yaml
# In robot_config.yaml
robot:
  safety:
    watchdog_interval: 2.0      # seconds
    watchdog_timeout: 5.0       # seconds
    watchdog_retries: 3         # attempts
```

### Watchdog Monitoring

```bash
# Check watchdog status
ros2 topic echo /watchdog_status

# Monitor component heartbeats
ros2 topic echo /component_heartbeats

# Check watchdog configuration
ros2 param list | grep watchdog
```

### Watchdog Recovery

When watchdog timeout occurs:

1. **Component Restart**: Automatic restart of unresponsive component
2. **Safety Activation**: Emergency stop if critical component fails
3. **Graceful Degradation**: Continue operation with reduced functionality
4. **Operator Notification**: Alert operator of component failure

#### Manual Watchdog Reset

```bash
# Reset all watchdog timers
ros2 service call /reset_watchdogs std_srvs/Trigger

# Reset specific component watchdog
ros2 service call /reset_component_watchdog robot_interfaces/ResetWatchdog "component_name: 'arduino_driver'"
```

## Velocity Limiting

### Velocity Limit Enforcement

The safety system enforces velocity limits at multiple levels:

1. **Configuration Limits**: Maximum safe velocities defined in configuration
2. **Dynamic Limits**: Adjusted based on current conditions
3. **Emergency Limits**: Reduced limits during safety conditions

#### Velocity Limit Configuration

```yaml
# In robot_config.yaml
robot:
  physical_parameters:
    max_linear_velocity: 0.5    # m/s
    max_angular_velocity: 1.0   # rad/s
  
  safety:
    emergency_linear_limit: 0.1  # m/s (during safety conditions)
    emergency_angular_limit: 0.2 # rad/s (during safety conditions)
```

### Velocity Monitoring

```bash
# Compare input and filtered commands
ros2 topic echo /cmd_vel &
ros2 topic echo /cmd_vel_filtered

# Monitor velocity violations
ros2 topic echo /velocity_violations

# Check current velocity limits
ros2 param get /safety_supervisor max_linear_velocity
```

### Dynamic Velocity Adjustment

Velocity limits are dynamically adjusted based on:

1. **Obstacle Proximity**: Reduced speed near obstacles
2. **Hardware Health**: Lower limits with degraded hardware
3. **Safety Conditions**: Emergency limits during safety violations
4. **System Load**: Reduced limits under high system load

## Safety Configuration

### Master Safety Configuration

All safety parameters are centralized in the master configuration file:

```yaml
# config/robot_config.yaml
robot:
  safety:
    # Emergency stop configuration
    emergency_stop_timeout: 0.5      # seconds
    emergency_stop_retries: 3        # attempts
    
    # Obstacle detection
    obstacle_stop_distance: 0.3      # meters
    obstacle_slow_distance: 0.5      # meters
    obstacle_detection_enabled: true
    
    # Command timeout
    command_timeout: 1.0             # seconds
    command_timeout_action: "stop"   # "stop" or "emergency_stop"
    
    # Watchdog configuration
    watchdog_interval: 2.0           # seconds
    watchdog_timeout: 5.0            # seconds
    watchdog_enabled: true
    
    # Velocity limiting
    velocity_limit_enabled: true
    emergency_velocity_factor: 0.2   # 20% of normal limits during emergency
    
    # Hardware safety
    hardware_timeout: 3.0            # seconds
    hardware_retry_count: 3          # attempts
    hardware_recovery_enabled: true
```

### Safety Parameter Validation

```bash
# Validate safety configuration
ros2 run robot_control configuration_manager --validate-safety

# Check safety parameter consistency
ros2 topic echo /safety_configuration_status

# Test safety parameter changes
ros2 param set /safety_supervisor obstacle_stop_distance 0.4
```

## Troubleshooting Safety Issues

### Common Safety Problems

#### Emergency Stop Won't Clear

**Symptoms:**
- Emergency stop service call fails
- Safety status remains in emergency state
- System rejects motion commands

**Diagnostic Steps:**
```bash
# Check active safety violations
ros2 topic echo /safety_violations

# Verify hardware health
ros2 topic echo /component_health

# Check emergency stop status
ros2 topic echo /emergency_stop_status
```

**Solutions:**
1. **Resolve Active Violations**: Address all reported safety violations
2. **Hardware Recovery**: Ensure all hardware is operational
3. **Manual Confirmation**: Use service call, not topic publication
4. **System Restart**: Restart safety system if persistent issues

#### False Safety Triggers

**Symptoms:**
- Frequent emergency stops without apparent cause
- Velocity limits too restrictive
- Watchdog timeouts under normal operation

**Diagnostic Steps:**
```bash
# Monitor safety violations in real-time
ros2 topic echo /safety_violations

# Check watchdog status
ros2 topic echo /watchdog_status

# Monitor system performance
htop
ros2 run rqt_top rqt_top
```

**Solutions:**
1. **Adjust Sensitivity**: Tune safety parameters for environment
2. **Performance Optimization**: Reduce system load
3. **Hardware Issues**: Check for intermittent hardware problems
4. **Configuration Review**: Verify safety parameter appropriateness

#### Safety System Not Responding

**Symptoms:**
- Safety topics not publishing
- Emergency stop commands ignored
- No safety status updates

**Diagnostic Steps:**
```bash
# Check safety supervisor status
ros2 node list | grep safety

# Verify safety system launch
ros2 launch robot_control safety_system.launch.py

# Check safety topic availability
ros2 topic list | grep safety
```

**Solutions:**
1. **Restart Safety System**: Launch safety system components
2. **Check Dependencies**: Verify all required nodes are running
3. **Configuration Issues**: Validate safety system configuration
4. **Hardware Problems**: Check hardware manager connectivity

### Safety System Maintenance

#### Regular Safety Checks

Perform these checks regularly to ensure safety system reliability:

1. **Weekly Checks**:
   ```bash
   # Test emergency stop response
   ros2 topic pub /emergency_stop_request std_msgs/Bool "data: true"
   ros2 service call /clear_emergency_stop std_srvs/Trigger
   
   # Verify watchdog operation
   ros2 topic echo /watchdog_status
   
   # Check safety configuration
   ros2 run robot_control configuration_manager --validate-safety
   ```

2. **Monthly Checks**:
   - Test hardware emergency stop (if available)
   - Verify obstacle detection accuracy
   - Check velocity limiting effectiveness
   - Review safety logs for patterns

3. **System Updates**:
   - Update safety parameters based on operational experience
   - Review and update safety procedures
   - Train operators on safety system operation

#### Safety Log Analysis

```bash
# View safety-related logs
ros2 log view | grep -i safety

# Check emergency stop history
grep "emergency_stop" ~/.ros/log/*/rosout.log

# Analyze safety violations
grep "safety_violation" ~/.ros/log/*/rosout.log
```

### Emergency Contact Information

In case of safety system failure or emergency:

1. **Immediate Actions**:
   - Physically disconnect power if safe to do so
   - Clear area of personnel
   - Document incident details

2. **Technical Support**:
   - Check system logs and diagnostics
   - Review troubleshooting procedures
   - Contact technical support with detailed information

3. **Incident Reporting**:
   - Document safety incidents
   - Review and update safety procedures
   - Implement corrective measures

---

**Safety First**: Always prioritize safety over system operation. When in doubt, activate emergency stop and seek assistance.