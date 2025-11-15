# Robot Gaussian Splat

ROS2 package for generating 3D Gaussian Splatting reconstructions from synchronized camera and LiDAR sensor data.

## Overview

This package enables photorealistic 3D scene reconstruction using Gaussian Splatting techniques. It processes synchronized camera images and LiDAR point clouds to generate a collection of 3D Gaussian primitives that represent the mapped environment.

Gaussian Splatting represents 3D scenes as collections of oriented 3D Gaussians, each with position, color, covariance (shape/orientation), and opacity. This representation enables high-quality rendering and efficient scene representation for robotics applications including digital twins, simulation, and visualization.

## Features

- Real-time Gaussian primitive generation from sensor data
- Temporal synchronization of camera and LiDAR streams (50ms tolerance)
- Automatic covariance computation from local point cloud geometry
- Color projection from camera images to 3D points
- Persistent reconstruction accumulation during mapping
- Export to PLY and JSON formats
- RViz visualization of reconstruction progress
- Automatic downsampling for memory management (configurable threshold)
- Robust error handling for corrupted or missing sensor data
- Diagnostic monitoring and progress reporting

## System Requirements

- ROS2 Humble or later
- Python 3.10+
- Ubuntu 22.04 or later (recommended)
- 8GB+ RAM (16GB recommended for large reconstructions)
- Camera and LiDAR sensors with overlapping fields of view

## Dependencies

### ROS2 Packages
- `rclpy` - ROS2 Python client library
- `sensor_msgs` - Image and PointCloud2 messages
- `visualization_msgs` - Marker messages for RViz
- `diagnostic_msgs` - System diagnostics
- `message_filters` - Time synchronization
- `cv_bridge` - OpenCV-ROS bridge
- `tf2_ros` - Transform handling
- `std_srvs` - Standard service definitions

### Python Libraries
- `numpy>=1.21.0` - Numerical operations
- `opencv-python>=4.5.0` - Image processing
- `scipy>=1.7.0` - Spatial operations (KDTree)
- `open3d>=0.13.0` - Point cloud processing
- `plyfile>=0.7.4` - PLY format export

## Installation

### Quick Install

1. Ensure you're in your ROS2 workspace:
```bash
cd ~/ros2_ws/src
```

2. Install Python dependencies:
```bash
pip3 install numpy opencv-python scipy open3d plyfile
```

3. Build the package:
```bash
cd ~/ros2_ws
colcon build --packages-select robot_gaussian_splat
source install/setup.bash
```

### Verify Installation

Check that the package is properly installed:
```bash
ros2 pkg list | grep robot_gaussian_splat
```

Test the node can be launched:
```bash
ros2 run robot_gaussian_splat gaussian_splatting_node --ros-args -h
```

## Usage

### Basic Launch

Launch the Gaussian Splatting node with default parameters:

```bash
ros2 launch robot_gaussian_splat gaussian_splatting.launch.py
```

### Launch with Custom Parameters

Override default parameters at launch time:

```bash
ros2 launch robot_gaussian_splat gaussian_splatting.launch.py \
  camera_topic:=/my_camera/image_raw \
  pointcloud_topic:=/my_lidar/points \
  visualization_enabled:=true
```

### Launch with RViz Visualization

Launch with RViz for real-time visualization:

```bash
ros2 launch robot_gaussian_splat gaussian_splatting.launch.py use_rviz:=true
```

### Integration with Robot System

To use with the complete robot system:

```bash
ros2 launch robot_semantic_slam cutting_edge_features.launch.py
```

This launches Gaussian Splatting alongside other advanced features.

## Service Calls

### Save the Reconstruction Model

Export the reconstruction to PLY format:

```bash
ros2 service call /gaussian_splat/save_model robot_gaussian_splat/srv/SaveSplatModel \
  "{filepath: '/home/user/reconstruction.ply', format: 'ply'}"
```

Export to JSON format:

```bash
ros2 service call /gaussian_splat/save_model robot_gaussian_splat/srv/SaveSplatModel \
  "{filepath: '/home/user/reconstruction.json', format: 'json'}"
```

### Get Reconstruction Statistics

Query current reconstruction statistics:

```bash
ros2 service call /gaussian_splat/get_stats robot_gaussian_splat/srv/GetSplatStats
```

This returns:
- Total primitive count
- Memory usage in MB
- Scene bounds (min/max coordinates)
- Number of frames processed

### Clear the Reconstruction

