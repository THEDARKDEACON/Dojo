# Robot Navigation Configuration Files

This directory contains configuration files for the robot navigation system using Nav2.

## Configuration Files

### Core Navigation Files

#### `nav2_params.yaml`
**Purpose**: Main Nav2 navigation stack parameters
**Used by**: Primary navigation launch files
**Contains**: Complete navigation stack configuration

#### `bt_navigator_params.yaml`
**Purpose**: Behavior Tree navigator configuration
**Used by**: BT navigator node
**Contains**: Behavior tree definitions and parameters

#### `controller_params.yaml`
**Purpose**: Path following controller configuration
**Used by**: Controller server
**Contains**: DWB controller parameters and constraints

#### `planner_params.yaml`
**Purpose**: Path planning algorithm configuration
**Used by**: Planner server
**Contains**: NavFn planner parameters and settings

### Costmap Configuration Files

#### `costmap_common_params.yaml`
**Purpose**: Shared costmap parameters for global and local costmaps
**Used by**: Both global and local costmap configurations
**Contains**: Common costmap layers and parameters

#### `global_costmap_params.yaml`
**Purpose**: Global costmap specific configuration
**Used by**: Global costmap server
**Contains**: Global planning costmap settings

#### `local_costmap_params.yaml`
**Purpose**: Local costmap specific configuration
**Used by**: Local costmap server
**Contains**: Local planning costmap settings

### Localization and Mapping Files

#### `localization_params.yaml`
**Purpose**: Robot localization configuration
**Used by**: AMCL localization node
**Contains**: Particle filter and localization parameters

#### `map_server_params.yaml`
**Purpose**: Map server configuration
**Used by**: Map server node
**Contains**: Map loading and serving parameters

## Navigation Stack Architecture

```
Nav2 Stack Components:
├── BT Navigator (bt_navigator_params.yaml)
├── Controller Server (controller_params.yaml)
├── Planner Server (planner_params.yaml)
├── Global Costmap (global_costmap_params.yaml + costmap_common_params.yaml)
├── Local Costmap (local_costmap_params.yaml + costmap_common_params.yaml)
├── Localization (localization_params.yaml)
└── Map Server (map_server_params.yaml)
```

## Usage Examples

### Complete Navigation Launch
```python
# Loading all navigation parameters
nav_params = PathJoinSubstitution([
    FindPackageShare('robot_navigation'),
    'config',
    'nav2_params.yaml'
])
```

### Individual Component Launch
```python
# Loading specific component parameters
controller_params = PathJoinSubstitution([
    FindPackageShare('robot_navigation'),
    'config',
    'controller_params.yaml'
])
```

## Key Configuration Areas

### Path Planning
- **Global Planning**: Long-range path planning using NavFn
- **Local Planning**: Real-time obstacle avoidance using DWB
- **Behavior Trees**: High-level navigation logic and recovery behaviors

### Costmaps
- **Static Layer**: Map-based obstacles
- **Obstacle Layer**: Sensor-based dynamic obstacles
- **Inflation Layer**: Safety margins around obstacles

### Localization
- **AMCL**: Adaptive Monte Carlo Localization
- **Particle Filter**: Position estimation parameters
- **Sensor Models**: Laser scan matching configuration

## Tuning Guidelines

### Performance Tuning
1. **Costmap Resolution**: Balance accuracy vs. computational cost
2. **Update Rates**: Adjust for real-time performance
3. **Planning Frequency**: Match robot dynamics

### Safety Tuning
1. **Inflation Radius**: Ensure safe clearance from obstacles
2. **Velocity Limits**: Match robot physical constraints
3. **Recovery Behaviors**: Configure appropriate fallback actions

### Accuracy Tuning
1. **Localization**: Tune particle filter parameters
2. **Path Following**: Adjust controller gains
3. **Obstacle Detection**: Configure sensor parameters

## Maintenance Guidelines

1. **Parameter Validation**: Test parameter changes in simulation first
2. **Performance Monitoring**: Monitor navigation performance metrics
3. **Safety Verification**: Always verify safety parameters
4. **Documentation**: Document custom parameter changes
5. **Backup Configurations**: Keep working parameter sets backed up