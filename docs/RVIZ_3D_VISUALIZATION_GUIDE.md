# RViz 3D Point Cloud Visualization Guide

## Overview

This guide explains how to use the enhanced RViz configuration for 3D point cloud visualization with the Dojo robot.

## Quick Start

### Launch with 3D Visualization

```bash
# Start robot with enhanced visualization
python3 start_cutting_edge_robot.py

# RViz will automatically open with 3D point cloud configuration
```

## RViz Configuration

### Displays Included

1. **Grid** - Reference grid in map frame
2. **RobotModel** - 3D robot model
3. **TF** - Transform frames visualization
4. **Map** - 2D occupancy grid map
5. **PointCloud Real-Time** - Live 2D scan as 3D points (enabled by default)
6. **PointCloud Dense Map** - Accumulated 3D dense map (toggle on/off)
7. **Human Safety Markers** - Human detection visualization
8. **Threat Markers** - Safety threat visualization
9. **Safety Markers** - General safety markers
10. **Path** - Navigation path

### Toggle Between Views

#### Real-Time View (Default)
- **Topic:** `/pointcloud`
- **Update Rate:** 10 Hz
- **Description:** Live 2D LiDAR scan converted to 3D points
- **Use Case:** Real-time obstacle detection

**To Enable:**
1. In RViz Displays panel
2. Check "PointCloud Real-Time"
3. Uncheck "PointCloud Dense Map"

#### Dense Map View
- **Topic:** `/dense_map`
- **Update Rate:** 10 Hz
- **Description:** Accumulated scans over 10 seconds
- **Use Case:** Dense 3D mapping, environment reconstruction

**To Enable:**
1. In RViz Displays panel
2. Uncheck "PointCloud Real-Time"
3. Check "PointCloud Dense Map"

#### Both Views (Comparison)
- Enable both displays simultaneously
- Real-time shows current scan
- Dense map shows accumulated history

### Color Scheme Configuration

#### Height-Based Coloring (Default)
- **Red:** Low points (-0.5m)
- **Orange:** Below ground level
- **Yellow:** Ground level (0m)
- **Green:** Mid-height (0.5-1.0m)
- **Blue:** High points (1.0-1.5m)
- **Violet:** Very high points (2.0m+)

#### Adjust Color Settings

**In PointCloud Display:**
1. Expand "PointCloud Real-Time" or "PointCloud Dense Map"
2. **Color Transformer:** RGB8 (uses height-based colors from node)
3. **Size (m):** 0.05 (adjust point size)
4. **Style:** Points (or Flat Squares, Spheres, Boxes)

**Change Point Size:**
- Small points (0.03m): Better for dense maps
- Medium points (0.05m): Default, good balance
- Large points (0.1m): Better visibility for sparse data

### View Configuration

#### Orbit View (Default)
- **Distance:** 10m from focal point
- **Pitch:** 45° (0.785 radians)
- **Yaw:** 45° (0.785 radians)
- **Focal Point:** Origin (0, 0, 0)

#### Adjust View
- **Rotate:** Left-click + drag
- **Pan:** Middle-click + drag
- **Zoom:** Scroll wheel
- **Reset:** Views → Current View → Reset

#### Recommended Views

**Top-Down View:**
- Pitch: 90° (1.57 radians)
- Yaw: 0°
- Distance: 15m
- Good for: Navigation, path planning

**Side View:**
- Pitch: 0°
- Yaw: 0° or 90°
- Distance: 10m
- Good for: Height visualization, 3D structure

**Isometric View:**
- Pitch: 45°
- Yaw: 45°
- Distance: 10m
- Good for: General 3D visualization

## Performance Optimization

### Target Performance
- **Update Rate:** 10 Hz
- **Frame Rate:** 30 FPS
- **Latency:** < 100ms

### If Performance is Slow

1. **Reduce Point Size**
   ```
   Size (m): 0.03 (instead of 0.05)
   ```

2. **Disable Dense Map**
   - Uncheck "PointCloud Dense Map"
   - Only use real-time view

3. **Reduce Accumulation Time**
   ```bash
   # Edit launch file parameter
   'accumulation_time': 5.0  # Reduce from 10.0
   ```

4. **Increase Voxel Size**
   ```bash
   # Edit launch file parameter
   'voxel_size': 0.1  # Increase from 0.05
   ```

5. **Limit Max Points**
   ```bash
   # Edit launch file parameter
   'max_points': 500000  # Reduce from 1000000
   ```

