# Dojo Robot - ROS2 Robotics Platform

A production-ready, safety-focused ROS2 robotics platform with automatic hardware discovery, unified configuration management, and comprehensive safety systems.

## 🚀 Quick Start

```bash
# Build the workspace
./build_ros2.sh

# Real hardware with auto-discovery (recommended)
ros2 launch robot_bringup bringup.launch.py

# Simulation mode (requires robot_gazebo package)
ros2 launch robot_bringup bringup.launch.py use_simulation:=true

# Hardware mode with specific components
ros2 launch robot_bringup bringup.launch.py use_arduino:=true use_camera:=false use_lidar:=false

# Launch with configuration validation
ros2 launch robot_control configuration_manager.launch.py
```

## 🏗️ Architecture Overview

The Dojo robot uses a **production-ready layered architecture** with automatic hardware discovery and unified configuration management:

```
┌─────────────────────────────────────────────────────────────┐
│                    NAVIGATION LAYER                         │
│              (Path Planning, SLAM, Mapping)                 │
├─────────────────────────────────────────────────────────────┤
│                    PERCEPTION LAYER                         │
│            (Computer Vision, Object Detection)              │
├─────────────────────────────────────────────────────────────┤
│                  SAFETY & CONTROL LAYER                     │
│    (Safety Supervisor, Emergency Stop, Velocity Limiting)   │
├─────────────────────────────────────────────────────────────┤
│                CONFIGURATION MANAGEMENT                      │
│         (Unified Config, Validation, Auto-Propagation)      │
├─────────────────────────────────────────────────────────────┤
│                HARDWARE ABSTRACTION LAYER                   │
│        (Auto-Discovery, Health Monitoring, Recovery)        │
├─────────────────────────────────────────────────────────────┤
│                    DEVICE DRIVERS                           │
│           (Arduino, Camera, LiDAR with Auto-Reconnect)      │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

**🔍 Automatic Hardware Discovery**: Zero-configuration hardware setup
- Automatic Arduino detection on all serial ports
- Camera capability detection and optimal configuration
- LiDAR model identification and driver selection
- USB device monitoring with automatic reconnection

**⚙️ Unified Configuration Management**: Single source of truth
- Master configuration file (`config/robot_config.yaml`)
- Automatic parameter validation and conflict detection
- Consistent parameters across all system components
- Runtime configuration updates with safety checks

**🛡️ Comprehensive Safety Systems**: Production-ready safety
- Multi-layered emergency stop coordination
- Real-time obstacle detection and avoidance
- Velocity limiting and command timeout protection
- Watchdog timers for critical system components

**🔧 Robust Hardware Management**: Enterprise-grade reliability
- Continuous health monitoring of all components
- Automatic recovery procedures for failed devices
- Graceful degradation when components are unavailable
- Real-time diagnostic reporting and alerting

## 📦 Package Structure

### Core Packages

| Package | Purpose | Key Features |
|---------|---------|--------------|
| `robot_control` | **Unified Control & Safety** | Configuration manager, hardware discovery, safety supervisor, emergency stop coordination |
| `robot_hardware` | **Hardware Drivers** | Arduino, camera, LiDAR drivers with auto-discovery and health monitoring |
| `robot_interfaces` | **Custom Messages** | Standardized data structures and services for safety and diagnostics |
| `robot_bringup` | **System Orchestration** | Launch files with automatic mode detection and configuration validation |

### Configuration System

| Component | Location | Purpose |
|-----------|----------|---------|
| **Master Config** | `config/robot_config.yaml` | Single source of truth for all robot parameters |
| **Configuration Manager** | `robot_control/configuration_manager.py` | Validation, conflict detection, parameter propagation |
| **Hardware Discovery** | `robot_control/hardware_discovery.py` | Automatic device detection and capability discovery |
| **Safety Supervisor** | `robot_control/safety_supervisor.py` | Emergency stop coordination and safety monitoring |

### Optional Packages

| Package | Purpose | Status |
|---------|---------|--------|
| `robot_perception` | Computer vision, object detection | Optional |
| `robot_navigation` | Autonomous navigation, SLAM | Optional |
| `robot_description` | URDF models, visualization | Available |
| `robot_gazebo` | Simulation environment | Optional (for simulation mode) |

## 🔌 Hardware Discovery System

### Automatic Hardware Detection

The system automatically discovers and configures hardware devices:

**Arduino Detection:**
- Scans all serial ports (`/dev/ttyACM*`, `/dev/ttyUSB*`)
- Identifies Arduino devices by communication protocol
- Automatically configures baud rate and communication parameters
- Monitors connection status and attempts reconnection on failure

**Camera Discovery:**
- Detects USB cameras (`/dev/video*`)
- Queries camera capabilities (resolutions, formats, frame rates)
- Automatically selects optimal configuration based on preferences
- Supports multiple camera formats (MJPEG, YUYV, etc.)

**LiDAR Detection:**
- Scans serial ports for LiDAR devices
- Identifies device model and capabilities
- Configures appropriate driver and parameters
- Supports RPLiDAR A1/A2 and compatible devices

### Supported Hardware

- **Arduino Uno/Nano** - Motor control, encoders, sensors (auto-detected)
- **USB Camera** - Computer vision, streaming (auto-configured)
- **RPLiDAR A1/A2** - 360° laser scanning (auto-identified)
- **Ultrasonic Sensors** - Obstacle detection (via Arduino)
- **IMU** (optional) - Orientation sensing (via Arduino)

### Hardware Connections

```
Raspberry Pi 4
├── USB Ports: Auto-discovered devices
│   ├── Arduino (any available port)
│   ├── LiDAR (any available port)
│   └── Camera (any available port)
└── GPIO: Additional sensors via Arduino
```

### Hardware Health Monitoring

- **Real-time Status**: Continuous monitoring of device connectivity
- **Automatic Recovery**: Reconnection attempts for disconnected devices
- **Graceful Degradation**: System continues with available devices
- **Diagnostic Reporting**: Detailed health metrics and error reporting

## ⚙️ Configuration Management

### Master Configuration File

All robot parameters are centralized in `config/robot_config.yaml` - the single source of truth:

```yaml
robot:
  physical_parameters:
    wheel_base: 0.26          # meters
    wheel_radius: 0.030       # meters
    max_linear_velocity: 0.5  # m/s
    max_angular_velocity: 1.0 # rad/s
    
  hardware:
    arduino:
      auto_discover: true
      fallback_port: "/dev/ttyACM0"
      baud_rate: 115200
      timeout: 1.0
      
    camera:
      auto_discover: true
      preferred_resolution: [640, 480]
      fps: 30.0
      
    lidar:
      auto_discover: true
      fallback_port: "/dev/ttyUSB0"
      scan_frequency: 10.0
      
  safety:
    emergency_stop_timeout: 0.5  # seconds
    obstacle_stop_distance: 0.3  # meters
    command_timeout: 1.0         # seconds
    watchdog_interval: 2.0       # seconds
    
  system:
    use_simulation: false
    log_level: "INFO"
    diagnostics_rate: 2.0        # Hz
