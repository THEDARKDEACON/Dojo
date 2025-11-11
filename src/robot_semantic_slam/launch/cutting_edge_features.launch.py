#!/usr/bin/env python3
"""
Cutting-Edge Features Launch File
Modular launcher for advanced AI and robotics features
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    # Declare launch arguments
    use_semantic_slam_arg = DeclareLaunchArgument(
        'use_semantic_slam',
        default_value='true',
        description='Enable semantic SLAM with object detection'
    )
    
    use_enhanced_viz_arg = DeclareLaunchArgument(
        'use_enhanced_viz',
        default_value='true',
        description='Enable enhanced 3D visualization and performance dashboard'
    )
    
    use_advanced_safety_arg = DeclareLaunchArgument(
        'use_advanced_safety',
        default_value='true',
        description='Enable advanced safety system with predictive collision avoidance'
    )
    
    use_semantic_interface_arg = DeclareLaunchArgument(
        'use_semantic_interface',
        default_value='true',
        description='Enable natural language command interface'
    )
    
    use_performance_dashboard_arg = DeclareLaunchArgument(
        'use_performance_dashboard',
        default_value='true',
        description='Enable real-time performance monitoring dashboard'
    )
    
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation time'
    )
    
    # Launch configurations
    use_semantic_slam = LaunchConfiguration('use_semantic_slam')
    use_enhanced_viz = LaunchConfiguration('use_enhanced_viz')
    use_advanced_safety = LaunchConfiguration('use_advanced_safety')
    use_semantic_interface = LaunchConfiguration('use_semantic_interface')
    use_performance_dashboard = LaunchConfiguration('use_performance_dashboard')
    use_sim_time = LaunchConfiguration('use_sim_time')
    
    # Semantic SLAM Launch
    semantic_slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_semantic_slam'),
                'launch',
                'semantic_slam.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'confidence_threshold': '0.5',
            'yolo_model': 'yolov8n.pt'
        }.items(),
        condition=IfCondition(use_semantic_slam)
    )
    
    # Enhanced Visualization Launch
    enhanced_viz_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_semantic_slam'),
                'launch',
                'enhanced_visualization.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'visualization_rate': '10.0',
            'use_rviz': 'true'
        }.items(),
        condition=IfCondition(use_enhanced_viz)
    )
    
    # Advanced Safety Launch
    advanced_safety_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_semantic_slam'),
                'launch',
                'advanced_safety.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'safety_check_rate': '10.0',
            'prediction_horizon': '3.0',
            'critical_distance': '0.3'
        }.items(),
        condition=IfCondition(use_advanced_safety)
    )
    
    # Semantic Interface Launch
    semantic_interface_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_semantic_slam'),
                'launch',
                'semantic_interface.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'enable_voice_commands': 'false',
            'command_timeout': '30.0'
        }.items(),
        condition=IfCondition(use_semantic_interface)
    )
    
    # Performance Dashboard Launch
    performance_dashboard_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_semantic_slam'),
                'launch',
                'performance_dashboard.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'update_rate': '1.0',
            'cpu_warning_threshold': '80.0',
            'cpu_critical_threshold': '90.0',
            'memory_warning_threshold': '80.0',
            'memory_critical_threshold': '90.0'
        }.items(),
        condition=IfCondition(use_performance_dashboard)
    )
    
    return LaunchDescription([
        # Launch arguments
        use_semantic_slam_arg,
        use_enhanced_viz_arg,
        use_advanced_safety_arg,
        use_semantic_interface_arg,
        use_performance_dashboard_arg,
        use_sim_time_arg,
        
        # Modular feature launches
        semantic_slam_launch,
        enhanced_viz_launch,
        advanced_safety_launch,
        semantic_interface_launch,
        performance_dashboard_launch,
    ])