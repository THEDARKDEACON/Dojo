# Performance Dashboard

## Overview

The Performance Dashboard is a dedicated ROS2 node that provides real-time system monitoring and performance metrics visualization. It monitors both system resources (CPU, memory, network) and robotics-specific metrics (detection rate, navigation efficiency, mapping coverage, safety status).

## Features

### System Monitoring
- **CPU Usage**: Real-time CPU utilization percentage with warning/critical thresholds
- **Memory Usage**: RAM usage in percentage and MB with configurable alerts
- **Disk Usage**: Storage utilization monitoring
- **Network Bandwidth**: Network I/O in Mbps

### Robotics Metrics
- **Detection Rate**: Objects detected per second
- **Objects Detected**: Total count of semantic objects in the map
- **Mapping Coverage**: Percentage of environment mapped
- **Navigation Efficiency**: Path smoothness metric (0-100%)
- **Goal Distance**: Distance to current navigation goal
- **Current Velocity**: Robot's current speed

### Safety Monitoring
- **Safety Level**: Current safety system status
- **Active Threats**: Number of detected threats requiring attention

## Topics

### Subscribed Topics
- `/semantic_map` (std_msgs/String): Semantic object map data
- `/plan` (nav_msgs/Path): Current navigation plan
- `/cmd_vel` (geometry_msgs/Twist): Velocity commands
- `/safety_status` (std_msgs/String): Safety system status
- `/map` (nav_msgs/OccupancyGrid): Occupancy grid map

### Published Topics
- `/performance_dashboard` (visualization_msgs/MarkerArray): RViz visualization markers
- `/performance_metrics_json` (std_msgs/String): JSON-formatted metrics data
- `/performance_alerts` (std_msgs/String): Performance alerts and warnings

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `update_rate` | double | 1.0 | Dashboard update frequency (Hz) |
| `cpu_warning_threshold` | double | 80.0 | CPU usage warning threshold (%) |
| `cpu_critical_threshold` | double | 90.0 | CPU usage critical threshold (%) |
| `memory_warning_threshold` | double | 80.0 | Memory usage warning threshold (%) |
| `memory_critical_threshold` | double | 90.0 | Memory usage critical threshold (%) |

## Usage

### Launch with Default Settings

```bash
ros2 launch robot_semantic_slam performance_dashboard.launch.py
```

### Launch with Custom Thresholds

```bash
ros2 launch robot_semantic_slam performance_dashboard.launch.py \
    cpu_warning_threshold:=70.0 \
    cpu_critical_threshold:=85.0 \
    memory_warning_threshold:=75.0 \
    update_rate:=2.0
```

### Launch as Part of Cutting-Edge Features

The performance dashboard is automatically included when launching the full system:

```bash
ros2 launch robot_semantic_slam cutting_edge_features.launch.py \
    use_performance_dashboard:=true
```

To disable the dashboard:

```bash
ros2 launch robot_semantic_slam cutting_edge_features.launch.py \
    use_performance_dashboard:=false
```

## RViz Visualization

The dashboard creates a visual panel in RViz with the following sections:

### Dashboard Layout

```
┌─────────────────────────────────────┐
│ PERFORMANCE DASHBOARD               │
├─────────────────────────────────────┤
│ System Health:                      │
│   CPU: 45.2%                        │
│   Memory: 62.1% (1024MB)            │
│   Network: 2.34 Mbps                │
├─────────────────────────────────────┤
│ Navigation:                         │
│   Efficiency: 87.5%                 │
│   Goal Distance: 3.45m              │
│   Velocity: 0.25m/s                 │
├─────────────────────────────────────┤
│ Perception:                         │
│   Objects: 12                       │
│   Detection Rate: 1.5/s             │
│   Map Coverage: 78.3%               │
├─────────────────────────────────────┤
│ Safety:                             │
│   Active Threats: 0                 │
└─────────────────────────────────────┘
```

### Color Coding

- **Green**: Normal operation (below warning threshold)
- **Orange**: Warning level (above warning, below critical)
- **Red**: Critical level (above critical threshold)

## Alerts System

The dashboard generates alerts when metrics exceed thresholds:

### Alert Levels

1. **WARNING**: Metric exceeds warning threshold
   - Logged as warning message
   - Published to `/performance_alerts` topic
   - Orange color in visualization

