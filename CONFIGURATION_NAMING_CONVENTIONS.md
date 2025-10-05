# Configuration File Naming Conventions

This document establishes consistent naming conventions for configuration files across the Dojo robot project.

## Naming Convention Rules

### 1. File Extension
- All configuration files MUST use `.yaml` extension (not `.yml`)

### 2. Naming Pattern
Configuration files SHOULD follow this pattern:
```
<functionality>_<type>.yaml
```

Where:
- `<functionality>`: Describes what the configuration is for (e.g., `perception`, `control`, `navigation`)
- `<type>`: Describes the configuration type (see types below)

### 3. Configuration Types

#### `params.yaml` - ROS2 Parameter Files
For files containing ROS2 node parameters with `ros__parameters` structure.
- **Examples**: `perception_params.yaml`, `control_params.yaml`, `navigation_params.yaml`
- **Usage**: ROS2 launch files, parameter loading
- **Structure**: ROS2 parameter hierarchy with `node_name/ros__parameters`

#### `config.yaml` - System Configuration Files  
For files containing system-level configuration (not ROS2 parameters).
- **Examples**: `slam_config.yaml`, `ekf_config.yaml`, `hardware_config.yaml`
- **Usage**: System configuration, algorithm parameters
- **Structure**: Flat or nested YAML without ROS2 parameter structure

#### `controllers.yaml` - Controller Configuration Files
For files specifically configuring ROS2 controllers.
- **Examples**: `ros2_controllers.yaml`, `gazebo_controllers.yaml`
- **Usage**: ROS2 control system, controller manager
- **Structure**: Controller manager and controller-specific parameters

### 4. Package-Specific Naming

#### Primary Configuration Files
Each package SHOULD have one primary configuration file named:
```
<package_functionality>_params.yaml
```
- `robot_control` → `control_params.yaml`
- `robot_perception` → `perception_params.yaml`  
- `robot_navigation` → `navigation_params.yaml`
- `robot_hardware` → `hardware_params.yaml`

#### Secondary Configuration Files
Additional configuration files SHOULD be named by functionality:
```
<specific_functionality>_<type>.yaml
```
- `arduino_config.yaml` (hardware interface configuration)
- `slam_config.yaml` (SLAM algorithm configuration)
- `ekf_config.yaml` (Extended Kalman Filter configuration)

### 5. Deprecated Patterns

The following naming patterns are DEPRECATED and should be migrated:

❌ **Avoid these patterns:**
- `robot_<package>_params.yaml` (too verbose)
- `<functionality>.yaml` (missing type suffix)
- Mixed case or special characters
- Abbreviations without clear meaning

✅ **Use these patterns instead:**
- `<functionality>_params.yaml`
- `<functionality>_config.yaml`
- `<functionality>_controllers.yaml`

## Current File Mapping

### Files Following Convention ✅
- `perception_params.yaml` - Good
- `slam_config.yaml` - Good  
- `ekf_config.yaml` - Good
- `ros2_control.yaml` - Should be `ros2_controllers.yaml`

### Files Needing Rename 🔄
- `robot_control_params.yaml` → `control_params.yaml`
- `robot_perception_params.yaml` → `perception_params.yaml` (keep existing)
- `hardware.yaml` → `hardware_config.yaml`
- `arduino.yaml` → `arduino_config.yaml`
- `controllers.yaml` → `control_controllers.yaml`
- `twist_mux.yaml` → `twist_mux_config.yaml`
- `robot_controllers.yaml` → `control_controllers_template.yaml`

### Navigation Files (Already Good) ✅
- `bt_navigator_params.yaml`
- `controller_params.yaml`
- `costmap_common_params.yaml`
- `global_costmap_params.yaml`
- `local_costmap_params.yaml`
- `localization_params.yaml`
- `map_server_params.yaml`
- `nav2_params.yaml`
- `planner_params.yaml`

## Implementation Guidelines

### 1. Renaming Process
1. Rename the configuration file
2. Update all references in launch files
3. Update documentation
4. Test that all functionality still works

### 2. File Headers
All configuration files SHOULD include a header comment:
```yaml
# <Functionality> Configuration
# Purpose: <Brief description of what this configures>
# Used by: <List of launch files or nodes that use this>
# Package: <package_name>
```

### 3. Documentation
Each config directory SHOULD include a `README.md` explaining:
- Purpose of each configuration file
- When to use each file
- Key parameters and their meanings
- Usage examples

## Migration Plan

### Phase 1: High-Impact Files
1. `robot_control_params.yaml` → `control_params.yaml`
2. `hardware.yaml` → `hardware_config.yaml`
3. `arduino.yaml` → `arduino_config.yaml`

### Phase 2: Medium-Impact Files  
1. `controllers.yaml` → `control_controllers.yaml`
2. `twist_mux.yaml` → `twist_mux_config.yaml`
3. `ros2_control.yaml` → `ros2_controllers.yaml`

### Phase 3: Low-Impact Files
1. `robot_controllers.yaml` → `control_controllers_template.yaml`
2. Update any remaining inconsistent files

## Validation

After implementing naming conventions:
1. All configuration files follow the established pattern
2. All launch files reference correct file names
3. All documentation is updated
4. System builds and runs without errors
5. No broken references remain