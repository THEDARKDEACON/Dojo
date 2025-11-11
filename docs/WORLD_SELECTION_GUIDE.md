# World Selection Guide - Dojo Robot Simulation Environments

## Overview

The Dojo Robot supports 54 different simulation worlds for testing various scenarios. This guide provides information on available worlds, how to select them, and their characteristics.

## Quick Start

### Basic World Selection

```bash
# Launch with specific world
ros2 launch robot_gazebo gazebo.launch.py world:=<world_name>

# Examples
ros2 launch robot_gazebo gazebo.launch.py world:=empty.world
ros2 launch robot_gazebo gazebo.launch.py world:=office_small.world
ros2 launch robot_gazebo gazebo.launch.py world:=warehouse.world
```

### With Full Robot System

```bash
# Launch complete system with specific world
python3 start_cutting_edge_robot.py --world <world_name>
```

## Available Worlds (54 Total)

### 🏠 Indoor Environments (15 worlds)

#### Residential
- **house.world** - Multi-room residential home with furniture
  - Use case: Indoor navigation, object detection
  - Complexity: Medium
  - Spawn position: (0, 0, 0.1)

#### Office Environments
- **office_small.world** - Compact office layout
  - Use case: Structured indoor navigation
  - Complexity: Low-Medium
  - Spawn position: (0, 0, 0.1)

- **office_cpr.world** - CPR office environment
  - Use case: Real-world office simulation
  - Complexity: Medium
  - Spawn position: (0, 0, 0.1)

- **office_cpr_construction.world** - Office under construction
  - Use case: Dynamic obstacle navigation
  - Complexity: Medium-High
  - Spawn position: (0, 0, 0.1)

- **office_earthquake.world** - Damaged office environment
  - Use case: Disaster response, irregular obstacles
  - Complexity: High
  - Spawn position: (0, 0, 0.1)

- **office_env_large.world** - Large office space
  - Use case: Long-range navigation, large-scale mapping
  - Complexity: Medium-High
  - Spawn position: (0, 0, 0.1)

#### Industrial
- **warehouse.world** - Large warehouse with shelves
  - Use case: Logistics, large space navigation
  - Complexity: Medium
  - Spawn position: (0, 0, 0.1)

- **powerplant.world** - Power plant interior
  - Use case: Industrial inspection
  - Complexity: High
  - Spawn position: (0, 0, 0.1)

- **inspection.world** - Inspection facility
  - Use case: Inspection tasks
  - Complexity: Medium
  - Spawn position: (0, 0, 0.1)

#### Challenge Arenas
- **fetchit_challenge_arena_montreal2019.world** - Competition arena
- **fetchit_challenge_assembly.world** - Assembly area
- **fetchit_challenge_simple.world** - Simple challenge environment
- **workshop_example.world** - Workshop environment
- **dojo_world.world** - Dojo training environment
- **demo_world.world** - Demo environment

### 🌳 Outdoor Environments (12 worlds)

- **outdoor.world** - General outdoor environment
  - Use case: Outdoor navigation testing
  - Complexity: Medium
  - Spawn position: (0, 0, 0.2)

- **agriculture.world** - Agricultural field
  - Use case: Agricultural robotics
  - Complexity: Low-Medium

- **canyonview_field.world** - Canyon view environment
  - Use case: Terrain navigation
  - Complexity: Medium

- **neighborhood.world** - Residential neighborhood
  - Use case: Urban navigation
  - Complexity: Medium-High

- **small_city.world** - Small city environment
  - Use case: Urban robotics
  - Complexity: High

- **test_city.world** - Test city
  - Use case: Urban testing
  - Complexity: High

- **city_osm_roundabout.world** - City with roundabout
  - Use case: Traffic navigation
  - Complexity: High

- **city_osm_roundabout_combined.world** - Combined roundabout
  - Use case: Complex traffic scenarios
  - Complexity: High

- **yosemite.world** - Yosemite park environment
  - Use case: Natural terrain
  - Complexity: Medium

- **rubble.world** - Rubble/debris field
  - Use case: Disaster response
  - Complexity: Medium-High

- **skidpan.world** - Skid testing area
  - Use case: Vehicle dynamics testing
  - Complexity: Low

- **waypoint.world** - Waypoint navigation
  - Use case: GPS navigation testing
  - Complexity: Low-Medium