2. **CRITICAL**: Metric exceeds critical threshold
   - Logged as error message
   - Published to `/performance_alerts` topic
   - Red color in visualization

### Alert Format

Alerts are published as JSON:

```json
[
  {
    "level": "WARNING",
    "metric": "CPU",
    "value": 82.5,
    "message": "CPU usage high: 82.5%"
  },
  {
    "level": "CRITICAL",
    "metric": "Memory",
    "value": 92.1,
    "message": "Memory usage critical: 92.1%"
  }
]
```

## Metrics JSON Format

Performance metrics are published as JSON to `/performance_metrics_json`:

```json
{
  "timestamp": 1699876543,
  "metrics": {
    "cpu_usage": 45.2,
    "memory_usage": 62.1,
    "memory_usage_mb": 1024.5,
    "disk_usage": 35.7,
    "network_bandwidth": 2.34,
    "detection_rate": 1.5,
    "navigation_efficiency": 87.5,
    "mapping_coverage": 78.3,
    "safety_level": 0,
    "active_threats": 0,
    "objects_detected": 12,
    "goal_distance": 3.45,
    "current_velocity": 0.25
  }
}
```

## Integration with Other Systems

### With Enhanced Visualizer

The performance dashboard complements the enhanced visualizer:
- **Enhanced Visualizer**: Focuses on 3D visualization and semantic object markers
- **Performance Dashboard**: Focuses on system metrics and performance monitoring

Both can run simultaneously for comprehensive monitoring.

### With Safety System

The dashboard subscribes to safety system status and displays:
- Current safety level
- Number of active threats
- Safety-related alerts

### With Semantic SLAM

The dashboard monitors:
- Object detection rate
- Number of detected objects
- Mapping coverage progress

## Troubleshooting

### Dashboard Not Visible in RViz

1. Ensure the MarkerArray display is added to RViz
2. Set the topic to `/performance_dashboard`
3. Check that the frame is set to `map`
4. Verify the node is running: `ros2 node list | grep performance_dashboard`

### High CPU/Memory Warnings

If you see persistent warnings:
1. Check for resource-intensive processes
2. Reduce update rate: `update_rate:=0.5`
3. Disable unused features
4. Consider adjusting thresholds for your system

### No Metrics Data

If metrics show zeros:
1. Verify required topics are being published:
   ```bash
   ros2 topic list
   ros2 topic echo /semantic_map
   ros2 topic echo /plan
   ```
2. Check node connections:
   ```bash
   ros2 node info /performance_dashboard
   ```

### psutil Not Found

If you get import errors:
```bash
pip3 install psutil
```

## Performance Considerations

### Update Rate

- **1 Hz (default)**: Good balance for most applications
- **2-5 Hz**: For more responsive monitoring
- **0.5 Hz**: For resource-constrained systems

### Resource Usage

The dashboard itself is lightweight:
- CPU: ~1-2% on typical systems
- Memory: ~50-100 MB
- Network: Minimal (only publishes at update_rate)

## Examples

### Monitor High-Performance Navigation

```bash
ros2 launch robot_semantic_slam cutting_edge_features.launch.py \
    use_performance_dashboard:=true \
    update_rate:=2.0
```

### Conservative Resource Monitoring

```bash
ros2 launch robot_semantic_slam performance_dashboard.launch.py \
    cpu_warning_threshold:=60.0 \
    cpu_critical_threshold:=75.0 \
    memory_warning_threshold:=70.0 \
    memory_critical_threshold:=85.0
```

### Subscribe to Alerts

```bash
ros2 topic echo /performance_alerts
```

### View Metrics JSON

```bash
ros2 topic echo /performance_metrics_json
```

## Future Enhancements

Planned improvements:
- Historical metrics logging
- Trend analysis and prediction
- Custom metric plugins
- Web-based dashboard interface
- Integration with cloud monitoring services

## Related Documentation

- [Enhanced Visualization Guide](RVIZ_3D_VISUALIZATION_GUIDE.md)
- [Advanced Safety System](BEHAVIOR_TREE_SAFETY.md)
- [Implementation Guide](IMPLEMENTATION_GUIDE.md)
- [Troubleshooting](TROUBLESHOOTING.md)
