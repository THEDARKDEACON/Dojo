# Dojo Robot File Structure Diagram

**Date**: November 11, 2025  
**Purpose**: Visual representation of the complete codebase structure

## Legend
- 📦 Package
- 🚀 Launch file
- 🐍 Python module
- ⚙️ Configuration file
- 📝 Documentation
- 🧪 Test file
- ⚠️ Potential duplicate/redundant
- ✅ Primary/recommended file
- 🔧 Utility script

---

## Complete Directory Tree

```
dojo-robot/
│
├── 📦 src/                                 # ROS2 Source Packages
│   │
│   ├── 📦 robot_bringup/                   # System Integration & Startup
│   │   ├── launch/
│   │   │   ├── 🚀 bringup.launch.py                    ✅ Primary real robot entry
│   │   │   ├── 🚀 rviz.launch.py                       Standard visualization
│   │   │   ├── 🚀 enhanced_rviz.launch.py              ⚠️ Advanced viz (consolidate?)
│   │   │   └── 🚀 vision_enhanced_system.launch.py     ⚠️ Vision-focused (review)
│   │   ├── robot_bringup/
│   │   │   ├── 🐍 __init__.py
│   │   │   └── 🐍 system_validator.py                  System health validation
│   │   ├── resource/
│   │   ├── 📝 package.xml
│   │   └── 📝 setup.py
│   │
│   ├── 📦 robot_control/                   # Motor Control & Hardware Interface
│   │   ├── launch/
│   │   │   ├── 🚀 control.launch.py                    ✅ Primary control entry
│   │   │   ├── 🚀 bypass_mode.launch.py                Direct motor control
│   │   │   ├── 🚀 configuration_manager.launch.py      Runtime config
│   │   │   ├── 🚀 health_monitoring.launch.py          System diagnostics
│   │   │   └── 🚀 safety_system.launch.py              Safety supervisor
│   │   ├── config/
│   │   │   ├── ⚙️ control_params.yaml
│   │   │   ├── ⚙️ control_controllers.yaml
│   │   │   ├── ⚙️ arduino_config.yaml
│   │   │   ├── ⚙️ bypass_config.yaml
│   │   │   ├── ⚙️ twist_mux_config.yaml
│   │   │   └── 📝 README.md
│   │   ├── robot_control/
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 control_manager.py                   Main control orchestration
│   │   │   ├── 🐍 cmd_vel_to_motors.py                 Velocity conversion
│   │   │   ├── 🐍 velocity_limiter.py                  Safety limiting
│   │   │   ├── 🐍 arduino_bridge.py                    Arduino communication
│   │   │   ├── 🐍 direct_arduino_driver.py             Direct Arduino control
│   │   │   ├── 🐍 hardware_manager.py                  Hardware lifecycle
│   │   │   ├── 🐍 hardware_discovery.py                Auto-discovery
│   │   │   ├── 🐍 device_abstraction.py                Hardware abstraction
│   │   │   ├── 🐍 device_implementations.py            Device implementations
│   │   │   ├── 🐍 camera_driver.py                     Camera interface
│   │   │   ├── 🐍 lidar_driver.py                      LiDAR interface
│   │   │   ├── 🐍 safety_supervisor.py                 Safety monitoring
│   │   │   ├── 🐍 safety_override_manager.py           Safety overrides
│   │   │   ├── 🐍 emergency_stop_handler.py            E-stop handling
│   │   │   ├── 🐍 watchdog_system.py                   System watchdog
│   │   │   ├── 🐍 diagnostic_system.py                 Diagnostics
│   │   │   ├── 🐍 graceful_degradation.py              Degraded mode
│   │   │   ├── 🐍 configuration_manager.py             Runtime config
│   │   │   ├── 🐍 configuration_override.py            Config overrides
│   │   │   ├── 🐍 revert_parameters.py                 Parameter restore
│   │   │   ├── 🐍 bypass_controller.py                 Bypass mode
│   │   │   ├── 🐍 launch_utils.py                      Launch utilities
│   │   │   ├── 🧪 test_configuration_override.py       ⚠️ Move to test/
│   │   │   └── 🧪 test_enhanced_camera_driver.py       ⚠️ Move to test/
│   │   ├── 📝 README.md
│   │   ├── 📝 package.xml
│   │   └── 📝 setup.py
│   │
│   ├── 📦 robot_description/               # URDF Models & Robot Description
│   │   ├── launch/
│   │   │   ├── 🚀 description.launch.py                ✅ Robot description publisher
│   │   │   ├── 🚀 robot_state_publisher.launch.py     ⚠️ DUPLICATE - remove
│   │   │   └── 🚀 display.launch.py                    URDF visualization
│   │   ├── urdf/
│   │   │   ├── robot.urdf
│   │   │   ├── robot.urdf.xacro                        ✅ Main robot model
│   │   │   ├── robot_humble.urdf.xacro
│   │   │   ├── common_properties.xacro
│   │   │   ├── dojo_robot.gazebo
│   │   │   └── sensors/                                Sensor definitions
│   │   ├── rviz/
│   │   │   ├── robot_display.rviz
│   │   │   └── robot_simulation.rviz
│   │   ├── config/
│   │   │   ├── ⚙️ control_controllers_template.yaml
│   │   │   └── 📝 README.md
│   │   ├── scripts/
│   │   │   └── 🔧 display_robot.py
│   │   ├── 📝 README.md
│   │   ├── 📝 package.xml
│   │   └── 📝 setup.py
│   │
│   ├── 📦 robot_gazebo/                    # Simulation Environments
│   │   ├── launch/
│   │   │   ├── 🚀 complete_simulation.launch.py        ✅ PRIMARY SIMULATION ENTRY
│   │   │   ├── 🚀 gazebo.launch.py                     Gazebo world launcher
│   │   │   ├── 🚀 simulation.launch.py                 ⚠️ DUPLICATE - remove
│   │   │   └── 🚀 simulation_with_teleop.launch.py     Sim + teleop mode
│   │   ├── worlds/                                     60+ world files
│   │   │   ├── mapping_world.world                     ✅ Default testing world
│   │   │   ├── house.world                             Residential environment
│   │   │   ├── office_small.world                      Office environment
│   │   │   ├── warehouse.world                         Large warehouse
│   │   │   ├── outdoor.world                           Outdoor terrain
│   │   │   ├── empty.world                             Minimal testing
│   │   │   ├── minimal.world                           Basic testing
│   │   │   ├── dojo_world.world                        Custom world
│   │   │   └── ... (50+ more worlds)
│   │   ├── rviz/
│   │   │   ├── simulation.rviz
│   │   │   ├── simulation_with_sensors.rviz
│   │   │   ├── navigation_with_map.rviz
│   │   │   └── pointcloud_3d_visualization.rviz        3D point cloud viz
│   │   ├── config/
│   │   │   ├── ⚙️ gazebo_controllers.yaml
│   │   │   ├── ⚙️ ros2_controllers.yaml
│   │   │   ├── ⚙️ diff_drive_controller.yaml
│   │   │   ├── ⚙️ ekf_config.yaml
│   │   │   ├── ⚙️ slam_config.yaml
│   │   │   └── 📝 README.md
│   │   ├── scripts/
│   │   │   └── 🔧 spawn_robot.py
│   │   ├── robot_gazebo/
│   │   │   ├── 🐍 __init__.py
│   │   │   └── 🐍 cmd_vel_relay.py                     Command relay
│   │   ├── 📝 README.md
│   │   ├── 📝 package.xml
│   │   └── 📝 setup.py
│   │
│   ├── 📦 robot_hardware/                  # Hardware Drivers & Interfaces
│   │   ├── launch/
│   │   │   ├── 🚀 hardware.launch.py                   ✅ Primary hardware entry
│   │   │   ├── 🚀 arduino_only.launch.py               Arduino-only mode
│   │   │   └── 🚀 rosarduino_bridge.launch.py          ROSArduinoBridge
│   │   ├── config/
│   │   │   ├── ⚙️ hardware.yaml
│   │   │   ├── ⚙️ hardware_config.yaml
│   │   │   ├── ⚙️ rosarduino_bridge_config.yaml
│   │   │   ├── ⚙️ slam_config.yaml
│   │   │   └── 📝 README.md
│   │   ├── robot_hardware/
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 hardware_manager.py                  Hardware lifecycle
│   │   │   └── drivers/                                Hardware drivers
│   │   ├── 📝 package.xml
│   │   └── 📝 setup.py
│   │
│   ├── 📦 robot_interfaces/                # Custom ROS2 Messages & Services
│   │   ├── msg/
│   │   │   ├── EmergencyStop.msg
│   │   │   ├── HardwareStatus.msg
│   │   │   ├── MotorCommand.msg
│   │   │   ├── RobotState.msg
│   │   │   ├── SafetyStatus.msg
│   │   │   └── SensorData.msg
│   │   ├── srv/
│   │   │   ├── Calibration.srv
│   │   │   └── SetMode.srv
│   │   ├── action/
│   │   │   └── Navigation.action
│   │   ├── 📝 CMakeLists.txt
│   │   └── 📝 package.xml
│   │
│   ├── 📦 robot_navigation/                # Navigation & Path Planning
│   │   ├── launch/
│   │   │   ├── 🚀 navigation.launch.py                 ✅ Primary navigation
│   │   │   ├── 🚀 nav2.launch.py                       Nav2 stack
│   │   │   ├── 🚀 slam.launch.py                       SLAM system
│   │   │   ├── 🚀 localization.launch.py               Localization (AMCL/EKF)
│   │   │   ├── 🚀 map_server.launch.py                 Map server
│   │   │   ├── 🚀 autonomous_exploration.launch.py     Auto exploration
│   │   │   └── 🚀 autonomous_movement.launch.py        Auto movement
│   │   ├── config/
│   │   │   ├── ⚙️ nav2_params.yaml                     ✅ Main Nav2 config
│   │   │   ├── ⚙️ bt_navigator_params.yaml
│   │   │   ├── ⚙️ controller_params.yaml
│   │   │   ├── ⚙️ planner_params.yaml
│   │   │   ├── ⚙️ costmap_common_params.yaml
│   │   │   ├── ⚙️ global_costmap_params.yaml
│   │   │   ├── ⚙️ local_costmap_params.yaml
│   │   │   ├── ⚙️ localization_params.yaml
│   │   │   ├── ⚙️ map_server_params.yaml
│   │   │   └── 📝 README.md
│   │   ├── robot_navigation/
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 autonomous_explorer.py               Autonomous exploration
│   │   │   ├── 🐍 autonomous_movement_controller.py    Movement control
│   │   │   ├── 🐍 frame_validator.py                   TF validation
│   │   │   ├── 🐍 map_diagnostic_node.py               Map diagnostics
│   │   │   └── 🐍 map_status_monitor.py                Map monitoring
│   │   ├── 📝 package.xml
│   │   └── 📝 setup.py
│   │
│   ├── 📦 robot_perception/                # Vision & Sensor Processing
│   │   ├── launch/
│   │   │   ├── 🚀 perception.launch.py                 ✅ Primary perception
│   │   │   ├── 🚀 perception_system.launch.py          System-level perception
│   │   │   ├── 🚀 perception_integration.launch.py     Integration layer
│   │   │   ├── 🚀 object_detector.launch.py            Object detection
│   │   │   └── 🚀 vision_detection.launch.py           ⚠️ DUPLICATE - remove
│   │   ├── config/
│   │   │   ├── ⚙️ perception_params.yaml
│   │   │   ├── ⚙️ robot_perception_params.yaml
│   │   │   └── 📝 README.md
│   │   ├── robot_perception/
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── nodes/
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── 🐍 camera_processor.py              Camera processing
│   │   │   │   ├── 🐍 lidar_processor.py               LiDAR processing
│   │   │   │   ├── 🐍 object_detector.py               Object detection
│   │   │   │   ├── 🐍 vision_detection_node.py         Vision detection
│   │   │   │   └── 🐍 perception_integrator.py         Integration
│   │   │   ├── utils/
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── 🐍 common.py                        Common utilities
│   │   │   │   └── 🐍 config.py                        Config utilities
│   │   │   ├── 🐍 performance_monitor.py               Performance tracking
│   │   │   ├── 🐍 resource_manager.py                  Resource management
│   │   │   ├── 🧪 test_performance_monitoring.py       ⚠️ Move to test/
│   │   │   └── yolov8n.pt                              YOLO model weights
│   │   ├── rviz/
│   │   │   └── perception.rviz
│   │   ├── scripts/
│   │   │   ├── 🔧 camera_processor
│   │   │   └── 🔧 object_detector
│   │   ├── 📝 README.md
│   │   ├── 📝 DEPENDENCIES.md
│   │   ├── 📝 package.xml
│   │   └── 📝 setup.py
│   │
│   └── 📦 robot_semantic_slam/             # Semantic SLAM & Advanced Features
│       ├── launch/
│       │   ├── 🚀 semantic_slam.launch.py              Core semantic SLAM
│       │   ├── 🚀 semantic_interface.launch.py         Natural language interface
│       │   ├── 🚀 advanced_safety.launch.py            Predictive safety
│       │   ├── 🚀 enhanced_visualization.launch.py     3D visualization
│       │   ├── 🚀 performance_dashboard.launch.py      Metrics dashboard
│       │   └── 🚀 cutting_edge_features.launch.py      ✅ MASTER LAUNCHER (Priority 1)
│       ├── robot_semantic_slam/
│       │   ├── 🐍 __init__.py
│       │   ├── 🐍 semantic_slam_node.py                ✅ Core semantic SLAM
│       │   ├── 🐍 semantic_interface.py                Natural language commands
│       │   ├── 🐍 advanced_safety_system.py            Predictive safety
│       │   ├── 🐍 enhanced_visualizer.py               3D visualization
│       │   ├── 🐍 performance_dashboard.py             Metrics dashboard
│       │   └── 🐍 pointcloud_processor.py              Point cloud processing
│       ├── test/
│       │   ├── 🧪 test_behavior_tree_safety.py         ✅ Proper location
│       │   ├── 🧪 test_semantic_navigation.py
│       │   ├── 🧪 test_object_persistence.py
│       │   └── 🧪 test_lidar_camera_fusion.py
│       ├── 📝 package.xml
│       └── 📝 setup.py
│
├── 🔧 scripts/                             # Utility Scripts
│   ├── 🔧 build_workspace.sh                           ✅ Build ROS2 workspace
│   ├── 🔧 install_dependencies.sh                      Install system deps
│   ├── 🔧 ensure_build_deps.sh                         Pre-build check
│   ├── 🔧 check_dependencies.sh                        Dependency validation
│   ├── 🔧 test_configuration.py                        Config validation
│   ├── 🔧 test_simulation_setup.py                     Sim validation
│   ├── 🔧 test_system_integration.py                   ✅ Integration tests
│   ├── 🔧 validate_system_integration.py               ⚠️ DUPLICATE - merge
│   ├── 🔧 validate_system_structure.py                 Structure checks
│   ├── 🔧 validate_cleanup.sh                          Post-cleanup validation
│   ├── 🔧 launch_robot.py                              High-level launcher
│   ├── 🔧 launch_simulation.sh                         Sim launcher
│   ├── 🔧 backup_system.sh                             Backup utility
│   ├── 🔧 rollback_phase.sh                            Recovery utility
│   └── 📝 README_cleanup_tools.md
│
├── 📝 docs/                                # Documentation
│   ├── 📝 IMPLEMENTATION_GUIDE.md                      ✅ Main implementation guide
│   ├── 📝 TROUBLESHOOTING.md                           Troubleshooting guide
│   ├── 📝 BEHAVIOR_TREE_SAFETY.md                      Safety system docs
│   ├── 📝 PERFORMANCE_DASHBOARD.md                     Dashboard docs
│   ├── 📝 RVIZ_3D_VISUALIZATION_GUIDE.md               Visualization guide
│   ├── 📝 GAZEBO_OGRE2_FIX.md                          Gazebo fix docs
│   ├── 📝 WORLD_SELECTION_GUIDE.md                     World selection guide
│   ├── 📝 TASK_4.2_SUMMARY.md                          ⚠️ Consolidate into progress doc
│   ├── 📝 TASK_4.3_VERIFICATION.md                     ⚠️ Consolidate
│   ├── 📝 TASK_4.4_SUMMARY.md                          ⚠️ Consolidate
│   ├── 📝 TASK_4.5_SUMMARY.md                          ⚠️ Consolidate
│   ├── 📝 TASK_4.6_SUMMARY.md                          ⚠️ Consolidate
│   ├── 📝 TASK_4.6_TEST_PLAN.md                        ⚠️ Consolidate
│   ├── 📝 TASK_5.1_VERIFICATION.md                     ⚠️ Consolidate
│   ├── 📝 TASK_5.2_VERIFICATION.md                     ⚠️ Consolidate
│   ├── 📝 CODEBASE_STRUCTURE_ANALYSIS.md               ✅ This analysis (NEW)
│   └── 📝 FILE_STRUCTURE_DIAGRAM.md                    ✅ This diagram (NEW)
│
├── ⚙️ config/                              # Top-Level Configuration
│   ├── ⚙️ robot_config.yaml                            Main robot config
│   ├── ⚙️ nav2_params.yaml                             Nav2 parameters
│   └── 📝 README.md
│
├── firmware/                               # Arduino Firmware
│   └── arduino/
│       ├── ROSArduinoBridge/                           ROSArduinoBridge firmware
│       │   ├── ROSArduinoBridge.ino
│       │   ├── commands.h
│       │   ├── diff_controller.h
│       │   ├── encoder_driver.h
│       │   ├── encoder_driver.ino
│       │   ├── motor_driver.h
│       │   ├── motor_driver.ino
│       │   ├── sensors.h
│       │   └── 📝 README.md
│       └── ros2_motor_controller/
│           └── ros2_motor_controller.ino
│
├── build/                                  # Build Artifacts (generated)
├── install/                                # Install Artifacts (generated)
├── log/                                    # Build Logs (generated)
│
├── 📝 README.md                            # ✅ Main project documentation
├── 🔧 install_vision_deps.sh               # Vision dependencies installer
├── 🔧 start_cutting_edge_robot.py          # ✅ Master launcher for Priority 1 features
├── 📝 requirements.txt                     # Python dependencies
├── 📝 CLEANUP_SUMMARY.md                   # Cleanup documentation
├── 📝 TASK_2_3_HANDOFF.md                  # Task handoff doc
├── 📝 .gitignore                           # Git ignore rules
│
└── .kiro/                                  # Kiro Specs & Configuration
    └── specs/
        ├── cutting-edge-features-implementation/
        │   ├── 📝 requirements.md
        │   ├── 📝 design.md
        │   └── 📝 tasks.md                             ✅ Current spec
        ├── autonomous-mapping-fix/
        ├── codebase-cleanup/
        ├── comprehensive-robot-fixes/
        ├── fix-robot-perception/
        ├── jazzy-harmonic-migration/
        └── slam-odometry-fix/
```