```

### Configuration Features

- **Automatic Validation**: Configuration conflicts detected at startup
- **Parameter Propagation**: Master config automatically updates all subsystems
- **Hardware Auto-Discovery**: Devices detected automatically when `auto_discover: true`
- **Fallback Configuration**: Manual device paths used when auto-discovery fails
- **Safety Enforcement**: Safety parameters validated and enforced across all components

## 🎮 Usage Examples

### Basic Robot Control

```bash
# Start the robot
ros2 launch robot_bringup bringup.launch.py

# Control manually with keyboard
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# Check system status
ros2 topic echo /system_status
ros2 topic echo /diagnostics
```

### Simulation vs Real Hardware

- Real hardware (no Gazebo): set `use_gazebo:=false` so the URDF doesn’t require simulation-only dependencies. Example:
  - `ros2 launch robot_bringup bringup.launch.py use_gazebo:=false`
- Simulation (Gazebo): set `use_gazebo:=true use_sim_time:=true` and ensure the `robot_gazebo/` package is built and sourced.
  - `colcon build --packages-select robot_gazebo && source install/setup.bash`
  - `ros2 launch robot_bringup bringup.launch.py use_gazebo:=true use_sim_time:=true`
- Sensor toggles: `use_arduino`, `use_camera`, `use_lidar` are available in both `bringup.launch.py` and `hardware.launch.py` to selectively enable drivers.

### Hardware Discovery and Testing

```bash
# Test hardware discovery
ros2 launch robot_control configuration_manager.launch.py

