#!/usr/bin/env python3
"""
Semantic SLAM Launch File
Launches YOLO-based object detection integrated with SLAM mapping
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # Launch arguments
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation time'
    )
    
    confidence_threshold_arg = DeclareLaunchArgument(
        'confidence_threshold',
        default_value='0.5',
        description='YOLO detection confidence threshold'
    )
    
    yolo_model_arg = DeclareLaunchArgument(
        'yolo_model',
        default_value='yolov8n.pt',
        description='YOLO model to use (yolov8n.pt, yolov8s.pt, etc.)'
    )
    
    # Launch configurations
    use_sim_time = LaunchConfiguration('use_sim_time')
    confidence_threshold = LaunchConfiguration('confidence_threshold')
    yolo_model = LaunchConfiguration('yolo_model')
    
    # Semantic SLAM Node
    semantic_slam_node = Node(
        package='robot_semantic_slam',
        executable='semantic_slam_node',
        name='semantic_slam_node',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'yolo_model': yolo_model,
            'confidence_threshold': confidence_threshold,
            'detection_rate': 10.0,
            'semantic_map_size': 1000,
        }]
    )
    
    return LaunchDescription([
        use_sim_time_arg,
        confidence_threshold_arg,
        yolo_model_arg,
        semantic_slam_node,
    ])