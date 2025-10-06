#!/usr/bin/env python3
"""
Launch file for testing performance monitoring and resource management.

This launch file starts the vision detection node with performance monitoring
and resource management enabled, along with a test node that generates test images.
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    """Generate launch description for performance monitoring test."""
    
    # Declare launch arguments
    debug_mode_arg = DeclareLaunchArgument(
        'debug_mode',
        default_value='true',
        description='Enable debug mode for detailed logging'
    )
    
    target_fps_arg = DeclareLaunchArgument(
        'target_fps',
        default_value='10.0',
        description='Target frame rate for performance monitoring'
    )
    
    cpu_threshold_arg = DeclareLaunchArgument(
        'cpu_threshold',
        default_value='70.0',
        description='CPU usage threshold for alerts (percentage)'
    )
    
    memory_threshold_arg = DeclareLaunchArgument(
        'memory_threshold_mb',
        default_value='400.0',
        description='Memory usage threshold for alerts (MB)'
    )
    
    # Vision detection node with performance monitoring
    vision_detection_node = Node(
        package='robot_perception',
        executable='vision_detection_node',
        name='vision_detection_node',
        parameters=[{
            'debug_mode': LaunchConfiguration('debug_mode'),
            'target_fps': LaunchConfiguration('target_fps'),
            'cpu_threshold': LaunchConfiguration('cpu_threshold'),
            'memory_threshold_mb': LaunchConfiguration('memory_threshold_mb'),
            'enable_performance_monitoring': True,
            'enable_resource_management': True,
            'max_fps': 30.0,
            'min_fps': 2.0,
            'confidence_threshold': 0.5,
            'input_topic': '/camera/image_raw',
            'detection_image_topic': '/camera/detection_image',
            'detections_topic': '/detections',
            'camera_frame': 'camera_optical_frame'
        }],
        output='screen',
        emulate_tty=True
    )
    
    # Performance test node
    performance_test_node = Node(
        package='robot_perception',
        executable='test_performance_monitoring.py',
        name='performance_test_node',
        output='screen',
        emulate_tty=True
    )
    
    # RViz for visualization (optional)
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', '/opt/ros/humble/share/rviz_common/default.rviz'],
        output='screen',
        condition='false'  # Disabled by default, can be enabled manually
    )
    
    return LaunchDescription([
        debug_mode_arg,
        target_fps_arg,
        cpu_threshold_arg,
        memory_threshold_arg,
        
        LogInfo(msg='Starting performance monitoring test...'),
        
        vision_detection_node,
        performance_test_node,
        
        LogInfo(msg='Performance monitoring test nodes started. Monitor the logs for performance metrics.')
    ])