# Test individual components with auto-discovery
ros2 launch robot_hardware hardware.launch.py use_arduino:=true use_camera:=false use_lidar:=false

# Monitor hardware health and discovery status
ros2 topic echo /hardware_discovery_status
ros2 topic echo /arduino_status
ros2 topic echo /camera_status
ros2 topic echo /lidar_status
ros2 topic echo /diagnostics
```

### Safety System Features

```bash
# Emergency stop (coordinated across all components)
ros2 topic pub /emergency_stop_request std_msgs/Bool "data: true"

# Clear emergency stop (requires explicit confirmation)
ros2 service call /clear_emergency_stop std_srvs/Trigger

# Monitor safety status
ros2 topic echo /safety_status
ros2 topic echo /emergency_stop_status
ros2 topic echo /watchdog_status

# Test velocity limiting
ros2 topic echo /cmd_vel_filtered  # Shows velocity-limited commands
```

### Configuration Management

```bash
# Validate configuration
ros2 run robot_control configuration_manager --validate

# Check for configuration conflicts
ros2 topic echo /configuration_status

# Reload configuration (with validation)
ros2 service call /reload_configuration std_srvs/Trigger
```
## 🛠️ 
Development Guide

### Adding New Hardware

1. **Create driver in `robot_hardware/drivers/`**:
```python
class NewSensorDriver(Node):
    def __init__(self):
        super().__init__('new_sensor_driver')
        # Your sensor code here
```

2. **Add to hardware manager**:
```python
# In hardware_manager.py
self.new_sensor_status_sub = self.create_subscription(
    String, 'new_sensor_status', self._new_sensor_callback, 10)
```

3. **Update configuration**:
```yaml
# In hardware.yaml
new_sensor_driver:
  ros__parameters:
    port: "/dev/ttyUSB1"
    # Your parameters here
```

4. **Add to launch file**:
```python
# In hardware.launch.py
new_sensor_node = Node(
    package='robot_hardware',
    executable='new_sensor_driver',
    # ...
)
```

### Safety System Integration

All new components should integrate with the safety system:

```python
# Publish status for monitoring
self.status_pub = self.create_publisher(String, 'component_status', 10)

# Listen for emergency stops
self.estop_sub = self.create_subscription(
    Bool, 'emergency_stop', self._estop_callback, 10)

def _estop_callback(self, msg):
    if msg.data:
        self.stop_all_operations()
```

## 🐛 Troubleshooting

### Hardware Discovery Issues

**No devices detected:**
```bash
# Check hardware discovery status
ros2 topic echo /hardware_discovery_status

# Manual device scan
ros2 run robot_control hardware_discovery --scan

# Check USB permissions
sudo usermod -a -G dialout $USER
# Logout and login again
```

**Arduino not auto-detected:**
```bash
# Check available serial ports
ls /dev/tty{ACM,USB}*

# Test manual connection
ros2 run robot_control arduino_bridge --port /dev/ttyACM0

# Check Arduino firmware compatibility
# Ensure ROSArduinoBridge firmware is loaded
```

**Camera auto-discovery fails:**
```bash
# Check camera devices
ls /dev/video*
v4l2-ctl --list-devices

# Test camera capabilities
ros2 run robot_control camera_driver --test-capabilities

# Check camera permissions
sudo usermod -a -G video $USER
```

**LiDAR not detected:**
```bash
# Check serial devices
ls /dev/ttyUSB*

# Test LiDAR communication
ros2 run robot_control lidar_driver --test-connection

