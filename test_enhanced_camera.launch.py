#!/usr/bin/env python3
"""
Launch file to test the enhanced camera driver with dual-topic support.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for camera driver testing."""
    
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    camera_id = LaunchConfiguration('camera_id', default='0')
    
    # Enhanced camera driver node
    camera_driver = Node(
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
                'frame_id': 'camera_link',
                'camera_name': 'camera',
                'publish_camera_info': True,
                'adaptive_quality': True,
                'auto_discover': False,  # Use fallback for testing
                'fallback_device': '/dev/video0'
            }
        ]
    )
    
    # Test node to verify dual-topic functionality
    camera_tester = Node(
        package='robot_control',
        executable='test_enhanced_camera_driver.py',
        name='camera_driver_tester',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time}
        ]
    )
    
    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation time'
        ),
        DeclareLaunchArgument(
            'camera_id',
            default_value='0',
            description='Camera device ID'
        ),
        
        # Nodes
        camera_driver,
        camera_tester,
    ])