#!/usr/bin/env python3
"""
Complete Robot Simulation with Priority 1 Features
Unified launch file for all cutting-edge features with world selection
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    RegisterEventHandler,
    TimerAction,
    LogInfo,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessStart
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
    PythonExpression,
)
from launch_ros.actions import Node, SetParameter
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    """Generate launch description with all Priority 1 features"""
    
    # ============================================================================
    # LAUNCH ARGUMENTS
    # ============================================================================
    
    # World and simulation
    world_arg = DeclareLaunchArgument(
        'world',
        default_value='mapping_world',
        description='Gazebo world name (without .world extension)'
    )
    
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation time'
    )
    
    gui_arg = DeclareLaunchArgument(
        'gui',
        default_value='true',
        description='Start Gazebo GUI'
    )
    
    rviz_arg = DeclareLaunchArgument(
        'rviz',
        default_value='true',
        description='Launch RViz visualization'
    )
    
    # Core features
    slam_arg = DeclareLaunchArgument(
        'slam',
        default_value='true',
        description='Enable SLAM mapping'
    )
    
    navigation_arg = DeclareLaunchArgument(
        'navigation',
        default_value='false',
        description='Enable Nav2 navigation stack'
    )
    
    # Priority 1 features
    semantic_slam_arg = DeclareLaunchArgument(
        'semantic_slam',
        default_value='true',
        description='Enable semantic SLAM with YOLO object detection'
    )
    
    pointcloud_viz_arg = DeclareLaunchArgument(
        'pointcloud_viz',
        default_value='true',
        description='Enable 3D point cloud visualization'
    )
    
    performance_dashboard_arg = DeclareLaunchArgument(
        'performance_dashboard',
        default_value='true',
        description='Enable real-time performance dashboard'
    )
    
    advanced_safety_arg = DeclareLaunchArgument(
        'advanced_safety',
        default_value='true',
        description='Enable advanced safety system with behavior trees'
    )
    
    semantic_interface_arg = DeclareLaunchArgument(
        'semantic_interface',
        default_value='true',
        description='Enable natural language command interface'
    )
    
    # Additional features
    autonomous_exploration_arg = DeclareLaunchArgument(
        'autonomous_exploration',
        default_value='false',
        description='Enable autonomous exploration'
    )
    
    vision_arg = DeclareLaunchArgument(
        'vision',
        default_value='true',
        description='Enable vision/perception systems'
    )
    
    # ============================================================================
    # LAUNCH CONFIGURATIONS
    # ============================================================================
    
    world = LaunchConfiguration('world')
    use_sim_time = LaunchConfiguration('use_sim_time')
    gui = LaunchConfiguration('gui')
    rviz = LaunchConfiguration('rviz')
    slam = LaunchConfiguration('slam')
    navigation = LaunchConfiguration('navigation')
    semantic_slam = LaunchConfiguration('semantic_slam')
    pointcloud_viz = LaunchConfiguration('pointcloud_viz')
    performance_dashboard = LaunchConfiguration('performance_dashboard')
    advanced_safety = LaunchConfiguration('advanced_safety')
    semantic_interface = LaunchConfiguration('semantic_interface')
    autonomous_exploration = LaunchConfiguration('autonomous_exploration')
    vision = LaunchConfiguration('vision')
    
    # ============================================================================
    # PACKAGE PATHS
    # ============================================================================
    
    pkg_robot_gazebo = FindPackageShare('robot_gazebo')
    pkg_robot_semantic_slam = FindPackageShare('robot_semantic_slam')
    pkg_robot_navigation = FindPackageShare('robot_navigation')
    
    # ============================================================================
    # STARTUP BANNER
    # ============================================================================
    
    startup_banner = LogInfo(
        msg=[
            '\n',
            '='*80, '\n',
            '🚀 DOJO ROBOT - PRIORITY 1 FEATURES LAUNCH\n',
            '='*80, '\n',
            '🤖 Semantic SLAM with YOLO Object Detection\n',
            '🎨 3D Point Cloud Visualization\n',
            '📊 Real-Time Performance Dashboard\n',
            '🛡️  Advanced Safety System with Behavior Trees\n',
            '🗣️  Natural Language Command Interface\n',
            '🌍 Multi-World Support\n',
            '='*80, '\n',
            'World: ', world, '\n',
            'Features: All Priority 1 Active\n',
            '='*80, '\n'
        ]
    )
    
    # ============================================================================
    # CORE SIMULATION
    # ============================================================================
    
    # Gazebo simulation with world selection
    world_file = PathJoinSubstitution([
        pkg_robot_gazebo,
        'worlds',
        [world, '.world']
    ])
    
    gazebo_simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([pkg_robot_gazebo, 'launch', 'gazebo.launch.py'])
        ]),
        launch_arguments={
            'world': world_file,
            'use_sim_time': use_sim_time,
            'gui': gui,
            'rviz': 'false',  # We'll launch RViz separately
            'use_config_manager': 'true'
        }.items(),
    )
    
    # ============================================================================
    # SLAM
    # ============================================================================
    
    slam_toolbox = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            PathJoinSubstitution([pkg_robot_gazebo, 'config', 'slam_config.yaml']),
            {'use_sim_time': use_sim_time}
        ],
        condition=IfCondition(slam)
    )
    
    # ============================================================================
    # PRIORITY 1 FEATURES
    # ============================================================================
    
    # Cutting-Edge Features Launch (includes all Priority 1 features)
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
        }.items(),
    )
    
    # ============================================================================
    # NAVIGATION (Optional)
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
    # AUTONOMOUS EXPLORATION (Optional)
    # ============================================================================
    
    autonomous_explorer = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                pkg_robot_navigation,
                'launch',
                'autonomous_exploration.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
        }.items(),
        condition=IfCondition(autonomous_exploration)
    )
    
    # ============================================================================
    # RVIZ VISUALIZATION
    # ============================================================================
    
    # Use specialized RViz config for 3D visualization
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
    # SYSTEM MONITOR
    # ============================================================================
    
    system_monitor = Node(
        package='robot_semantic_slam',
        executable='system_monitor.py',
        name='system_monitor',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
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
        slam_arg,
        navigation_arg,
        semantic_slam_arg,
        pointcloud_viz_arg,
        performance_dashboard_arg,
        advanced_safety_arg,
        semantic_interface_arg,
        autonomous_exploration_arg,
        vision_arg,
        
        # Set global parameter
        SetParameter(name='use_sim_time', value=use_sim_time),
        
        # Startup banner
        startup_banner,
        
        # Core simulation
        gazebo_simulation,
        
        # SLAM
        TimerAction(
            period=3.0,
            actions=[slam_toolbox]
        ),
        
        # Priority 1 Features (delayed start for stability)
        TimerAction(
            period=5.0,
            actions=[cutting_edge_features]
        ),
        
        # Navigation (optional)
        TimerAction(
            period=8.0,
            actions=[nav2_stack]
        ),
        
        # Autonomous exploration (optional)
        TimerAction(
            period=10.0,
            actions=[autonomous_explorer]
        ),
        
        # Visualization
        TimerAction(
            period=7.0,
            actions=[rviz_node]
        ),
        
        # System monitor
        TimerAction(
            period=2.0,
            actions=[system_monitor]
        ),
    ])
