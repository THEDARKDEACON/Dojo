# Perception Configuration Files

This directory contains configuration files for the robot perception system. Each file serves a specific purpose and has a distinct structure.

## Configuration Files

### `perception_params.yaml`
**Purpose**: Flat configuration structure for perception system utilities and scripts
**Used by**: 
- `perception_system.launch.py`
- `robot_perception/utils/config.py`
- Utility scripts and tools

**Structure**: Flat YAML with sections:
- `camera`: Camera processing parameters
- `lidar`: LiDAR processing parameters  
- `detection`: Object detection parameters
- `fusion`: Sensor fusion parameters
- `visualization`: Visualization settings
- `debug`: Debug and logging settings

**When to use**: When you need a simple, flat configuration structure for scripts or when using the ConfigManager utility class.

### `robot_perception_params.yaml`
**Purpose**: ROS2-compatible parameter structure for perception nodes
**Used by**:
- `perception.launch.py`
- Individual perception nodes
- ROS2 parameter system

**Structure**: ROS2 parameter format with `ros__parameters` sections:
- `camera_processor/ros__parameters`: Camera node parameters
- `lidar_processor/ros__parameters`: LiDAR node parameters
- `object_detector/ros__parameters`: Detection node parameters
- `visualization/ros__parameters`: Visualization parameters

**When to use**: When launching individual perception nodes or when you need ROS2-compatible parameter loading.

## Key Differences

| Aspect | perception_params.yaml | robot_perception_params.yaml |
|--------|------------------------|-------------------------------|
| Structure | Flat YAML sections | ROS2 parameter hierarchy |
| Usage | Utility scripts, tools | ROS2 nodes, launch files |
| Parameter Access | ConfigManager class | ROS2 parameter system |
| Flexibility | Easy to read/modify | ROS2 standard compliance |

## Usage Examples

### Using perception_params.yaml
```python
from robot_perception.utils.config import load_config
config = load_config()  # Loads perception_params.yaml by default
camera_topic = config.get('camera.image_topic')
```

### Using robot_perception_params.yaml
```python
# In a ROS2 node
self.declare_parameters_from_file('robot_perception_params.yaml')
camera_topic = self.get_parameter('camera_processor.camera_topic').value
```

## Maintenance Guidelines

1. **Keep both files synchronized** for common parameters
2. **Update both files** when adding new perception features
3. **Use descriptive comments** to explain parameter purposes
4. **Follow naming conventions**:
   - `perception_params.yaml`: flat structure with dots (e.g., `camera.image_topic`)
   - `robot_perception_params.yaml`: hierarchical structure (e.g., `camera_processor/ros__parameters/camera_topic`)

## Migration Notes

If you need to convert between formats:
- **Flat to ROS2**: Wrap sections in `node_name/ros__parameters`
- **ROS2 to Flat**: Extract parameters from `ros__parameters` sections