---

## Key Insights from Visual Structure

### Well-Organized Areas ✅
1. **robot_semantic_slam**: Clean structure, proper test directory, clear module purposes
2. **robot_navigation**: Well-organized launch files, comprehensive configs
3. **robot_hardware**: Simple, focused, no redundancy
4. **robot_interfaces**: Clean message/service definitions

### Areas Needing Cleanup ⚠️
1. **robot_perception**: 6 launch files with significant overlap (HIGH PRIORITY)
2. **robot_control**: Duplicate launch file, misplaced tests
3. **robot_description**: Duplicate state publisher launch
4. **robot_gazebo**: Duplicate simulation launch
5. **robot_bringup**: Potential RViz consolidation opportunity
6. **docs/**: 9 task summary files to consolidate
7. **Root directory**: Duplicate build script

### Primary Entry Points 🚀
- **Simulation**: `complete_simulation.launch.py` or `start_cutting_edge_robot.py`
- **Real Robot**: `bringup.launch.py`
- **Advanced Features**: `cutting_edge_features.launch.py`

---

## File Count Summary

| Category | Count | Clean | Needs Review |
|----------|-------|-------|--------------|
| Launch Files | 36 | 32 | 4 |
| Python Modules | 67 | 64 | 3 |
| Utility Scripts | 13 | 12 | 1 |
| Config Files | ~30 | ~30 | 0 |
| Documentation | 18 | 9 | 9 |
| Test Files | 7 | 4 | 3 |
| **Total** | **~171** | **~151** | **~20** |

**Cleanup Progress**: Removed 3 files (Task 6.2 complete) | Remaining: ~20 files for consolidation

---

**Diagram created**: November 11, 2025  
**Next**: Proceed with file removal and consolidation (Task 6.2)