### 🧪 Testing/Training Environments (18 worlds)

#### Basic Testing
- **empty.world** - Empty environment (ground plane only)
  - Use case: Baseline testing, algorithm development
  - Complexity: Minimal
  - Spawn position: (0, 0, 0.1)
  - **Status**: ✅ Stable

- **minimal.world** - Minimal setup with basic elements
  - Use case: Simple testing
  - Complexity: Minimal
  - Spawn position: (0, 0, 0.1)
  - **Status**: ✅ Stable

- **mapping_world.world** - Designed for mapping tests
  - Use case: SLAM and mapping development
  - Complexity: Low-Medium
  - Spawn position: (0, 0, 0.1)
  - **Status**: ✅ Recommended for navigation

- **simple_env_1.world** - Simple environment variant 1
- **simple_env_2.world** - Simple environment variant 2
- **simple_env_3.world** - Simple environment variant 3
- **test_zone.world** - General test zone

#### Cyberzoo Environments
- **cyberzoo.world** - Cyberzoo facility
- **cyberzoo_4_panels.world** - Cyberzoo with 4 panels
- **cyberzoo_orange_poles.world** - Cyberzoo with orange poles
- **cyberzoo_panel.world** - Cyberzoo panel test
- **cyberzoo2019_orange_poles.world** - 2019 version with poles
- **cyberzoo2019_orange_poles_panels.world** - Poles and panels
- **cyberzoo2019_orange_poles_panels_mats.world** - Full setup
- **cyberzoo2019_ralphthesis2020.world** - Thesis environment

#### Obstacle Testing
- **barrels.world** - Barrel obstacles
  - Use case: Simple obstacle avoidance
  - Complexity: Low

- **hemicyl.world** - Hemicylinder test
  - Use case: Geometric obstacle testing
  - Complexity: Low

- **azcar.world** - Azcar environment
  - Use case: Specific testing scenario
  - Complexity: Medium

### 🚁 Specialized Environments (9 worlds)

#### Aerial/Drone
- **drone_race_track_2018_actual.world** - Drone racing track
- **drone_race_track_2018_actual_with_gatepapers.world** - Racing with gates
- **empty_aerial_manipulation.world** - Aerial manipulation testing
- **wall_aerial_manipulation.world** - Wall manipulation testing

#### Challenge Variants
- **fetchit_challenge_atrezzo.world** - Challenge props
- **fetchit_challenge_tests.world** - Challenge tests
- **fetchit_challenge_tests_lowlights.world** - Low light testing
- **fetchit_challenge_simple_highlights.world** - Highlighted simple
- **fetchit_challenge_arena_montreal2019_highlights.world** - Highlighted arena

## World Selection by Use Case

### Navigation Testing
**Recommended Worlds:**
1. `mapping_world.world` - Purpose-built for navigation
2. `office_small.world` - Structured indoor
3. `warehouse.world` - Large open space
4. `empty.world` - Baseline testing

### Object Detection Testing
**Recommended Worlds:**
1. `office_small.world` - Office furniture
2. `warehouse.world` - Shelves and boxes
3. `dojo_world.world` - Training objects

### Obstacle Avoidance Testing
**Recommended Worlds:**
1. `barrels.world` - Simple obstacles
2. `rubble.world` - Complex debris
3. `office_earthquake.world` - Irregular obstacles

### SLAM and Mapping
**Recommended Worlds:**
1. `mapping_world.world` - Designed for SLAM
2. `office_env_large.world` - Large area mapping
3. `warehouse.world` - Structured mapping

### Performance Testing
**Recommended Worlds:**
1. `empty.world` - Baseline performance
2. `minimal.world` - Minimal overhead
3. `simple_env_1.world` - Simple test case

## Usage Examples

### Basic Launch
```bash
# Empty world (fastest, most stable)
ros2 launch robot_gazebo gazebo.launch.py world:=empty.world

# Office environment
ros2 launch robot_gazebo gazebo.launch.py world:=office_small.world

# Warehouse
ros2 launch robot_gazebo gazebo.launch.py world:=warehouse.world
```

### With Custom Spawn Position
```bash
ros2 launch robot_gazebo gazebo.launch.py \
    world:=warehouse.world \
    spawn_x:=5.0 \
    spawn_y:=5.0 \
    spawn_yaw:=1.57
```

