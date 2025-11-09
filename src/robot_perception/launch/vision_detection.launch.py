#!/usr/bin/env python3
"""
Vision Detection Launch File

Launches the vision detection node for object detection in simulation or real robot.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    confidence_threshold = LaunchConfiguration('confidence_threshold', default='0.5')
    debug_mode = LaunchConfiguration('debug_mode', default='false')
    
    # Vision detection node
    vision_detection_node = Node(
        package='robot_perception',
        executable='object_detector',
        name='vision_detection_node',
        output='screen',
        parameters=[
            {
                'use_sim_time': use_sim_time,
                'confidence_threshold': confidence_threshold,
                'input_topic': '/camera/image_raw',
                'detection_image_topic': '/camera/detection_image',
                'detections_topic': '/detections',
                'camera_frame': 'camera_link',
                'debug_mode': debug_mode,
            }
        ],
        remappings=[
            # Ensure proper topic remapping if needed
        ]
    )
    
    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'
        ),
        DeclareLaunchArgument(
            'confidence_threshold',
            default_value='0.5',
            description='Minimum confidence threshold for object detection'
        ),
        DeclareLaunchArgument(
            'debug_mode',
            default_value='false',
            description='Enable debug mode with additional logging'
        ),
        
        # Launch nodes
        vision_detection_node,
    ])