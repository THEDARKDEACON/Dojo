# Semantic SLAM Quick Start Guide

## Overview

The semantic SLAM system combines YOLO object detection with SLAM mapping to create object-aware maps and enable natural language navigation.

---

## Quick Start

### 1. Launch the System

```bash
# Launch complete simulation with semantic SLAM
ros2 launch robot_semantic_slam cutting_edge_features.launch.py
```

This starts:
- Semantic SLAM node (YOLO + mapping)
- Semantic interface (natural language commands)
- Advanced safety system
- Enhanced visualizer

### 2. Send Natural Language Commands

```bash
# In a new terminal, send commands
ros2 topic pub /text_command std_msgs/msg/String "data: 'list objects'" --once
ros2 topic pub /text_command std_msgs/msg/String "data: 'go to chair'" --once
ros2 topic pub /text_command std_msgs/msg/String "data: 'find bottle'" --once
```

### 3. View Semantic Map

```bash
# View the semantic map in real-time
ros2 topic echo /semantic_map
```

### 4. View Annotated Images

```bash
# View annotated camera images with bounding boxes
ros2 run rqt_image_view rqt_image_view /semantic_image
```

---

## Supported Commands

### Navigation Commands
- `"go to chair"` - Navigate to nearest chair
- `"go to the table"` - Navigate to nearest table
- `"return home"` - Return to home position

### Search Commands
- `"find bottle"` - Locate all bottles in the map
- `"find person"` - Locate all people in the map

### Information Commands
- `"list objects"` - List all detected objects
- `"what do you see"` - Same as list objects
- `"status"` - Get robot status

### Movement Commands
- `"move forward"` - Move forward
- `"move backward"` - Move backward
- `"turn left"` - Turn left
- `"turn right"` - Turn right
- `"stop"` - Emergency stop

### Exploration Commands
- `"explore kitchen"` - Explore kitchen area
- `"map office"` - Map office area
- `"patrol hallway"` - Patrol hallway

---

## Detected Object Classes

The system can detect 80+ object classes from YOLO, including:

**Common Objects**:
- person, chair, table, bottle, cup, book
- laptop, mouse, keyboard, cell phone
- tv, couch, bed, dining table

**Kitchen Items**:
- refrigerator, oven, microwave, sink
- bowl, fork, knife, spoon

**Vehicles**:
- car, bicycle, motorcycle, bus, truck

**Animals**:
- dog, cat, bird, horse

And many more! See YOLO documentation for full list.

---

## ROS2 Topics Reference

### Subscribe to These Topics:

```bash
# Semantic map (JSON format)
ros2 topic echo /semantic_map

# Annotated images with bounding boxes
ros2 topic echo /semantic_image

# Navigation goals
ros2 topic echo /navigate_to_object

# Command responses
ros2 topic echo /semantic_response
```

### Publish to These Topics:

```bash
# Send text commands
ros2 topic pub /text_command std_msgs/msg/String "data: 'YOUR_COMMAND'"

# Send semantic commands directly
ros2 topic pub /semantic_command std_msgs/msg/String "data: 'go to chair'"
```

---

## Example Workflow

### 1. Start the Robot and Explore

```bash
# Terminal 1: Launch system
ros2 launch robot_semantic_slam cutting_edge_features.launch.py

# Terminal 2: Start exploration
ros2 topic pub /text_command std_msgs/msg/String "data: 'explore room'" --once
```

### 2. Check What Objects Were Detected

```bash
# List all detected objects
ros2 topic pub /text_command std_msgs/msg/String "data: 'list objects'" --once

# Or view the semantic map
ros2 topic echo /semantic_map --once
```

### 3. Navigate to a Specific Object

```bash
# Navigate to a chair
ros2 topic pub /text_command std_msgs/msg/String "data: 'go to chair'" --once
```

### 4. Monitor in RViz

The semantic objects are visualized in RViz as 3D markers with:
- Color-coded by object class
- Size based on confidence
- Text labels with class name and confidence

---

## Troubleshooting

### No Objects Detected

**Problem**: Semantic map is empty

**Solutions**:
1. Ensure camera is enabled in simulation
2. Check if objects are in camera view
3. Verify YOLO model is loaded: `yolov8n.pt`
4. Check camera topic: `ros2 topic echo /camera/image_raw`

### Commands Not Working

**Problem**: No response to text commands

**Solutions**:
1. Check if semantic interface is running: `ros2 node list | grep semantic`
2. Verify topic connection: `ros2 topic info /text_command`
3. Check for typos in command syntax

### Navigation Not Working

**Problem**: Robot doesn't move to objects

**Solutions**:
1. Ensure objects are detected first (check semantic map)
2. Verify Nav2 is running (if using full navigation)
3. Check if robot pose is being published
4. Ensure map is available for navigation

---

## Performance Tips

1. **Camera Frame Rate**: Higher frame rate = more detections
2. **Confidence Threshold**: Adjust in code (default: 0.5)
3. **Object Merging**: Objects within 1m are merged
4. **YOLO Model**: Use `yolov8n.pt` for speed, `yolov8x.pt` for accuracy

---

## Next Steps

- **Task 1.2**: Improve depth estimation with LiDAR fusion
- **Task 1.3**: Add object persistence and timeout mechanism
- **Task 1.4**: Complete Nav2 integration for autonomous navigation

---

## Additional Resources

- **Full Documentation**: `docs/TASK_1_1_VERIFICATION.md`
- **Validation Test**: `test_task_1_1_validation.py`
- **Source Code**: `src/robot_semantic_slam/robot_semantic_slam/`
- **Launch Files**: `src/robot_semantic_slam/launch/`
