#!/usr/bin/env python3
"""
SLAM Launch File for Robot Navigation
Launches SLAM Toolbox for real-time mapping and localization
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, Node
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Get package directories
    pkg_robot_navigation = get_package_share_directory('robot_navigation')
    pkg_robot_gazebo = get_package_share_directory('robot_gazebo')
    
    # Default paths
    default_slam_config = os.path.join(pkg_robot_gazebo, 'config', 'slam_config.yaml')
    
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    slam_params_file = LaunchConfiguration('slam_params_file', default=default_slam_config)
    use_lifecycle_manager = LaunchConfiguration('use_lifecycle_manager', default='true')
    autostart = LaunchConfiguration('autostart', default='true')
    
    # Declare launch arguments
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true')
    
    declare_slam_params_file = DeclareLaunchArgument(
        'slam_params_file',
        default_value=default_slam_config,
        description='Full path to the SLAM parameters file')
    
    declare_use_lifecycle_manager = DeclareLaunchArgument(
        'use_lifecycle_manager',
        default_value='true',
        description='Whether to use lifecycle manager for SLAM')
    
    declare_autostart = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically start SLAM')
    
    # SLAM Toolbox node
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='sync_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            slam_params_file,
            {'use_sim_time': use_sim_time}
        ],
        remappings=[
            ('/scan', '/scan'),
            ('/map', '/map'),
            ('/map_metadata', '/map_metadata')
        ]
    )
    
    # Lifecycle manager for SLAM (optional)
    lifecycle_nodes = ['slam_toolbox']
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_slam',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'autostart': autostart},
            {'node_names': lifecycle_nodes}
        ],
        condition=IfCondition(use_lifecycle_manager)
    )
    
    return LaunchDescription([
        # Launch arguments
        declare_use_sim_time,
        declare_slam_params_file,
        declare_use_lifecycle_manager,
        declare_autostart,
        
        # Launch nodes
        slam_toolbox_node,
        lifecycle_manager,
    ])