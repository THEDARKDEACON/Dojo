#!/usr/bin/env python3

"""
Complete Dojo Robot with ROSbot XL Integration
Full feature set: ROSbot XL URDF + All Dojo Advanced Features
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    TimerAction,
    LogInfo,
    ExecuteProcess,
    GroupAction,
)
from launch_ros.actions import Node, SetParameter, SetRemap

from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node, SetParameter
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    """Launch complete Dojo robot with ROSbot XL integration"""
    
    # ============================================================================
    # LAUNCH ARGUMENTS
    # ============================================================================
    
    # World and simulation
    world_arg = DeclareLaunchArgument(
        'world',
        default_value='office',
        description='World file (office.sdf, warehouse.sdf, husarion_world.sdf, etc.)'
    )
    
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='True',
        description='Use simulation time'
    )
    
    gui_arg = DeclareLaunchArgument(
        'gui',
        default_value='True',
        description='Start Gazebo GUI'
    )
    
    rviz_arg = DeclareLaunchArgument(
        'rviz',
        default_value='True',
        description='Launch RViz visualization'
    )
    
    mecanum_arg = DeclareLaunchArgument(
        'mecanum',
        default_value='False',
        description='Use Mecanum wheels (holonomic drive)'
    )
    
    # Core features
    slam_arg = DeclareLaunchArgument(
        'slam',
        default_value='True',
        description='Enable SLAM mapping'
    )
    
    navigation_arg = DeclareLaunchArgument(
        'navigation',
        default_value='True',
        description='Enable Nav2 navigation stack'
    )
    
    # Dojo advanced features
    semantic_slam_arg = DeclareLaunchArgument(
        'semantic_slam',
        default_value='True',
        description='Enable semantic SLAM with YOLO object detection'
    )
    
    pointcloud_viz_arg = DeclareLaunchArgument(
        'pointcloud_viz',
        default_value='True',
        description='Enable 3D point cloud visualization'
    )
    
    performance_dashboard_arg = DeclareLaunchArgument(
        'performance_dashboard',
        default_value='True',
        description='Enable real-time performance dashboard'
    )
    
    advanced_safety_arg = DeclareLaunchArgument(
        'advanced_safety',
        default_value='True',
        description='Enable advanced safety system with behavior trees'
    )
    
    semantic_interface_arg = DeclareLaunchArgument(
        'semantic_interface',
        default_value='True',
        description='Enable natural language command interface'
    )
    
    gaussian_splatting_arg = DeclareLaunchArgument(
        'gaussian_splatting',
        default_value='False',
        description='Enable Gaussian Splatting data collection mode'
    )
    
    autonomous_exploration_arg = DeclareLaunchArgument(
        'autonomous_exploration',
        default_value='True',
        description='Enable autonomous exploration for mapping'
    )

    # ============================================================================
    # LAUNCH CONFIGURATIONS
    # ============================================================================
    
    world = LaunchConfiguration('world')
    use_sim_time = LaunchConfiguration('use_sim_time')
    gui = LaunchConfiguration('gui')
    rviz = LaunchConfiguration('rviz')
    mecanum = LaunchConfiguration('mecanum')
    slam = LaunchConfiguration('slam')
    navigation = LaunchConfiguration('navigation')
    semantic_slam = LaunchConfiguration('semantic_slam')
    pointcloud_viz = LaunchConfiguration('pointcloud_viz')
    gaussian_splatting = LaunchConfiguration('gaussian_splatting')
    performance_dashboard = LaunchConfiguration('performance_dashboard')
    advanced_safety = LaunchConfiguration('advanced_safety')
    semantic_interface = LaunchConfiguration('semantic_interface')
    autonomous_exploration = LaunchConfiguration('autonomous_exploration')
    
    
    # ============================================================================
    # PACKAGE PATHS
    # ============================================================================
    
    pkg_rosbot_xl_gazebo = FindPackageShare('rosbot_xl_gazebo')
    pkg_husarion_gz_worlds = FindPackageShare('husarion_gz_worlds')
    pkg_robot_semantic_slam = FindPackageShare('robot_semantic_slam')
    pkg_robot_navigation = FindPackageShare('robot_navigation')
    pkg_robot_gazebo = FindPackageShare('robot_gazebo')
    
    # ============================================================================
    # STARTUP BANNER
    # ============================================================================
    
    startup_banner = LogInfo(
        msg=[
            '\n',
            '='*80, '\n',
            '🚀 DOJO ROBOT - COMPLETE SYSTEM WITH ROSBOT XL\n',
            '='*80, '\n',
            '🤖 ROSbot XL Professional URDF & Controls\n',
            '🗺️  Husarion Gazebo Worlds (188 environments)\n',
            '📍 SLAM Mapping (Auto-enabled for Nav2/Exploration)\n',
            '🎯 Semantic SLAM with YOLO Detection\n',
            '✨ Gaussian Splatting 3D Reconstruction\n',
            '🛡️  Advanced Safety with Behavior Trees\n',
            '📊 Real-Time Performance Dashboard\n',
            '🧭 Nav2 Navigation (Requires SLAM)\n',
            '🔍 Autonomous Exploration (Requires SLAM + Nav2)\n',
            '🗣️  Natural Language Interface\n',
            '='*80, '\n',
            '⚠️  DEPENDENCY: Nav2 and Exploration require SLAM (auto-enabled)\n',
            '='*80, '\n',
            'World: ', world, '\n',
            '='*80, '\n'
        ]
    )
    
    # ============================================================================
    # CLOCK GENERATOR (Using Lidar Trigger)
    # ============================================================================
    
    imu_to_clock = ExecuteProcess(
        cmd=['python3', '/home/gareth-joel/Downloads/Dojo/scripts/imu_to_clock.py'],
        output='screen',
        condition=IfCondition(use_sim_time)
    )

    scan_republisher = ExecuteProcess(
        cmd=['python3', '/home/gareth-joel/Downloads/Dojo/scripts/scan_republisher.py', '--ros-args', '-p', 'use_sim_time:=true'],
        output='screen',
        condition=IfCondition(use_sim_time)
    )

    cmd_vel_relay = ExecuteProcess(
        cmd=['python3', '/home/gareth-joel/Downloads/Dojo/scripts/cmd_vel_relay.py'],
        output='screen',
        condition=IfCondition(use_sim_time)
    )

    # ============================================================================
    # ROSBOT XL SIMULATION
    # ============================================================================
    
    # Build world path
    world_file = PathJoinSubstitution([
        pkg_husarion_gz_worlds,
        'worlds',
        [world, '.sdf']
    ])
    
    rosbot_xl_simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([pkg_rosbot_xl_gazebo, 'launch', 'simulation.launch.py'])
        ]),
        launch_arguments={
            'world': world_file,
            'headless': PythonExpression(["'True' if not '", gui, "' else 'False'"]),
            'mecanum': mecanum,
            'lidar_model': 'slamtec_rplidar',  # For SLAM
            'camera_model': 'intel_realsense_d435',  # For vision
            'use_sim_time': use_sim_time,
        }.items(),
    )
    
    # ============================================================================
    # SLAM
    # ============================================================================
    
    slam_config = PathJoinSubstitution([pkg_robot_gazebo, 'config', 'slam_config.yaml'])
    
    slam_toolbox = GroupAction([
        # SetRemap(src='/scan', dst='/scan_relayed'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('slam_toolbox'),
                    'launch',
                    'online_async_launch.py'
                ])
            ]),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'slam_params_file': slam_config,
            }.items(),
            condition=IfCondition(slam)
        )
    ])
    
    # ============================================================================
    # DOJO FEATURES (via cutting_edge_features.launch.py)
    # ============================================================================
    
    cutting_edge_features = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                pkg_robot_semantic_slam,
                'launch',
                'cutting_edge_features.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'use_semantic_slam': semantic_slam,
            'use_enhanced_viz': pointcloud_viz,
            'use_performance_dashboard': performance_dashboard,
            'use_advanced_safety': advanced_safety,
            'use_semantic_interface': semantic_interface,
            'use_gaussian_splatting': gaussian_splatting,
        }.items(),
    )
    
    # ============================================================================
    # NAVIGATION (FIXED!)
    # ============================================================================
    
    nav2_stack = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([pkg_robot_navigation, 'launch', 'nav2.launch.py'])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
        }.items(),
        condition=IfCondition(navigation)
    )
    
    # ============================================================================
    # AUTONOMOUS EXPLORATION (FIXED!)
    # ============================================================================
    
    autonomous_exploration_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                pkg_robot_navigation,
                'launch',
                'autonomous_exploration.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'gaussian_splat_mode': gaussian_splatting,
        }.items(),
        condition=IfCondition(autonomous_exploration)
    )
    
    # ============================================================================
    # RVIZ VISUALIZATION
    # ============================================================================
    
    rviz_config = PathJoinSubstitution([
        pkg_robot_gazebo,
        'rviz',
        'pointcloud_3d_visualization.rviz'
    ])
    
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(rviz)
    )
    
    # ============================================================================
    # LAUNCH DESCRIPTION
    # ============================================================================
    
    return LaunchDescription([
        # Arguments
        world_arg,
        use_sim_time_arg,
        gui_arg,
        rviz_arg,
        mecanum_arg,
        slam_arg,
        navigation_arg,
        semantic_slam_arg,
        pointcloud_viz_arg,
        performance_dashboard_arg,
        advanced_safety_arg,
        semantic_interface_arg,
        gaussian_splatting_arg,
        autonomous_exploration_arg,
        
        # Set global parameter
        SetParameter(name='use_sim_time', value=use_sim_time),
        
        # Startup banner
        startup_banner,
        
        # Fake Clock / IMU Clock Bridge
        # fake_clock,
        # imu_to_clock,
        # scan_republisher,
        cmd_vel_relay,
        
        # ROSbot XL Simulation (URDF, Gazebo, sensors, controllers)
        rosbot_xl_simulation,
        
        # SLAM (delayed for Gazebo to start)
        TimerAction(
            period=3.0,
            actions=[slam_toolbox]
        ),
        
        # Dojo Advanced Features (delayed for stability)
        TimerAction(
            period=5.0,
            actions=[cutting_edge_features]
        ),
        
        # Navigation Stack (if enabled - waits for SLAM map)
        TimerAction(
            period=30.0,  # Increased: wait longer for SLAM to publish /map
            actions=[nav2_stack]
        ),
        
        # Autonomous Exploration (if enabled - waits for Nav2)
        TimerAction(
            period=40.0,  # Increased: wait for Nav2 to fully initialize
            actions=[autonomous_exploration_node]
        ),
        
        # RViz Visualization
        TimerAction(
            period=7.0,
            actions=[rviz_node]
        ),
    ])