Reset the reconstruction and start fresh:

```bash
ros2 service call /gaussian_splat/clear_model std_srvs/srv/Trigger
```

## Example Workflow

Here's a typical workflow for creating a Gaussian Splat reconstruction:

1. **Start the robot simulation or hardware**:
```bash
ros2 launch robot_gazebo complete_robot_simulation.launch.py
```

2. **Launch Gaussian Splatting**:
```bash
ros2 launch robot_gaussian_splat gaussian_splatting.launch.py use_rviz:=true
```

3. **Drive the robot around** to collect data (use autonomous exploration or manual control)

4. **Monitor progress** in RViz or via diagnostics:
```bash
ros2 topic echo /gaussian_splat/progress
```

5. **Save the reconstruction** when complete:
```bash
ros2 service call /gaussian_splat/save_model robot_gaussian_splat/srv/SaveSplatModel \
  "{filepath: '~/my_reconstruction.ply', format: 'ply'}"
```

6. **View the saved model** using external tools (MeshLab, CloudCompare, etc.)

## Configuration

Configuration parameters are defined in `config/gaussian_splatting_params.yaml`. You can modify these values to tune performance and behavior.

### Core Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sync_tolerance` | float | 0.05 | Time synchronization tolerance in seconds. Camera and LiDAR data must be within this window to be processed together. |
| `max_primitives` | int | 1000000 | Maximum number of primitives before automatic downsampling is triggered. |
| `camera_topic` | string | `/camera/image_raw` | Topic name for camera RGB images. |
| `camera_info_topic` | string | `/camera/camera_info` | Topic name for camera calibration info. |
| `pointcloud_topic` | string | `/scan` | Topic name for LiDAR point cloud data. |

### Visualization Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `visualization_enabled` | bool | true | Enable/disable real-time RViz visualization. Disable for better performance. |
| `visualization_rate` | float | 1.0 | Rate (Hz) at which visualization markers are published. Lower values reduce CPU load. |
| `visualization_limit` | int | 10000 | Maximum number of primitives to visualize. Higher values may impact RViz performance. |

### Advanced Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `neighbor_count` | int | 10 | Number of neighbors used for covariance computation. |
| `neighbor_radius` | float | 0.1 | Search radius (meters) for finding neighbors. |
| `min_opacity` | float | 0.3 | Minimum opacity value for generated primitives. |
| `max_opacity` | float | 1.0 | Maximum opacity value for generated primitives. |

### Editing Configuration

To modify parameters, edit the config file:

```bash
nano ~/ros2_ws/src/robot_gaussian_splat/config/gaussian_splatting_params.yaml
```

Or override at launch time:

```bash
ros2 launch robot_gaussian_splat gaussian_splatting.launch.py \
  sync_tolerance:=0.1 \
  max_primitives:=500000
```

## Topics

### Subscribed Topics
- `/camera/image_raw` (sensor_msgs/Image): RGB camera feed
- `/camera/camera_info` (sensor_msgs/CameraInfo): Camera calibration
- `/scan` or `/velodyne_points` (sensor_msgs/PointCloud2): LiDAR data

### Published Topics
- `/gaussian_splat/visualization` (visualization_msgs/MarkerArray): RViz markers
- `/gaussian_splat/diagnostics` (diagnostic_msgs/DiagnosticArray): System status
- `/gaussian_splat/progress` (std_msgs/Float32): Reconstruction progress

## Services

- `/gaussian_splat/save_model` (SaveSplatModel): Export reconstruction
- `/gaussian_splat/clear_model` (std_srvs/Trigger): Reset reconstruction
- `/gaussian_splat/get_stats` (GetSplatStats): Query model statistics

## Visualization

The package includes RViz configuration for visualizing the Gaussian Splatting reconstruction:

```bash
rviz2 -d $(ros2 pkg prefix robot_gaussian_splat)/share/robot_gaussian_splat/rviz/gaussian_splat_visualization.rviz
```

## Export Formats

### PLY Format
Standard PLY format with custom properties for Gaussian attributes:
- Position (x, y, z)
- Color (r, g, b)
- Covariance matrix elements
- Opacity

### JSON Format
Complete primitive parameters in JSON format for maximum flexibility and compatibility with custom tools.

## Performance Considerations

- Memory usage scales with the number of primitives
- Automatic downsampling triggers at configurable thresholds
- Visualization is limited to a subset of primitives for performance
- Processing rate depends on sensor data frequency and point cloud density

## Troubleshooting

