# Vision Detection System Usage Guide

This guide explains how to use the vision detection system in simulation and with the real robot.

## Overview

The vision detection system provides real-time object detection capabilities using:
- **YOLO model** (primary) for accurate object detection
- **OpenCV DNN** (fallback) for basic detection when YOLO is unavailable
- **ROS2 integration** with proper message types and topic structure
- **Timestamp synchronization** between camera feed and detection results

## Topics

### Subscribed Topics
- `/camera/image_raw` - Raw camera images from Gazebo simulation or real camera
- `/camera/camera_info` - Camera calibration information

### Published Topics
- `/detections` - Object detections as `vision_msgs/Detection2DArray`
- `/camera/detection_image` - Annotated images with bounding boxes and labels

## Quick Start - Simulation

### 1. Launch Complete Simulation with Vision Detection

```bash
cd Dojo
source install/setup.bash
ros2 launch complete_simulation_with_vision.launch.py
```

This launches:
- Gazebo simulation with the robot
- Camera sensor publishing to `/camera/image_raw`
- Vision detection node processing camera feed
- RViz with camera and detection visualization
- SLAM for mapping
- Teleop control

**Note**: If you get "Address already in use" errors, kill existing Gazebo processes:
```bash
pkill -f gazebo
```

### 2. Launch Only Vision Detection (if robot is already running)

```bash
cd Dojo
source install/setup.bash
ros2 launch robot_perception vision_detection.launch.py
```

### 3. Manual Node Launch (for debugging)

```bash
cd Dojo
source install/setup.bash
ros2 run robot_perception vision_detection_node
```

## Configuration Parameters

You can customize the vision detection behavior:

```bash
# Launch with custom confidence threshold
ros2 launch robot_perception vision_detection.launch.py confidence_threshold:=0.7

# Enable debug mode for detailed logging
ros2 launch robot_perception vision_detection.launch.py debug_mode:=true

# Use with real robot (disable sim time)
ros2 launch robot_perception vision_detection.launch.py use_sim_time:=false
```

## Visualization in RViz

The system provides multiple visualization options:

1. **Raw Camera Feed** - Shows the original camera image
2. **Detection Image** - Shows camera image with bounding boxes and labels
3. **Detection Overlays** - 3D markers in the world (if available)

### RViz Setup
1. Open RViz with the provided configuration
2. Add Camera display for `/camera/image_raw` (raw feed)
3. Add Camera display for `/camera/detection_image` (annotated feed)
4. Add MarkerArray display for `/detection_markers` (3D overlays)

## Testing the System

### 1. Check Topics
```bash
# List all topics
ros2 topic list

# Check detection messages
ros2 topic echo /detections

# Check camera feed
ros2 topic echo /camera/image_raw --no-arr
```

### 2. Monitor Performance
```bash
# Check detection frequency
ros2 topic hz /detections

# Check camera feed frequency  
ros2 topic hz /camera/image_raw

# Monitor node status
ros2 node info /vision_detection_node
```

### 3. View Detection Results
```bash
# Print detection info in readable format
ros2 topic echo /detections --field detections
```

## Troubleshooting

### Common Issues

1. **No detections appearing**
   - Check if camera is publishing: `ros2 topic hz /camera/image_raw`
   - Verify detection node is running: `ros2 node list | grep vision`
   - Lower confidence threshold: `confidence_threshold:=0.3`

2. **NumPy/OpenCV compatibility warnings**
   - These are system-level warnings and don't affect functionality
   - The node will still work correctly despite the warnings

3. **YOLO model not loading**
   - The system automatically falls back to OpenCV DNN
   - Install ultralytics: `pip install ultralytics`

4. **No camera feed in simulation**
   - Ensure Gazebo is running with the robot spawned
   - Check robot URDF includes camera sensor
   - Verify camera plugin is loaded in Gazebo

### Debug Mode

Enable debug mode for detailed logging:
```bash
ros2 launch robot_perception vision_detection.launch.py debug_mode:=true
```

This provides:
- Frame processing statistics
- Detection count per frame
- Timestamp synchronization info
- Model initialization status

## Integration with Navigation

The vision detection system can be integrated with navigation for:
- **Obstacle avoidance** - Detect dynamic obstacles
- **Object following** - Follow specific detected objects  
- **Semantic navigation** - Navigate to specific object types

Example integration topics:
- Subscribe to `/detections` in navigation nodes
- Use detection positions for path planning
- Combine with laser scan data for robust obstacle detection

## Real Robot Usage

To use with a real robot:

1. **Update camera topics** if different from `/camera/image_raw`
2. **Disable simulation time**: `use_sim_time:=false`
3. **Adjust camera frame**: `camera_frame:=your_camera_frame`
4. **Tune confidence threshold** based on real-world performance

```bash
ros2 launch robot_perception vision_detection.launch.py \
    use_sim_time:=false \
    input_topic:=/your_camera/image_raw \
    camera_frame:=your_camera_optical_frame \
    confidence_threshold:=0.6
```

## Performance Notes

- **Detection frequency**: ~10-30 Hz depending on image size and model
- **Latency**: <100ms from image capture to detection publishing
- **Memory usage**: ~200-500MB depending on YOLO model size
- **CPU usage**: Moderate, scales with image resolution

## Next Steps

After getting basic detection working:
1. Add object tracking for temporal consistency
2. Integrate with robot behavior for object interaction
3. Add custom object classes for specific use cases
4. Implement 3D position estimation using depth information