# Check power supply (LiDAR needs 5V, 1.5A)
# Verify USB cable supports data transfer
```

### Configuration Issues

**Configuration validation fails:**
```bash
# Check configuration conflicts
ros2 run robot_control configuration_manager --validate

# View detailed validation report
ros2 topic echo /configuration_validation_report

# Reset to default configuration
cp config/robot_config.yaml.default config/robot_config.yaml
```

**Parameter conflicts detected:**
```bash
# View conflict details
ros2 topic echo /configuration_conflicts

# Check parameter propagation
ros2 param list | grep robot_config

# Force parameter reload
ros2 service call /reload_configuration std_srvs/Trigger
```

### Safety System Issues

**Emergency stop not clearing:**
```bash
# Check safety status
ros2 topic echo /safety_status

# View safety violations
ros2 topic echo /safety_violations

# Clear emergency stop (requires manual confirmation)
ros2 service call /clear_emergency_stop std_srvs/Trigger
```

**Watchdog timeouts:**
```bash
# Check watchdog status
ros2 topic echo /watchdog_status

# View component health
ros2 topic echo /component_health

# Reset watchdog timers
ros2 service call /reset_watchdogs std_srvs/Trigger
```

### Debug Commands

```bash
# Check all ROS topics
ros2 topic list

# Monitor system health
ros2 topic echo /diagnostics

# Check node status
ros2 node list
ros2 node info /hardware_manager

# View logs
ros2 log view
```

### Performance Monitoring

```bash
# CPU and memory usage
htop

# ROS2 performance
ros2 run rqt_graph rqt_graph
ros2 run rqt_plot rqt_plot

# Network bandwidth
iftop
```

## 🔧 Build System

### Dependencies

**System packages:**
```bash
sudo apt install ros-humble-desktop python3-colcon-common-extensions
sudo apt install python3-opencv python3-serial python3-numpy
```

**ROS2 packages:**
```bash
sudo apt install ros-humble-tf2-ros ros-humble-geometry-msgs
sudo apt install ros-humble-sensor-msgs ros-humble-nav-msgs
```

### Build Process

The build system automatically:
1. **Validates dependencies** - Checks all required packages
2. **Handles package order** - Builds in correct dependency order  
3. **Manages Python paths** - Sets up module imports correctly
4. **Installs configurations** - Copies config files to install space

```bash
# Full build (recommended)
./build_ros2_pi.sh

# Individual package build
colcon build --packages-select robot_hardware

# Clean build
rm -rf build/ install/ log/
./build_ros2_pi.sh
```

#### Notes

- To avoid legacy package issues (e.g., `ros2arduino_bridge` installing to `/lib`), skip legacy packages during build:
  - `colcon build --packages-skip ros2arduino_bridge arduino_bridge robot_sensors nv21_converter_pkg`
  - Or move `backup_packages/` outside the workspace so `colcon` doesn’t discover them.
- For simulation, ensure `robot_gazebo` is built when launching with `use_gazebo:=true`:
  - `colcon build --packages-select robot_gazebo`
  - `source install/setup.bash`


## 📊 System Monitoring

### Health Dashboards

The system provides comprehensive monitoring:

**Hardware Status:**
- Arduino connection state and data flow
- Camera frame rate and image quality
- LiDAR scan rate and data validity
- USB device connectivity

**Safety Status:**
- Emergency stop state
- Obstacle detection alerts
- Velocity limit violations
- Hardware error conditions

**Performance Metrics:**
- CPU and memory usage
- Network bandwidth utilization
- Message publication rates
- System response times

### Diagnostic Tools

```bash
# Real-time system status
ros2 run rqt_robot_monitor rqt_robot_monitor

# Topic monitoring
ros2 run rqt_topic rqt_topic

