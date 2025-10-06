#!/usr/bin/env python3
"""
Vision Enhanced System Launch File

Comprehensive launch configuration that starts all enhanced components together
including camera system, object detection, SLAM, map visualization, and performance monitoring.
Implements proper node dependencies and startup sequencing.

Requirements: 2.1, 3.1, 4.1, 5.1
"""

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, 
    IncludeLaunchDescription, 
    Node, 
    TimerAction,
    GroupAction,
    ExecuteProcess
)
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    """Generate comprehensive launch description for vision enhanced system."""
    
    # Get package directories
    pkg_robot_bringup = get_package_share_directory('robot_bringup')
    pkg_robot_navigation = get_package_share_directory('robot_navigation')
    pkg_robot_gazebo = get_package_share_directory('robot_gazebo')
    pkg_robot_perception = get_package_share_directory('robot_perception')
    pkg_robot_control = get_package_share_directory('robot_control')
    
    # Default configuration paths
    default_rviz_config = os.path.join(pkg_robot_gazebo, 'rviz', 'simulation_with_sensors.rviz')
    default_slam_config = os.path.join(pkg_robot_gazebo, 'config', 'slam_config.yaml')
    
    # Launch arguments with defaults
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    use_camera = LaunchConfiguration('use_camera', default='true')
    use_detection = LaunchConfiguration('use_detection', default='true')
    use_slam = LaunchConfiguration('use_slam', default='true')
    use_rviz = LaunchConfiguration('use_rviz', default='true')
    use_performance_monitoring = LaunchConfiguration('use_performance_monitoring', default='true')
    
    # Configuration parameters
    rviz_config = LaunchConfiguration('rviz_config', default=default_rviz_config)
    slam_params_file = LaunchConfiguration('slam_params_file', default=default_slam_config)
    camera_id = LaunchConfiguration('camera_id', default='0')
    
    # Detection model parameters
    confidence_threshold = LaunchConfiguration('confidence_threshold', default='0.5')
    target_fps = LaunchConfiguration('target_fps', default='10.0')
    cpu_threshold = LaunchConfiguration('cpu_threshold', default='80.0')
    memory_threshold = LaunchConfiguration('memory_threshold', default='500.0')
    
    # Declare all launch arguments
    launch_args = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'
        ),
        DeclareLaunchArgument(
            'use_camera',
            default_value='true',
            description='Whether to start camera system'
        ),
        DeclareLaunchArgument(
            'use_detection',
            default_value='true',
            description='Whether to start object detection pipeline'
        ),
        DeclareLaunchArgument(
            'use_slam',
            default_value='true',
            description='Whether to start SLAM for mapping'
        ),
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Whether to start RViz visualization'
        ),
        DeclareLaunchArgument(
            'use_performance_monitoring',
            default_value='true',
            description='Whether to enable performance monitoring'
        ),
        DeclareLaunchArgument(
            'rviz_config',
            default_value=default_rviz_config,
            description='Full path to the RViz config file'
        ),
        DeclareLaunchArgument(
            'slam_params_file',
            default_value=default_slam_config,
            description='Full path to SLAM parameters file'
        ),
        DeclareLaunchArgument(
            'camera_id',
            default_value='0',
            description='Camera device ID'
        ),
        DeclareLaunchArgument(
            'confidence_threshold',
            default_value='0.5',
            description='Object detection confidence threshold'
        ),
        DeclareLaunchArgument(
            'target_fps',
            default_value='10.0',
            description='Target FPS for detection pipeline'
        ),
        DeclareLaunchArgument(
            'cpu_threshold',
            default_value='80.0',
            description='CPU usage threshold for performance alerts'
        ),
        DeclareLaunchArgument(
            'memory_threshold',
            default_value='500.0',
            description='Memory usage threshold in MB'
        ),
    ]
    
    # Camera system group - starts first
    camera_group = GroupAction([
        Node(
            package='robot_control',
            executable='camera_driver',
            name='enhanced_camera_driver',
            output='screen',
            parameters=[
                {
                    'use_sim_time': use_sim_time,
                    'camera_id': camera_id,
                    'width': 640,
                    'height': 480,
                    'fps': 30.0,
                    'frame_id': 'camera_optical_frame',
                    'camera_name': 'camera',
                    'publish_camera_info': True,
                    'adaptive_quality': True,
                    'auto_discover': True,
                    'fallback_device': '/dev/video0'
                }
            ],
            condition=IfCondition(use_camera)
        )
    ])
    
    # Object detection pipeline - starts after camera
    detection_group = GroupAction([
        Node(
            package='robot_perception',
            executable='vision_detection_node',
            name='vision_detection_node',
            output='screen',
            parameters=[
                {
                    'use_sim_time': use_sim_time,
                    'confidence_threshold': confidence_threshold,
                    'input_topic': '/camera/image_raw',
                    'detection_image_topic': '/camera/detection_image',
                    'detections_topic': '/detections',
                    'camera_frame': 'camera_optical_frame',
                    'debug_mode': False,
                    'target_fps': target_fps,
                    'cpu_threshold': cpu_threshold,
                    'memory_threshold_mb': memory_threshold,
                    'enable_performance_monitoring': use_performance_monitoring
                }
            ],
            condition=IfCondition(use_detection)
        )
    ])
    
    # SLAM system group
    slam_group = GroupAction([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_robot_navigation, 'launch', 'slam.launch.py')
            ),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'slam_params_file': slam_params_file,
                'use_lifecycle_manager': 'true',
                'autostart': 'true',
            }.items(),
            condition=IfCondition(use_slam)
        )
    ])
    
    # Map visualization and diagnostics group
    map_diagnostics_group = GroupAction([
        Node(
            package='robot_navigation',
            executable='map_diagnostic_node.py',
            name='map_diagnostic_node',
            output='screen',
            parameters=[
                {
                    'use_sim_time': use_sim_time,
                    'map_topic': '/map',
                    'diagnostic_period': 2.0
                }
            ],
            condition=IfCondition(use_slam)
        ),
        Node(
            package='robot_navigation',
            executable='map_status_monitor.py',
            name='map_status_monitor',
            output='screen',
            parameters=[
                {
                    'use_sim_time': use_sim_time,
                    'map_topic': '/map',
                    'fallback_marker_topic': '/map_fallback_markers',
                    'robot_pose_topic': '/robot_pose',
                    'check_interval': 1.0,
                    'map_timeout': 5.0
                }
            ],
            condition=IfCondition(use_slam)
        ),
        Node(
            package='robot_navigation',
            executable='frame_validator.py',
            name='frame_validator',
            output='screen',
            parameters=[
                {
                    'use_sim_time': use_sim_time,
                    'diagnostic_period': 5.0,
                    'frame_timeout': 1.0
                }
            ]
        )
    ])
    
    # Performance monitoring group
    performance_group = GroupAction([
        Node(
            package='robot_perception',
            executable='performance_monitor',
            name='system_performance_monitor',
            output='screen',
            parameters=[
                {
                    'use_sim_time': use_sim_time,
                    'target_fps': target_fps,
                    'cpu_threshold': cpu_threshold,
                    'memory_threshold_mb': memory_threshold,
                    'monitoring_period': 1.0,
                    'alert_cooldown': 10.0
                }
            ],
            condition=IfCondition(use_performance_monitoring)
        ),
        Node(
            package='robot_perception',
            executable='resource_manager',
            name='system_resource_manager',
            output='screen',
            parameters=[
                {
                    'use_sim_time': use_sim_time,
                    'cpu_limit': cpu_threshold,
                    'memory_limit_mb': memory_threshold,
                    'throttle_threshold': 85.0,
                    'recovery_threshold': 70.0
                }
            ],
            condition=IfCondition(use_performance_monitoring)
        )
    ])
    
    # System validation and health monitoring
    system_validator = Node(
        package='robot_bringup',
        executable='system_validator',
        name='system_validator',
        output='screen',
        parameters=[
            {
                'use_sim_time': use_sim_time,
                'startup_timeout': 30.0,
                'health_check_period': 2.0,
                'topic_timeout': 10.0,
                'service_timeout': 5.0,
                'enable_camera_check': use_camera,
                'enable_detection_check': use_detection,
                'enable_slam_check': use_slam,
                'enable_rviz_check': False,
                'shutdown_timeout': 10.0,
            }
        ]
    )
    
    # RViz visualization - starts last with delay
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
        condition=IfCondition(use_rviz)
    )
    
    # Timed actions for proper startup sequencing
    delayed_detection = TimerAction(
        period=2.0,  # Wait for camera to be ready
        actions=[detection_group]
    )
    
    delayed_map_diagnostics = TimerAction(
        period=3.0,  # Wait for SLAM to initialize
        actions=[map_diagnostics_group]
    )
    
    delayed_rviz = TimerAction(
        period=5.0,  # Wait for all systems to be ready
        actions=[rviz_node]
    )
    
    delayed_performance = TimerAction(
        period=1.0,  # Start monitoring early but after camera
        actions=[performance_group]
    )
    
    # Build launch description with proper sequencing
    return LaunchDescription([
        # Launch arguments
        *launch_args,
        
        # Start system validator first for monitoring
        system_validator,
        
        # Start camera system first
        camera_group,
        
        # Start SLAM system in parallel with camera
        slam_group,
        
        # Start performance monitoring after camera
        delayed_performance,
        
        # Start detection pipeline after camera is ready
        delayed_detection,
        
        # Start map diagnostics after SLAM initializes
        delayed_map_diagnostics,
        
        # Start RViz last when all systems are ready
        delayed_rviz,
    ])