### No Primitives Being Generated

**Symptoms**: The node runs but no primitives are created, reconstruction count stays at 0.

**Possible Causes**:
- Camera and LiDAR topics are not publishing data
- Topic names are incorrect
- Sensor data is not synchronized within tolerance
- Camera and LiDAR fields of view don't overlap

**Solutions**:
1. Verify topics are publishing:
```bash
ros2 topic list
ros2 topic hz /camera/image_raw
ros2 topic hz /scan
```

2. Check topic remapping in launch file or parameters

3. Increase sync tolerance if sensors have timing issues:
```bash
ros2 param set /gaussian_splatting_node sync_tolerance 0.1
```

4. Verify sensor calibration and mounting positions

### High Memory Usage

**Symptoms**: System runs out of memory, node crashes, or becomes slow.

**Possible Causes**:
- Too many primitives accumulated
- Downsampling threshold too high
- Memory leak

**Solutions**:
1. Reduce max_primitives parameter:
```bash
ros2 param set /gaussian_splatting_node max_primitives 500000
```

2. Clear reconstruction periodically:
```bash
ros2 service call /gaussian_splat/clear_model std_srvs/srv/Trigger
```

3. Disable visualization to save memory:
```bash
ros2 param set /gaussian_splatting_node visualization_enabled false
```

### Poor Reconstruction Quality

**Symptoms**: Reconstruction looks sparse, noisy, or has incorrect colors.

**Possible Causes**:
- Poor sensor calibration
- Insufficient overlap between camera and LiDAR FOV
- Fast robot motion causing blur
- Low lighting conditions

**Solutions**:
1. Calibrate camera intrinsics properly
2. Ensure camera and LiDAR are well-aligned
3. Move robot slower during data collection
4. Improve lighting conditions
5. Adjust neighbor parameters for covariance computation

### Synchronization Warnings

**Symptoms**: Frequent warnings about dropped or misaligned frames.

**Possible Causes**:
- Sensors running at different rates
- Network delays (if using remote sensors)
- CPU overload

**Solutions**:
1. Increase sync_tolerance parameter
2. Reduce sensor data rates
3. Ensure sensors are on same clock (use time synchronization)
4. Reduce CPU load by disabling visualization

### Export Failures

**Symptoms**: Service call succeeds but file is not created or is corrupted.

**Possible Causes**:
- Invalid file path
- Insufficient disk space
- Permission issues

**Solutions**:
1. Use absolute paths for file exports
2. Check disk space: `df -h`
3. Verify write permissions: `ls -la /path/to/directory`
4. Try exporting to home directory first: `~/test.ply`

### RViz Visualization Issues

**Symptoms**: Markers not appearing in RViz or RViz is slow.

**Possible Causes**:
- Wrong frame_id
- Too many markers
- RViz not subscribed to correct topic

**Solutions**:
1. Verify frame_id matches your robot's coordinate frame
2. Reduce visualization_limit parameter
3. Check RViz is subscribed to `/gaussian_splat/visualization`
4. Reduce visualization_rate to lower CPU usage

## Performance Tuning

### For Real-Time Performance

- Disable visualization: `visualization_enabled: false`
- Reduce max_primitives: `max_primitives: 500000`
- Increase sync_tolerance if needed: `sync_tolerance: 0.1`
- Lower sensor data rates

### For Maximum Quality

- Increase max_primitives: `max_primitives: 2000000`
- Decrease neighbor_radius for finer detail: `neighbor_radius: 0.05`
- Increase neighbor_count: `neighbor_count: 15`
- Use higher resolution camera
- Slow down robot motion

### For Large Environments

- Enable periodic exports and clearing
- Use lower max_primitives with more frequent downsampling
- Disable real-time visualization
- Consider splitting environment into sections

## Additional Documentation

For more detailed information, see:
- `docs/GAUSSIAN_SPLATTING_GUIDE.md` - Comprehensive user guide with concepts and advanced usage
- Design document: `.kiro/specs/gaussian-splatting-reconstruction/design.md`
- Requirements: `.kiro/specs/gaussian-splatting-reconstruction/requirements.md`

## License

MIT License

## Authors

Robot Team

## Support

For issues and questions:
- Check the troubleshooting section above
- Review the detailed guide in `docs/GAUSSIAN_SPLATTING_GUIDE.md`
- Check ROS2 logs: `ros2 run robot_gaussian_splat gaussian_splatting_node --ros-args --log-level debug`