# Parameter management
ros2 run rqt_reconfigure rqt_reconfigure
```

## 🚀 Deployment

### Raspberry Pi Setup

1. **Install ROS2 Humble**
2. **Clone repository**
3. **Run build script**
4. **Configure autostart** (optional)

```bash
# Autostart on boot
sudo systemctl enable robot-startup.service
```

### Docker Deployment (Alternative)

```dockerfile
FROM ros:humble
COPY . /workspace
WORKDIR /workspace
RUN ./build_ros2_pi.sh
CMD ["ros2", "launch", "robot_bringup", "bringup.launch.py"]
```

## 📚 API Reference

### Core Topics

| Topic | Type | Description |
|-------|------|-------------|
| `/cmd_vel` | `geometry_msgs/Twist` | Robot velocity commands (input) |
| `/cmd_vel_filtered` | `geometry_msgs/Twist` | Velocity commands after safety filtering |
| `/odom` | `nav_msgs/Odometry` | Robot odometry |
| `/scan` | `sensor_msgs/LaserScan` | LiDAR scan data |
| `/image_raw` | `sensor_msgs/Image` | Camera images |

### Hardware Discovery Topics

| Topic | Type | Description |
|-------|------|-------------|
| `/hardware_discovery_status` | `std_msgs/String` | Hardware discovery results |
| `/arduino_status` | `robot_interfaces/HardwareStatus` | Arduino connection and health |
| `/camera_status` | `robot_interfaces/HardwareStatus` | Camera status and capabilities |
| `/lidar_status` | `robot_interfaces/HardwareStatus` | LiDAR status and performance |

### Safety System Topics

| Topic | Type | Description |
|-------|------|-------------|
| `/safety_status` | `robot_interfaces/SafetyStatus` | Overall safety system status |
| `/emergency_stop_status` | `std_msgs/Bool` | Emergency stop state |
| `/emergency_stop_request` | `std_msgs/Bool` | Emergency stop trigger |
| `/safety_violations` | `std_msgs/String` | Active safety violations |
| `/watchdog_status` | `std_msgs/String` | Watchdog timer status |

### Configuration Topics

| Topic | Type | Description |
|-------|------|-------------|
| `/configuration_status` | `std_msgs/String` | Configuration validation status |
| `/configuration_conflicts` | `std_msgs/String` | Detected parameter conflicts |
| `/diagnostics` | `diagnostic_msgs/DiagnosticArray` | System diagnostics |

### Key Services

| Service | Type | Description |
|---------|------|-------------|
| `/clear_emergency_stop` | `std_srvs/Trigger` | Clear emergency stop (requires confirmation) |
| `/reload_configuration` | `std_srvs/Trigger` | Reload and validate configuration |
| `/reset_watchdogs` | `std_srvs/Trigger` | Reset all watchdog timers |
| `/set_control_mode` | `robot_interfaces/SetMode` | Change control mode |
| `/calibrate_hardware` | `robot_interfaces/Calibration` | Hardware calibration |

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `robot.physical_parameters.wheel_base` | 0.26 | Distance between wheels (m) |
| `robot.physical_parameters.wheel_radius` | 0.030 | Wheel radius (m) |
| `robot.physical_parameters.max_linear_velocity` | 0.5 | Maximum forward speed (m/s) |
| `robot.physical_parameters.max_angular_velocity` | 1.0 | Maximum rotation speed (rad/s) |
| `robot.safety.emergency_stop_timeout` | 0.5 | Emergency stop response time (s) |
| `robot.safety.obstacle_stop_distance` | 0.3 | Emergency stop distance (m) |
| `robot.safety.command_timeout` | 1.0 | Command timeout (seconds) |
| `robot.safety.watchdog_interval` | 2.0 | Watchdog check interval (s) | 

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Follow coding standards**: Use ROS2 conventions
4. **Add tests**: Ensure new code is tested
5. **Update documentation**: Keep README current
6. **Submit pull request**: Describe changes clearly

### Coding Standards

- **Python**: Follow PEP 8, use type hints
- **ROS2**: Follow ROS2 style guide
- **Comments**: Document complex logic
- **Safety**: Always consider safety implications

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **ROS2 Community** - For the excellent robotics framework
- **Open Source Contributors** - For the libraries and tools used
- **Robotics Community** - For inspiration and best practices

---

**Need help?** Open an issue or check the troubleshooting section above.