## Customization

### Change Color Mode

Edit `enhanced_visualization.launch.py`:

```python
# Height-based (default)
'color_mode': 'height',
'color_scheme': 'rainbow',

# Intensity-based (grayscale)
'color_mode': 'intensity',

# Fixed color (gray)
'color_mode': 'fixed',

# Different color schemes
'color_scheme': 'jet',     # MATLAB-style
'color_scheme': 'hot',     # Thermal
'color_scheme': 'cool',    # Cyan-magenta
```

### Adjust Height Range

```python
'min_height': -0.5,  # Red color
'max_height': 2.0,   # Violet color
```

### Change Update Rate

```python
'update_rate': 20.0,  # Increase to 20 Hz (more CPU)
'update_rate': 5.0,   # Decrease to 5 Hz (less CPU)
```

## Troubleshooting

### No Point Cloud Visible

**Check:**
1. PointCloud display is enabled (checkbox checked)
2. Correct topic selected (`/pointcloud` or `/dense_map`)
3. Robot simulation is running
4. PointCloud Processor node is running

**Verify:**
```bash
# Check if pointcloud is being published
ros2 topic hz /pointcloud

# Should show ~10 Hz
```

### Point Cloud is All One Color

**Cause:** Color transformer not set to RGB8

**Fix:**
1. Expand PointCloud display
2. Color Transformer → RGB8
3. Should now show height-based colors

### Performance Issues

**Symptoms:**
- Low frame rate (< 10 FPS)
- Laggy visualization
- High CPU usage

**Solutions:**
1. Reduce point size (0.03m)
2. Disable dense map view
3. Reduce accumulation time (5s)
4. Increase voxel size (0.1m)
5. Close other applications

### Points Appear Flat

**Expected for Real-Time View:**
- 2D LiDAR scan at fixed height
- Points form horizontal arc
- This is normal behavior

**For 3D Effect:**
- Enable "PointCloud Dense Map"
- Move robot around
- Scans accumulate at different positions
- Creates 3D structure over time

### Dense Map Not Updating

**Check:**
1. Accumulation enabled in launch file
2. Robot is moving (scans from different positions)
3. TF transforms available

**Verify:**
```bash
# Check dense map topic
ros2 topic hz /dense_map

# Check TF
ros2 run tf2_ros tf2_echo map base_link
```

## Advanced Features

### Save Current View

1. Views → Current View
2. Note down Distance, Pitch, Yaw values
3. Or: File → Save Config As...

### Custom RViz Config

1. Modify displays as desired
2. File → Save Config As...
3. Save to: `src/robot_gazebo/rviz/my_config.rviz`
4. Update launch file to use your config

### Multiple Point Cloud Layers

Enable both displays with different settings:
- Real-time: Small points (0.03m), high opacity
- Dense map: Medium points (0.05m), lower opacity
- Creates layered visualization

### Record and Playback

```bash
# Record point clouds
ros2 bag record /pointcloud /dense_map

# Playback
ros2 bag play <bag_file>
# Open RViz to visualize recorded data
```

## Keyboard Shortcuts

- **F5:** Reload configuration
- **Ctrl+S:** Save configuration
- **Ctrl+O:** Open configuration
- **Spacebar:** Pause/resume updates
- **R:** Reset view
- **G:** Toggle grid
- **T:** Toggle TF display

## Tips and Best Practices

1. **Start with Real-Time View**
   - Easier to understand
   - Lower resource usage
   - Good for debugging

2. **Use Dense Map for Mapping**
   - Drive robot around environment
   - Watch 3D structure build up
   - Great for environment understanding

3. **Adjust Colors for Your Environment**
   - Indoor: Default range (-0.5 to 2.0m)
   - Outdoor: Wider range (-1.0 to 5.0m)
   - Flat terrain: Narrow range (0 to 0.5m)

4. **Monitor Performance**
   - Keep frame rate above 10 FPS
   - Adjust settings if laggy
   - Balance quality vs performance

5. **Save Useful Configurations**
   - Save different configs for different tasks
   - Navigation config
   - Mapping config
   - Debugging config

## Related Documentation

- **Task 3.1:** PointCloud Processor Node
- **Task 3.2:** Scan Accumulation
- **Task 3.3:** Height-Based Color Mapping
- **Task 3.5:** Performance Optimization

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review task verification docs
3. Check ROS2 topic outputs
4. Verify node status
