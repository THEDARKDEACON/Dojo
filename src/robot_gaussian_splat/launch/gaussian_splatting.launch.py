#!/usr/bin/env python3
"""
Gaussian Splatting Reconstruction Launch File

Launches the Gaussian Splatting system for 3D reconstruction from
synchronized camera and LiDAR sensor data.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    """Generate launch description for Gaussian Splatting reconstruction."""
    
    # Get package directory
    gaussian_splat_dir = FindPackageShare('robot_gaussian_splat')
    
    # Declare launch arguments
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation time'
    )
    
    config_file_arg = DeclareLaunchArgument(
        'config_file',
        default_value=PathJoinSubstitution([
            gaussian_splat_dir,
            'config',
            'gaussian_splatting_params.yaml'
        ]),
        description='Path to Gaussian Splatting configuration file'
    )
    
    camera_topic_arg = DeclareLaunchArgument(
        'camera_topic',
        default_value='/camera/image_raw',
        description='Camera image topic to subscribe to'
    )
    
    camera_info_topic_arg = DeclareLaunchArgument(
        'camera_info_topic',
        default_value='/camera/camera_info',
        description='Camera info topic to subscribe to'
    )
    
    pointcloud_topic_arg = DeclareLaunchArgument(
        'pointcloud_topic',
        default_value='/scan',
        description='LiDAR point cloud topic to subscribe to'
    )
    
    launch_rviz_arg = DeclareLaunchArgument(
        'launch_rviz',
        default_value='false',
        description='Launch RViz with Gaussian Splatting visualization'
    )
    
    visualization_enabled_arg = DeclareLaunchArgument(
        'visualization_enabled',
        default_value='true',
        description='Enable real-time visualization markers'
    )
    
    # Launch configurations
    use_sim_time = LaunchConfiguration('use_sim_time')
    config_file = LaunchConfiguration('config_file')
    camera_topic = LaunchConfiguration('camera_topic')
    camera_info_topic = LaunchConfiguration('camera_info_topic')
    pointcloud_topic = LaunchConfiguration('pointcloud_topic')
    launch_rviz = LaunchConfiguration('launch_rviz')
    visualization_enabled = LaunchConfiguration('visualization_enabled')
    
    # Gaussian Splatting Node
    gaussian_splatting_node = Node(
        package='robot_gaussian_splat',
        executable='gaussian_splatting_node',
        name='gaussian_splatting_node',
        output='screen',
        parameters=[
            config_file,
            {
                'use_sim_time': use_sim_time,
                'camera_topic': camera_topic,
                'camera_info_topic': camera_info_topic,
                'pointcloud_topic': pointcloud_topic,
                'visualization_enabled': visualization_enabled,
            }
        ],
        remappings=[
            ('/camera/image_raw', camera_topic),
            ('/camera/camera_info', camera_info_topic),
            ('/scan', pointcloud_topic),
        ]
    )
    
    # RViz Node (optional)
    rviz_config_file = PathJoinSubstitution([
        gaussian_splat_dir,
        'rviz',
        'gaussian_splatting.rviz'
    ])
    
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2_gaussian_splatting',
        output='screen',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(launch_rviz)
    )
    
    return LaunchDescription([
        # Launch arguments
        use_sim_time_arg,
        config_file_arg,
        camera_topic_arg,
        camera_info_topic_arg,
        pointcloud_topic_arg,
        launch_rviz_arg,
        visualization_enabled_arg,
        
        # Nodes
        gaussian_splatting_node,
        rviz_node,
    ])
