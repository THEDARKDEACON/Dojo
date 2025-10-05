# File Organization Guide

This guide provides comprehensive guidelines for organizing files within the Dojo robot codebase, establishing clear conventions for file placement, naming, and purpose documentation.

## Table of Contents
- [Package Structure Overview](#package-structure-overview)
- [File Type Guidelines](#file-type-guidelines)
- [Naming Conventions](#naming-conventions)
- [File Placement Rules](#file-placement-rules)
- [Documentation Requirements](#documentation-requirements)

## Package Structure Overview

The Dojo robot codebase follows standard ROS2 package conventions with additional organization rules to maintain clarity and prevent redundancy.

### Standard ROS2 Package Structure
```
src/package_name/
├── package.xml                 # Package metadata
├── setup.py                   # Python package setup
├── setup.cfg                  # Python package configuration
├── CMakeLists.txt             # Build configuration (C++ packages)
├── README.md                  # Package documentation
├── package_name/              # Python source code
│   ├── __init__.py
│   └── [module_files].py
├── launch/                    # Launch files
│   └── *.launch.py
├── config/                    # Configuration files
│   ├── README.md
│   └── *.yaml
├── rviz/                      # RViz configurations
│   └── *.rviz
├── urdf/                      # Robot descriptions (robot_description only)
│   └── *.urdf.xacro
├── worlds/                    # Gazebo worlds (robot_gazebo only)
│   └── *.world
└── resource/                  # Package resources
    └── package_name
```

## File Type Guidelines

### Launch Files (`*.launch.py`)

**Purpose**: Define how to start nodes and configure the robot system

**Organization Rules**:
- Maximum 3-4 launch files per package
- Each launch file must have a distinct, documented purpose
- Use descriptive names that clearly indicate functionality

**Naming Convention**:
- `{functionality}.launch.py` (e.g., `simulation.launch.py`, `hardware.launch.py`)
- Avoid generic names like `main.launch.py` or `test.launch.py`

**Content Guidelines**:
- Include comprehensive docstring explaining purpose and parameters
- Use clear parameter names with default values
- Group related functionality together

**Example Structure**:
```python
"""
Launch file for robot simulation in Gazebo.

This launch file starts:
- Gazebo simulator with specified world
- Robot spawning and description
- Basic control interfaces

Parameters:
    world_name (str): Name of the Gazebo world file (default: 'empty.world')
    robot_name (str): Name of the robot instance (default: 'dojo_robot')
    use_sim_time (bool): Use simulation time (default: True)
"""
```

### Configuration Files (`*.yaml`)

**Purpose**: Store parameters and settings for nodes and systems

**Organization Rules**:
- Group related parameters in single files
- Avoid duplicate parameter definitions across files
- Use hierarchical parameter organization

**Naming Convention**:
- `{system}_params.yaml` for system-specific parameters
- `{node}_config.yaml` for node-specific configuration
- Avoid generic names like `config.yaml` or `params.yaml`

**Content Guidelines**:
- Use clear, descriptive parameter names
- Include comments explaining parameter purposes
- Group related parameters under namespaces
- Provide reasonable default values

**Example Structure**:
```yaml
# Navigation system parameters for Dojo robot
# Updated: 2025-01-XX

nav2_params:
  # Global costmap configuration
  global_costmap:
    global_frame: map
    robot_base_frame: base_link
    resolution: 0.05
    
  # Local costmap configuration  
  local_costmap:
    global_frame: odom
    robot_base_frame: base_link
    resolution: 0.025
```

### RViz Configuration Files (`*.rviz`)

**Purpose**: Define visualization layouts for different use cases

**Organization Rules**:
- Maximum 3 RViz configurations per package
- Each configuration must serve a distinct visualization purpose
- Avoid duplicate display configurations

**Naming Convention**:
- `{purpose}.rviz` (e.g., `simulation.rviz`, `perception.rviz`, `robot_display.rviz`)
- Use descriptive names indicating the visualization scenario

**Content Guidelines**:
- Configure appropriate displays for the intended use case
- Set reasonable default view angles and positions
- Include necessary transforms and coordinate frames

### URDF/Xacro Files (`*.urdf.xacro`, `*.urdf`)

**Purpose**: Define robot physical and visual properties

**Organization Rules** (robot_description package only):
- One primary robot description file (`robot.urdf.xacro`)
- One compiled URDF file (`robot.urdf`) - auto-generated
- Separate files for major components (sensors, actuators)
- Common properties in shared files

**Naming Convention**:
- `robot.urdf.xacro` - Primary robot description
- `{component}.urdf.xacro` - Component-specific descriptions
- `common_properties.xacro` - Shared properties and materials

**File Hierarchy**:
```
urdf/
├── robot.urdf.xacro           # Main robot description
├── robot.urdf                 # Compiled version (auto-generated)
├── common_properties.xacro    # Shared materials and properties
└── sensors/
    ├── rplidar.urdf.xacro     # LiDAR sensor description
    └── camera.urdf.xacro      # Camera sensor description
```

### Python Source Files (`*.py`)

**Purpose**: Implement robot functionality and ROS2 nodes

**Organization Rules**:
- Group related functionality in modules
- Use clear module and class names
- Follow Python PEP 8 style guidelines

**Naming Convention**:
- `{functionality}_{type}.py` (e.g., `camera_driver.py`, `safety_supervisor.py`)
- Use snake_case for file names
- Avoid abbreviations unless widely understood

**Content Guidelines**:
- Include comprehensive docstrings for classes and functions
- Use type hints for function parameters and return values
- Follow ROS2 Python coding standards

### World Files (`*.world`) - robot_gazebo package only

**Purpose**: Define Gazebo simulation environments

**Organization Rules**:
- Organize by environment type or complexity
- Include descriptive world files for different scenarios
- Avoid duplicate or near-identical worlds

**Naming Convention**:
- `{environment_type}.world` (e.g., `office.world`, `outdoor.world`)
- Use descriptive names indicating the environment

## Naming Conventions

### General Principles
1. **Descriptive**: Names should clearly indicate purpose and content
2. **Consistent**: Follow established patterns within the codebase
3. **Concise**: Avoid unnecessarily long names while maintaining clarity
4. **Standard**: Use ROS2 and Python naming conventions

### File Naming Patterns

| File Type | Pattern | Example |
|-----------|---------|---------|
| Launch files | `{functionality}.launch.py` | `simulation.launch.py` |
| Config files | `{system}_params.yaml` | `navigation_params.yaml` |
| RViz configs | `{purpose}.rviz` | `perception.rviz` |
| Python modules | `{functionality}_{type}.py` | `hardware_manager.py` |
| URDF files | `{component}.urdf.xacro` | `robot.urdf.xacro` |
| World files | `{environment}.world` | `warehouse.world` |

### Parameter Naming
- Use snake_case for parameter names
- Group related parameters under namespaces
- Use descriptive names that indicate units and purpose
- Example: `max_linear_velocity_mps` instead of `max_vel`

### Node and Topic Naming
- Use descriptive names that indicate functionality
- Follow ROS2 naming conventions with forward slashes
- Example: `/robot/sensors/lidar/scan` instead of `/scan`

## File Placement Rules

### Package-Specific Guidelines

#### robot_control
- **Purpose**: Core robot control and safety systems
- **Key files**: Hardware interfaces, safety systems, control managers
- **Config focus**: Control parameters, safety thresholds, hardware settings

#### robot_description  
- **Purpose**: Robot physical and visual description
- **Key files**: URDF/Xacro files, robot visualization configs
- **Unique directories**: `urdf/` for robot descriptions

#### robot_gazebo
- **Purpose**: Gazebo simulation integration
- **Key files**: Simulation launch files, Gazebo-specific configs
- **Unique directories**: `worlds/` for Gazebo world files

#### robot_perception
- **Purpose**: Sensor processing and perception algorithms
- **Key files**: Perception nodes, sensor processing, object detection
- **Config focus**: Sensor parameters, perception algorithms

#### robot_navigation
- **Purpose**: Navigation and path planning
- **Key files**: Navigation launch files, Nav2 configurations
- **Config focus**: Navigation parameters, costmap settings

#### robot_hardware
- **Purpose**: Hardware drivers and interfaces
- **Key files**: Hardware drivers, device interfaces
- **Config focus**: Hardware-specific parameters

### Cross-Package File Guidelines

#### Launch Files
- **System-level launches**: Place in `robot_bringup` or `robot_launch`
- **Package-specific launches**: Place in respective package `launch/` directory
- **Avoid**: Duplicate launch files across packages

#### Configuration Files
- **Shared configs**: Place in top-level `config/` directory
- **Package-specific configs**: Place in package `config/` directory
- **Node-specific configs**: Place with the package containing the node

#### Documentation Files
- **Package docs**: `README.md` in each package root
- **System docs**: Top-level directory with descriptive names
- **Config docs**: `README.md` in each `config/` directory

## Documentation Requirements

### Mandatory Documentation

#### Package README Files
Every package must have a `README.md` file containing:
- Package purpose and functionality
- Key nodes and their responsibilities  
- Launch file descriptions and usage
- Configuration file explanations
- Dependencies and requirements

#### Configuration README Files
Every `config/` directory must have a `README.md` file containing:
- Description of each configuration file
- Parameter explanations and valid ranges
- Usage examples and scenarios
- Relationships between configuration files

#### Launch File Documentation
Every launch file must include:
- Comprehensive docstring explaining purpose
- Parameter descriptions with types and defaults
- Usage examples
- Dependencies and requirements

### Documentation Standards

#### Format Requirements
- Use Markdown format for all documentation
- Include table of contents for longer documents
- Use code blocks for examples and commands
- Include clear section headers and organization

#### Content Requirements
- Explain the "why" not just the "what"
- Provide practical examples and use cases
- Include troubleshooting information where relevant
- Keep documentation up-to-date with code changes

#### Example Package README Structure
```markdown
# Package Name

Brief description of package purpose and functionality.

## Overview
Detailed explanation of what this package does and why it exists.

## Nodes
- `node_name`: Description of node functionality
- `another_node`: Description of another node

## Launch Files
- `main.launch.py`: Primary launch file for normal operation
- `debug.launch.py`: Launch file for debugging and development

## Configuration Files
- `params.yaml`: Main parameter configuration
- `debug_params.yaml`: Debug-specific parameters

## Usage Examples
```bash
# Example commands for using the package
ros2 launch package_name main.launch.py
```

## Dependencies
- List of required packages and dependencies
- Installation instructions if needed

## Troubleshooting
- Common issues and solutions
```

## Maintenance Guidelines

### Regular Reviews
- Monthly review of file organization
- Quarterly assessment of naming consistency
- Annual evaluation of package structure

### Adding New Files
1. Determine appropriate package and directory
2. Follow established naming conventions
3. Add appropriate documentation
4. Update relevant README files
5. Ensure no duplication with existing files

### Modifying Existing Files
1. Update documentation to reflect changes
2. Maintain backward compatibility where possible
3. Update related configuration files
4. Test changes thoroughly before committing

### Preventing Redundancy
1. Search for existing similar files before creating new ones
2. Consider merging functionality instead of creating duplicates
3. Use clear, descriptive names to avoid confusion
4. Regular cleanup of unused or obsolete files

This guide should be referenced when adding new files or reorganizing existing ones to maintain the clean, organized structure established during the codebase cleanup.