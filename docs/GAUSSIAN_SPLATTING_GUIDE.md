# Gaussian Splatting Reconstruction - User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [What is Gaussian Splatting?](#what-is-gaussian-splatting)
3. [System Architecture](#system-architecture)
4. [Getting Started](#getting-started)
5. [Understanding the Pipeline](#understanding-the-pipeline)
6. [Export Formats](#export-formats)
7. [Visualization](#visualization)
8. [Performance Tuning](#performance-tuning)
9. [Advanced Usage](#advanced-usage)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)

## Introduction

This guide provides comprehensive documentation for the Gaussian Splatting reconstruction system integrated into the robot platform. The system generates photorealistic 3D scene representations from synchronized camera and LiDAR sensor data during autonomous mapping operations.

### Who Should Read This Guide

- Robotics researchers working with 3D reconstruction
- Developers integrating Gaussian Splatting into applications
- Users wanting to create digital twins of mapped environments
- Anyone interested in understanding the reconstruction pipeline

### Prerequisites

- Basic understanding of ROS2 concepts (nodes, topics, services)
- Familiarity with 3D coordinate systems and transformations
- Understanding of camera and LiDAR sensor principles
- Python programming knowledge (for advanced customization)

## What is Gaussian Splatting?

### Overview

Gaussian Splatting is a modern 3D scene representation technique that models environments as collections of 3D Gaussian primitives. Unlike traditional mesh or voxel representations, Gaussian Splatting provides:

- **Photorealistic rendering**: High-quality visual appearance
- **Efficient storage**: Compact representation of complex scenes
- **Fast rendering**: Real-time visualization capabilities
- **Differentiable**: Enables optimization and learning

### Gaussian Primitives

Each Gaussian primitive in the reconstruction is defined by four key attributes:

1. **Position** (x, y, z): 3D location in space (meters)
2. **Covariance**: 3x3 matrix defining shape and orientation
3. **Color** (r, g, b): RGB color values (0-255)
4. **Opacity**: Transparency value (0.0-1.0)

### How It Works

The reconstruction process follows these steps:

1. **Sensor Synchronization**: Align camera images with LiDAR point clouds in time
2. **3D Point Extraction**: Get 3D positions from LiDAR data
3. **Color Projection**: Project camera colors onto 3D points using calibration
4. **Covariance Computation**: Analyze local geometry to determine Gaussian shape
5. **Opacity Assignment**: Set transparency based on point density
6. **Accumulation**: Add new primitives to the growing reconstruction

### Applications

- **Digital Twins**: Create virtual replicas of real environments
- **Simulation**: Generate realistic training environments
- **Visualization**: Photorealistic rendering of mapped spaces
- **Analysis**: Study environment structure and appearance
- **Archival**: Preserve 3D records of spaces over time

## System Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│              Gaussian Splatting System                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Camera ──┐                                             │
│           ├──> Sensor Synchronizer                      │
│  LiDAR  ──┘         │                                   │
│                     ↓                                    │
│              Splat Generator                             │
│                     │                                    │
│                     ↓                                    │
│           Reconstruction Manager                         │
│                     │                                    │
│          ┌──────────┴──────────┐                        │
│          ↓                     ↓                         │
│   Visualization          Export (PLY/JSON)               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Input**: Camera images and LiDAR point clouds arrive asynchronously
2. **Synchronization**: Message filters align data within 50ms tolerance
3. **Processing**: Splat generator creates Gaussian primitives
4. **Storage**: Reconstruction manager accumulates primitives
5. **Output**: Visualization markers and export services provide access

### Key Components

- **SensorSynchronizer**: Handles temporal alignment of sensor streams
- **SplatGenerator**: Converts sensor data to Gaussian primitives
- **ReconstructionManager**: Manages primitive storage and export
- **VisualizationPublisher**: Provides real-time RViz feedback

## Getting Started

### Quick Start

1. **Launch the system**:
```bash
ros2 launch robot_gaussian_splat gaussian_splatting.launch.py use_rviz:=true
```

2. **Start mapping** (autonomous or manual control):
```bash
# Autonomous exploration
ros2 launch robot_navigation autonomous_exploration.launch.py

# Or manual control
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

3. **Monitor progress**:
```bash
ros2 topic echo /gaussian_splat/progress
```

4. **Save reconstruction**:
```bash
ros2 service call /gaussian_splat/save_model robot_gaussian_splat/srv/SaveSplatModel \
  "{filepath: '~/my_scene.ply', format: 'ply'}"
```

### Verifying Setup

Check that sensors are publishing:
```bash
ros2 topic list | grep -E "(camera|scan|points)"
ros2 topic hz /camera/image_raw
ros2 topic hz /scan
```

Check node is running:
```bash
ros2 node list | grep gaussian
ros2 node info /gaussian_splatting_node
```

Monitor diagnostics:
```bash
ros2 topic echo /gaussian_splat/diagnostics
```

## Understanding the Pipeline

### Sensor Synchronization

The system uses approximate time synchronization to align camera and LiDAR data:

- **Tolerance**: Default 50ms (configurable via `sync_tolerance`)
- **Algorithm**: ApproximateTimeSynchronizer from message_filters
- **Behavior**: Drops frames that can't be matched within tolerance

**Why synchronization matters**: Camera and LiDAR must capture the same scene state. Misaligned data produces incorrect color assignments and artifacts.

**Tuning tips**:
- Increase tolerance if sensors have timing jitter
- Decrease tolerance for fast-moving robots
- Monitor sync success rate in diagnostics

### Color Projection

Colors from camera images are projected onto 3D LiDAR points:

1. **Transform**: Convert 3D point to camera coordinate frame
2. **Project**: Apply camera intrinsics (pinhole model)
3. **Sample**: Extract RGB values from image at projected pixel
4. **Validate**: Ensure point is within camera field of view

**Requirements**:
- Accurate camera calibration (intrinsics)
- Proper camera-LiDAR extrinsic calibration
- Overlapping fields of view

### Covariance Computation

Covariance matrices define the shape and orientation of each Gaussian:

1. **Neighbor Search**: Find k-nearest neighbors (default k=10)
2. **PCA Analysis**: Compute principal components of local geometry
3. **Matrix Construction**: Build 3x3 covariance from eigenvalues/vectors
4. **Scaling**: Adjust based on local point density

**What covariance represents**:
- Large eigenvalues = elongated Gaussian
- Small eigenvalues = compact Gaussian
- Eigenvectors = principal axes of orientation

### Opacity Assignment

Opacity values indicate primitive confidence and density:

- **High opacity**: Dense point regions, high confidence
- **Low opacity**: Sparse regions, lower confidence
- **Computation**: Based on local point density within radius
- **Range**: Configurable min/max values (default 0.3-1.0)

### Accumulation and Downsampling

Primitives accumulate over time as the robot explores:

- **Storage**: Octree spatial indexing for efficient queries
- **Threshold**: Automatic downsampling at max_primitives (default 1M)
- **Method**: Voxel grid filtering with adaptive voxel size
- **Preservation**: Maintains spatial coverage while reducing count

## Export Formats

### PLY Format

The PLY (Polygon File Format) is a standard 3D data format:

**Structure**:
```
ply
format binary_little_endian 1.0
element vertex <count>
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
property float cov_xx
property float cov_xy
property float cov_xz
property float cov_yy
property float cov_yz
property float cov_zz
property float opacity
end_header
<binary data>
```

**Usage**:
```bash
ros2 service call /gaussian_splat/save_model robot_gaussian_splat/srv/SaveSplatModel \
  "{filepath: '/home/user/scene.ply', format: 'ply'}"
```

**Viewing PLY files**:
- MeshLab: `meshlab scene.ply`
- CloudCompare: `CloudCompare scene.ply`
- Blender: Import > Stanford PLY

**Advantages**:
- Standard format, widely supported
- Compact binary encoding
- Includes all Gaussian attributes
- Compatible with most 3D tools

### JSON Format

JSON export provides maximum flexibility and readability:

**Structure**:
```json
{
  "metadata": {
    "creation_time": "2025-11-15T10:30:00",
    "primitive_count": 125000,
    "bounds_min": [-10.0, -8.0, 0.0],
    "bounds_max": [10.0, 8.0, 3.0],
    "frames_processed": 450
  },
  "primitives": [
    {
      "position": [1.5, 2.3, 0.8],
      "covariance": [[0.01, 0.0, 0.0], [0.0, 0.01, 0.0], [0.0, 0.0, 0.005]],
      "color": [128, 200, 150],
      "opacity": 0.85,
      "timestamp": 1234567890.123
    },
    ...
  ]
}
```

**Usage**:
```bash
ros2 service call /gaussian_splat/save_model robot_gaussian_splat/srv/SaveSplatModel \
  "{filepath: '/home/user/scene.json', format: 'json'}"
```

**Advantages**:
- Human-readable
- Easy to parse in any language
- Includes metadata
- Suitable for custom processing

**Disadvantages**:
- Larger file size
- Slower to read/write
- Not supported by standard 3D viewers

### Choosing a Format

| Use Case | Recommended Format |
|----------|-------------------|
| Visualization in 3D tools | PLY |
| Custom processing/analysis | JSON |
| Archival storage | PLY (smaller) |
| Debugging | JSON (readable) |
| Integration with other systems | JSON |
| Maximum compatibility | PLY |

## Visualization

### RViz Configuration

The package includes a pre-configured RViz setup:

```bash
ros2 launch robot_gaussian_splat gaussian_splatting.launch.py use_rviz:=true
```

**Display elements**:
- **MarkerArray**: Gaussian primitives as colored spheres
- **Camera**: Camera image feed
- **PointCloud2**: LiDAR point cloud
- **TF**: Coordinate frame transforms

### Understanding the Visualization

**Marker representation**:
- Each Gaussian is shown as a sphere
- Sphere color = primitive RGB color
- Sphere size = based on covariance (larger = more spread out)
- Transparency = primitive opacity

**Performance considerations**:
- Only `visualization_limit` primitives shown (default 10,000)
- Update rate controlled by `visualization_rate` (default 1 Hz)
- Disable for better performance: `visualization_enabled: false`

### Custom Visualization

Create your own RViz config:

1. Launch with default config
2. Adjust displays, views, and settings
3. Save: File > Save Config As
4. Use custom config:
```bash
rviz2 -d /path/to/my_config.rviz
```

### Real-Time Monitoring

Monitor reconstruction progress:

```bash
# Primitive count
ros2 topic echo /gaussian_splat/diagnostics

# Progress percentage
ros2 topic echo /gaussian_splat/progress

# Statistics
ros2 service call /gaussian_splat/get_stats robot_gaussian_splat/srv/GetSplatStats
```

## Performance Tuning

### Memory Optimization

**Problem**: High memory usage or out-of-memory errors

**Solutions**:

1. **Reduce max primitives**:
```yaml
max_primitives: 500000  # Default: 1000000
```

2. **Disable visualization**:
```yaml
visualization_enabled: false
```

3. **Periodic clearing**:
```bash
# Save current reconstruction
ros2 service call /gaussian_splat/save_model ... "{filepath: 'part1.ply', format: 'ply'}"

# Clear and continue
ros2 service call /gaussian_splat/clear_model std_srvs/srv/Trigger
```

### CPU Optimization

**Problem**: High CPU usage, dropped frames

**Solutions**:

1. **Reduce visualization rate**:
```yaml
visualization_rate: 0.5  # Default: 1.0 Hz
```

2. **Limit visualization primitives**:
```yaml
visualization_limit: 5000  # Default: 10000
```

3. **Increase sync tolerance** (reduces processing frequency):
```yaml
sync_tolerance: 0.1  # Default: 0.05
```

4. **Lower sensor data rates** at source

### Quality vs Performance Trade-offs

| Priority | Configuration |
|----------|---------------|
| **Maximum Quality** | max_primitives: 2000000<br>neighbor_count: 15<br>neighbor_radius: 0.05<br>visualization_enabled: false |
| **Balanced** | max_primitives: 1000000<br>neighbor_count: 10<br>neighbor_radius: 0.1<br>visualization_enabled: true |
| **Maximum Performance** | max_primitives: 500000<br>neighbor_count: 8<br>neighbor_radius: 0.15<br>visualization_enabled: false |

### Benchmarking

Monitor system performance:

```bash
# CPU usage
top -p $(pgrep -f gaussian_splatting_node)

# Memory usage
ros2 service call /gaussian_splat/get_stats robot_gaussian_splat/srv/GetSplatStats

# Processing rate
ros2 topic hz /gaussian_splat/visualization

# Frame sync rate
ros2 topic echo /gaussian_splat/diagnostics | grep sync_rate
```

## Advanced Usage

### Custom Topic Remapping

Use different sensor topics:

```bash
ros2 launch robot_gaussian_splat gaussian_splatting.launch.py \
  camera_topic:=/front_camera/image_raw \
  camera_info_topic:=/front_camera/camera_info \
  pointcloud_topic:=/velodyne_points
```

### Parameter Tuning at Runtime

Adjust parameters while running:

```bash
# List all parameters
ros2 param list /gaussian_splatting_node

# Get current value
ros2 param get /gaussian_splatting_node max_primitives

# Set new value
ros2 param set /gaussian_splatting_node max_primitives 750000
```

### Programmatic Control

Control the system from Python:

```python
import rclpy
from rclpy.node import Node
from robot_gaussian_splat.srv import SaveSplatModel, GetSplatStats
from std_srvs.srv import Trigger

class GaussianSplatController(Node):
    def __init__(self):
        super().__init__('splat_controller')
        self.save_client = self.create_client(SaveSplatModel, '/gaussian_splat/save_model')
        self.stats_client = self.create_client(GetSplatStats, '/gaussian_splat/get_stats')
        self.clear_client = self.create_client(Trigger, '/gaussian_splat/clear_model')
    
    def save_reconstruction(self, filepath, format='ply'):
        request = SaveSplatModel.Request()
        request.filepath = filepath
        request.format = format
        future = self.save_client.call_async(request)
        return future
    
    def get_stats(self):
        request = GetSplatStats.Request()
        future = self.stats_client.call_async(request)
        return future
    
    def clear_reconstruction(self):
        request = Trigger.Request()
        future = self.clear_client.call_async(request)
        return future

# Usage
rclpy.init()
controller = GaussianSplatController()
future = controller.save_reconstruction('/home/user/scene.ply')
rclpy.spin_until_future_complete(controller, future)
result = future.result()
print(f"Saved {result.primitive_count} primitives")
```

### Batch Processing

Process multiple mapping sessions:

```bash
#!/bin/bash
# batch_reconstruct.sh

SESSIONS=("session1" "session2" "session3")

for session in "${SESSIONS[@]}"; do
    echo "Processing $session..."
    
    # Play back recorded data
    ros2 bag play ${session}.bag &
    BAG_PID=$!
    
    # Wait for completion
    wait $BAG_PID
    
    # Save reconstruction
    ros2 service call /gaussian_splat/save_model robot_gaussian_splat/srv/SaveSplatModel \
      "{filepath: '${session}_reconstruction.ply', format: 'ply'}"
    
    # Clear for next session
    ros2 service call /gaussian_splat/clear_model std_srvs/srv/Trigger
    
    sleep 2
done
```

### Integration with Other Systems

Export and use in external applications:

```python
# Load PLY in Python
from plyfile import PlyData

ply_data = PlyData.read('reconstruction.ply')
vertices = ply_data['vertex']

positions = np.column_stack([vertices['x'], vertices['y'], vertices['z']])
colors = np.column_stack([vertices['red'], vertices['green'], vertices['blue']])
opacities = vertices['opacity']

# Use in your application
# ...
```

```python
# Load JSON in Python
import json

with open('reconstruction.json', 'r') as f:
    data = json.load(f)

metadata = data['metadata']
primitives = data['primitives']

for primitive in primitives:
    position = primitive['position']
    color = primitive['color']
    # Process primitive
    # ...
```

## Best Practices

### Data Collection

1. **Move slowly**: Fast motion causes blur and sync issues
2. **Good lighting**: Adequate illumination for camera
3. **Overlap coverage**: Revisit areas from multiple angles
4. **Stable platform**: Minimize vibration and shaking
5. **Calibration**: Ensure sensors are properly calibrated

### Sensor Setup

1. **Field of view overlap**: Camera and LiDAR must see same regions
2. **Mounting**: Rigid mounting, avoid flex or movement
3. **Synchronization**: Use hardware sync if available
4. **Frame rates**: Match camera and LiDAR rates when possible
5. **Resolution**: Higher resolution = better quality (but slower)

### Reconstruction Quality

1. **Complete coverage**: Map entire area thoroughly
2. **Multiple passes**: Revisit areas for better coverage
3. **Varied viewpoints**: Capture from different angles
4. **Avoid dynamic objects**: Moving objects create artifacts
5. **Consistent lighting**: Avoid dramatic lighting changes

### Resource Management

1. **Monitor memory**: Check stats regularly
2. **Save periodically**: Don't lose work to crashes
3. **Clear when needed**: Reset for new areas
4. **Disable viz**: Turn off visualization for large reconstructions
5. **Tune parameters**: Adjust based on your hardware

### Workflow Recommendations

1. **Test first**: Small test area before full mapping
2. **Incremental saves**: Save progress regularly
3. **Backup exports**: Keep multiple copies
4. **Document settings**: Record parameters used
5. **Validate results**: Check exports in viewer

## Troubleshooting

### Common Issues

#### Issue: No primitives generated

**Symptoms**: Reconstruction count stays at 0

**Diagnosis**:
```bash
# Check topics
ros2 topic list | grep -E "(camera|scan)"
ros2 topic hz /camera/image_raw
ros2 topic hz /scan

# Check synchronization
ros2 topic echo /gaussian_splat/diagnostics | grep sync
```

**Solutions**:
- Verify sensor topics are publishing
- Check topic names in configuration
- Increase sync_tolerance
- Verify camera and LiDAR FOV overlap

#### Issue: Poor color quality

**Symptoms**: Colors are wrong, black, or washed out

**Diagnosis**:
- Check camera image quality: `ros2 run rqt_image_view rqt_image_view`
- Verify camera calibration
- Check lighting conditions

**Solutions**:
- Recalibrate camera
- Improve lighting
- Adjust camera exposure settings
- Verify camera-LiDAR extrinsic calibration

#### Issue: Sparse reconstruction

**Symptoms**: Many gaps, incomplete coverage

**Diagnosis**:
- Check LiDAR point cloud density
- Verify coverage of mapped area
- Check downsampling threshold

**Solutions**:
- Move slower for better coverage
- Increase max_primitives
- Revisit areas from multiple angles
- Check LiDAR is functioning properly

#### Issue: High memory usage

**Symptoms**: System slow, out of memory errors

**Diagnosis**:
```bash
ros2 service call /gaussian_splat/get_stats robot_gaussian_splat/srv/GetSplatStats
```

**Solutions**:
- Reduce max_primitives
- Disable visualization
- Clear and save periodically
- Increase downsampling frequency

#### Issue: Synchronization failures

**Symptoms**: Many dropped frames, low sync rate

**Diagnosis**:
```bash
ros2 topic echo /gaussian_splat/diagnostics
```

**Solutions**:
- Increase sync_tolerance
- Check sensor timing
- Reduce sensor data rates
- Use hardware synchronization if available

### Debug Mode

Enable detailed logging:

```bash
ros2 run robot_gaussian_splat gaussian_splatting_node --ros-args --log-level debug
```

View logs:
```bash
ros2 run robot_gaussian_splat gaussian_splatting_node --ros-args --log-level debug 2>&1 | tee gaussian_splat.log
```

### Getting Help

1. Check this guide thoroughly
2. Review package README
3. Check ROS2 logs for errors
4. Verify sensor data quality
5. Test with simpler scenarios first

## Conclusion

This guide covers the essential aspects of using the Gaussian Splatting reconstruction system. For additional information:

- Package README: `src/robot_gaussian_splat/README.md`
- Design document: `.kiro/specs/gaussian-splatting-reconstruction/design.md`
- Requirements: `.kiro/specs/gaussian-splatting-reconstruction/requirements.md`

Happy reconstructing!