### With RViz
```bash
ros2 launch robot_gazebo gazebo.launch.py \
    world:=office_small.world \
    rviz:=true
```

### Headless (No GUI)
```bash
ros2 launch robot_gazebo gazebo.launch.py \
    world:=mapping_world.world \
    gui:=false
```

## Known Issues and Limitations

### ⚠️ Gazebo Ogre2 Rendering Issue

**Current Status**: Robot model has compatibility issues with Gazebo Harmonic's Ogre2 rendering engine.

**Symptoms**:
- Segmentation fault when spawning robot
- Crash in `Ogre2Node::AttachChild`
- Affects all worlds when robot is loaded

**Workaround**:
- Issue is being investigated
- Worlds can be loaded without robot for testing
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for details

**Testing Status**:
- ✅ World files verified (54 worlds available)
- ✅ World selection system functional
- ⚠️ Robot spawning requires fix
- 🔧 Fix in progress

### World-Specific Issues

**Complex Worlds** (may have performance impact):
- `office_env_large.world` - High resource usage
- `small_city.world` - Complex geometry
- `powerplant.world` - Many objects

**External Dependencies** (may require internet):
- Some worlds reference Gazebo Fuel models
- First launch may download models
- Subsequent launches use cached models

## World Characteristics Reference

### Performance Ratings

| World | Load Time | CPU Usage | Memory | Complexity |
|-------|-----------|-----------|--------|------------|
| empty.world | Fast | Low | Low | Minimal |
| minimal.world | Fast | Low | Low | Minimal |
| mapping_world.world | Fast | Low-Med | Medium | Low-Med |
| office_small.world | Medium | Medium | Medium | Medium |
| warehouse.world | Medium | Medium | Medium | Medium |
| office_env_large.world | Slow | High | High | High |
| small_city.world | Slow | High | High | High |

### Recommended Spawn Positions

| World | X | Y | Z | Yaw | Notes |
|-------|---|---|---|-----|-------|
| empty.world | 0.0 | 0.0 | 0.1 | 0.0 | Center |
| mapping_world.world | 0.0 | 0.0 | 0.1 | 0.0 | Start area |
| office_small.world | 0.0 | 0.0 | 0.1 | 0.0 | Office entrance |
| warehouse.world | 5.0 | 5.0 | 0.1 | 0.0 | Clear area |
| outdoor.world | 0.0 | 0.0 | 0.2 | 0.0 | Ground level |

## Testing Checklist

When testing a new world, verify:

- [ ] World loads without errors
- [ ] Robot spawns successfully
- [ ] Sensors function correctly
- [ ] Navigation works as expected
- [ ] Performance is acceptable
- [ ] No collision issues
- [ ] Lighting is adequate

## Troubleshooting

### World Won't Load
```bash
# Check world file exists
ls src/robot_gazebo/worlds/<world_name>

# Try with verbose output
gz sim -v 4 src/robot_gazebo/worlds/<world_name>
```

### Robot Won't Spawn
```bash
# Check robot description
ros2 topic echo /robot_description --once

# Verify spawn service
ros2 service list | grep create
```

### Performance Issues
```bash
# Launch without GUI
ros2 launch robot_gazebo gazebo.launch.py world:=<world> gui:=false

# Reduce physics rate (in world file)
# <max_step_size>0.01</max_step_size>
```

## Future Enhancements

Planned improvements:
- [ ] Fix Gazebo Ogre2 rendering compatibility
- [ ] Add world preview images
- [ ] Create world difficulty ratings
- [ ] Add recommended robot configurations per world
- [ ] Implement world validation tests
- [ ] Create custom world templates
- [ ] Add world metadata system

## Related Documentation

- [Task 5.1 Verification](TASK_5.1_VERIFICATION.md) - World inventory
- [Task 5.2 Verification](TASK_5.2_VERIFICATION.md) - Launch system
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues
- [README](../README.md) - Main documentation

## Summary

- ✅ 54 worlds available across 4 categories
- ✅ World selection system functional
- ✅ Comprehensive world variety for testing
- ⚠️ Robot spawning issue being addressed
- 📚 Complete documentation provided

For the latest status on the Gazebo rendering issue, see the troubleshooting guide or check the project issues.
