# Contributing to Dojo Robot

Thank you for your interest in contributing to the Dojo Robot project! This document provides guidelines and conventions to ensure consistency across the codebase.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Naming Conventions](#naming-conventions)
4. [Code Style](#code-style)
5. [Testing Guidelines](#testing-guidelines)
6. [Documentation Standards](#documentation-standards)
7. [Pull Request Process](#pull-request-process)
8. [Project Structure](#project-structure)

---

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow the technical guidelines below

---

## Getting Started

### Prerequisites
- ROS2 Humble or later
- Python 3.10+
- Gazebo 11+
- Ubuntu 22.04 or later

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd dojo-robot

# Install dependencies
./scripts/install_dependencies.sh

# Build the workspace
./scripts/build_workspace.sh

# Source the workspace
source install/setup.bash
```

---

## Naming Conventions

### 1. Package Names

**Convention**: `robot_<functionality>`  
**Format**: lowercase with underscores (snake_case)

**Examples**:
- ✅ `robot_control`
- ✅ `robot_navigation`
- ✅ `robot_semantic_slam`
- ❌ `RobotControl` (avoid CamelCase)
- ❌ `robot-control` (avoid hyphens)

**Rationale**: Follows ROS2 package naming conventions and Python module standards.

---

### 2. Launch Files

**Convention**: `<primary_function>.launch.py`  
**Format**: lowercase with underscores, always ends with `.launch.py`

**Examples**:
- ✅ `gazebo.launch.py` - Launches Gazebo simulator
- ✅ `complete_simulation.launch.py` - Full simulation system
- ✅ `semantic_slam.launch.py` - Semantic SLAM system
- ✅ `cutting_edge_features.launch.py` - All advanced features
- ❌ `launch_gazebo.py` (avoid "launch_" prefix)
- ❌ `GazeboLaunch.py` (avoid CamelCase)

**Special Cases**:
- Primary entry points should have descriptive names: `complete_simulation.launch.py`, `bringup.launch.py`
- Feature-specific launches: `<feature_name>.launch.py`
- Specialized modes: `<mode>_mode.launch.py` (e.g., `bypass_mode.launch.py`)

**Rationale**: Clear, descriptive names that indicate purpose without redundant prefixes.

---

### 3. Python Modules (Nodes)

**Convention**: `<descriptive_name>.py`  
**Format**: lowercase with underscores (snake_case)

**Examples**:
- ✅ `semantic_slam_node.py` - Main semantic SLAM node
- ✅ `performance_dashboard.py` - Performance monitoring
- ✅ `advanced_safety_system.py` - Safety system
- ✅ `pointcloud_processor.py` - Point cloud processing
- ❌ `SemanticSLAM.py` (avoid CamelCase for files)
- ❌ `node_semantic_slam.py` (avoid "node_" prefix)

**Node Names** (in code):
- Use descriptive names that match functionality
- Format: lowercase with underscores
- Example: `self.get_logger().info('semantic_slam_node starting')`

**Rationale**: Python PEP 8 compliance, clear purpose indication.

---

### 4. Python Classes

**Convention**: `PascalCase` (CapWords)  
**Format**: Each word capitalized, no underscores

**Examples**:
- ✅ `SemanticSLAMNode`
- ✅ `PerformanceDashboard`
- ✅ `AdvancedSafetySystem`
- ✅ `PointCloudProcessor`
- ❌ `semantic_slam_node` (use PascalCase for classes)
- ❌ `Semantic_SLAM_Node` (no underscores)

**Rationale**: Python PEP 8 standard for class names.

---

### 5. Python Functions and Methods

**Convention**: `snake_case`  
**Format**: lowercase with underscores

**Examples**:
- ✅ `process_point_cloud()`
- ✅ `calculate_detection_rate()`
- ✅ `publish_performance_metrics()`
- ✅ `handle_emergency_stop()`
- ❌ `ProcessPointCloud()` (avoid PascalCase)
- ❌ `calculateDetectionRate()` (avoid camelCase)

**Rationale**: Python PEP 8 standard for function names.

---

### 6. Python Variables

**Convention**: `snake_case`  
**Format**: lowercase with underscores

**Examples**:
- ✅ `detection_rate`
- ✅ `cpu_usage`
- ✅ `safety_level`
- ✅ `point_cloud_data`
- ❌ `detectionRate` (avoid camelCase)
- ❌ `CPUUsage` (avoid PascalCase)

**Constants**:
- Format: `UPPER_CASE_WITH_UNDERSCORES`
- Examples: `MAX_SPEED`, `DEFAULT_TIMEOUT`, `SAFETY_THRESHOLD`

**Rationale**: Python PEP 8 standards.

---

### 7. ROS2 Topics

**Convention**: `/<namespace>/<descriptive_name>`  
**Format**: lowercase with underscores, starts with `/`

**Examples**:
- ✅ `/semantic_map` - Semantic map data
- ✅ `/performance_metrics` - Performance data
- ✅ `/safety_status` - Safety system status
- ✅ `/cmd_vel` - Velocity commands (standard ROS name)
- ❌ `/SemanticMap` (avoid CamelCase)
- ❌ `/semantic-map` (avoid hyphens)

**Standard ROS Topics** (keep as-is):
- `/cmd_vel` - Velocity commands
- `/scan` - LaserScan data
- `/odom` - Odometry
- `/map` - Occupancy grid map
- `/tf` - Transform tree

**Rationale**: ROS2 naming conventions, consistency with standard topics.

---

### 8. ROS2 Services

**Convention**: `/<namespace>/<action>_<object>`  
**Format**: lowercase with underscores, verb + noun

**Examples**:
- ✅ `/find_object` - Find object service
- ✅ `/list_objects` - List objects service
- ✅ `/set_mode` - Set mode service
- ✅ `/calibrate_sensors` - Calibrate sensors
- ❌ `/FindObject` (avoid CamelCase)
- ❌ `/object_find` (verb should come first)

**Rationale**: Clear action indication, ROS2 conventions.

---

### 9. Configuration Files

**Convention**: `<component>_<type>.yaml`  
**Format**: lowercase with underscores, ends with `.yaml`

**Examples**:
- ✅ `nav2_params.yaml` - Nav2 parameters
- ✅ `control_params.yaml` - Control parameters
- ✅ `arduino_config.yaml` - Arduino configuration
- ✅ `twist_mux_config.yaml` - Twist mux configuration
- ❌ `Nav2Params.yaml` (avoid CamelCase)
- ❌ `params_nav2.yaml` (type should come after component)

**Rationale**: Clear component and type indication.

---

### 10. Test Files

**Convention**: `test_<feature>.py`  
**Format**: lowercase with underscores, starts with `test_`

**Location**: `<package>/test/` directory

**Examples**:
- ✅ `test_semantic_navigation.py`
- ✅ `test_behavior_tree_safety.py`
- ✅ `test_object_persistence.py`
- ✅ `test_lidar_camera_fusion.py`
- ❌ `semantic_navigation_test.py` (prefix with "test_")
- ❌ `TestSemanticNavigation.py` (avoid CamelCase for files)

**Test Class Names**:
- Format: `Test<FeatureName>`
- Examples: `TestSemanticNavigation`, `TestBehaviorTreeSafety`

**Test Method Names**:
- Format: `test_<specific_behavior>`
- Examples: `test_object_detection()`, `test_emergency_stop()`

**Rationale**: pytest discovery conventions, clear test identification.

---

### 11. Documentation Files

**Convention**: `<TOPIC>_<TYPE>.md` or `<TOPIC>.md`  
**Format**: UPPERCASE for main words, underscores between words

**Examples**:
- ✅ `README.md` - Main project documentation
- ✅ `CONTRIBUTING.md` - Contribution guidelines
- ✅ `IMPLEMENTATION_GUIDE.md` - Implementation guide
- ✅ `TROUBLESHOOTING.md` - Troubleshooting guide
- ✅ `BEHAVIOR_TREE_SAFETY.md` - Feature-specific docs
- ❌ `readme.md` (use uppercase for README)
- ❌ `implementation-guide.md` (use underscores)

**Task Documentation**:
- Format: `TASK_<number>_<type>.md`
- Examples: `TASK_6.2_CLEANUP_REPORT.md`, `TASK_6.3_CONSOLIDATION_REPORT.md`

**Rationale**: Standard documentation naming, easy to identify important files.

---

### 12. World Files

**Convention**: `<environment_name>.world`  
**Format**: lowercase with underscores

**Examples**:
- ✅ `house.world`
- ✅ `office_small.world`
- ✅ `warehouse.world`
- ✅ `mapping_world.world`
- ❌ `House.world` (avoid CamelCase)
- ❌ `office-small.world` (avoid hyphens)

**Rationale**: Gazebo conventions, clear environment indication.

---

### 13. RViz Configuration Files

**Convention**: `<purpose>.rviz`  
**Format**: lowercase with underscores

**Examples**:
- ✅ `simulation.rviz`
- ✅ `navigation_with_map.rviz`
- ✅ `pointcloud_3d_visualization.rviz`
- ❌ `Simulation.rviz` (avoid CamelCase)

**Rationale**: Clear purpose indication, RViz conventions.

---

## Code Style

### Python

Follow **PEP 8** style guide:

```python
# Good example
class SemanticSLAMNode(Node):
    """Semantic SLAM node with YOLO integration."""
    
    def __init__(self):
        super().__init__('semantic_slam_node')
        self.detection_rate = 0.0
        self.object_database = {}
        
    def process_detections(self, detections):
        """Process YOLO detections and update semantic map."""
        for detection in detections:
            self._update_object_database(detection)
            
    def _update_object_database(self, detection):
        """Private method to update object database."""
        # Implementation here
        pass
```

**Key Points**:
- 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters (flexible for readability)
- Docstrings for all public methods
- Type hints where appropriate
- Private methods prefixed with `_`

### Launch Files

```python
# Good example
def generate_launch_description():
    """Generate launch description for semantic SLAM."""
    
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    enable_safety = LaunchConfiguration('enable_safety', default='true')
    
    # Nodes
    semantic_slam_node = Node(
        package='robot_semantic_slam',
        executable='semantic_slam_node.py',
        name='semantic_slam_node',
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen'
    )
    
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('enable_safety', default_value='true'),
        semantic_slam_node
    ])
```

**Key Points**:
- Clear docstring at top
- Group related items (arguments, nodes, etc.)
- Use descriptive variable names
- Include comments for complex logic

---

## Testing Guidelines

### Test Organization

```
<package>/
├── <package>/
│   └── <modules>.py
└── test/
    ├── test_<feature1>.py
    ├── test_<feature2>.py
    └── test_<feature3>.py
```

### Test Structure

```python
import pytest
from robot_semantic_slam.semantic_slam_node import SemanticSLAMNode

class TestSemanticSLAM:
    """Test suite for Semantic SLAM functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.node = SemanticSLAMNode()
        
    def test_object_detection(self):
        """Test object detection and database update."""
        # Arrange
        detection = {'class': 'chair', 'confidence': 0.95}
        
        # Act
        self.node.process_detections([detection])
        
        # Assert
        assert len(self.node.object_database) == 1
        
    def test_detection_rate_calculation(self):
        """Test detection rate calculation."""
        # Test implementation
        pass
```

**Key Points**:
- Use pytest framework
- Arrange-Act-Assert pattern
- Clear test method names
- Docstrings for test classes and methods
- Setup and teardown methods as needed

---

## Documentation Standards

### Code Documentation

```python
def calculate_detection_rate(detections, time_window):
    """
    Calculate object detection rate over time window.
    
    Args:
        detections (list): List of detection objects
        time_window (float): Time window in seconds
        
    Returns:
        float: Detection rate in detections per second
        
    Raises:
        ValueError: If time_window is zero or negative
        
    Example:
        >>> detections = [obj1, obj2, obj3]
        >>> rate = calculate_detection_rate(detections, 1.0)
        >>> print(f"Detection rate: {rate} objects/sec")
    """
    if time_window <= 0:
        raise ValueError("Time window must be positive")
        
    return len(detections) / time_window
```

### README Structure

Each package should have a README.md with:
1. **Overview**: What the package does
2. **Dependencies**: Required packages and libraries
3. **Usage**: How to use the package
4. **Launch Files**: Available launch files and their purposes
5. **Nodes**: ROS2 nodes provided by the package
6. **Topics**: Published and subscribed topics
7. **Parameters**: Configurable parameters
8. **Examples**: Usage examples

---

## Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Follow Naming Conventions**
   - Ensure all new files follow conventions above
   - Update existing files if modifying them

3. **Write Tests**
   - Add tests for new functionality
   - Ensure existing tests pass

4. **Update Documentation**
   - Update relevant README files
   - Add docstrings to new code
   - Update IMPLEMENTATION_PROGRESS.md if completing a task

5. **Run Validation**
   ```bash
   # Build and test
   ./scripts/build_workspace.sh
   colcon test
   
   # Check code style
   flake8 src/
   ```

6. **Create Pull Request**
   - Clear title describing the change
   - Description of what was changed and why
   - Reference any related issues
   - Include test results

7. **Code Review**
   - Address reviewer feedback
   - Make requested changes
   - Ensure CI passes

---

## Project Structure

### Standard Package Layout

```
<package_name>/
├── <package_name>/          # Python modules
│   ├── __init__.py
│   ├── <node1>.py
│   ├── <node2>.py
│   └── utils/               # Utility modules
│       ├── __init__.py
│       └── <utility>.py
├── launch/                  # Launch files
│   ├── <feature1>.launch.py
│   └── <feature2>.launch.py
├── config/                  # Configuration files
│   ├── <component>_params.yaml
│   └── <component>_config.yaml
├── test/                    # Test files
│   ├── test_<feature1>.py
│   └── test_<feature2>.py
├── rviz/                    # RViz configurations (if applicable)
│   └── <config>.rviz
├── worlds/                  # Gazebo worlds (if applicable)
│   └── <world>.world
├── urdf/                    # URDF files (if applicable)
│   └── <robot>.urdf.xacro
├── README.md                # Package documentation
├── package.xml              # ROS2 package manifest
├── setup.py                 # Python package setup
└── CMakeLists.txt           # CMake build configuration (if needed)
```

---

## Quick Reference

### File Naming Cheat Sheet

| Type | Convention | Example |
|------|-----------|---------|
| Package | `robot_<name>` | `robot_control` |
| Launch File | `<function>.launch.py` | `gazebo.launch.py` |
| Python Module | `<name>.py` | `semantic_slam_node.py` |
| Python Class | `PascalCase` | `SemanticSLAMNode` |
| Function/Method | `snake_case` | `process_detections()` |
| Variable | `snake_case` | `detection_rate` |
| Constant | `UPPER_SNAKE_CASE` | `MAX_SPEED` |
| ROS Topic | `/snake_case` | `/semantic_map` |
| ROS Service | `/verb_noun` | `/find_object` |
| Config File | `<component>_<type>.yaml` | `nav2_params.yaml` |
| Test File | `test_<feature>.py` | `test_semantic_slam.py` |
| Documentation | `TOPIC.md` | `IMPLEMENTATION_GUIDE.md` |
| World File | `<name>.world` | `house.world` |

---

## Questions?

If you have questions about contributing or naming conventions:
1. Check existing code for examples
2. Review this document
3. Ask in project discussions
4. Open an issue for clarification

---

**Thank you for contributing to Dojo Robot!**

*Last Updated: November 11, 2025*
