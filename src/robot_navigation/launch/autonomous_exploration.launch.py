#!/usr/bin/env python3
"""
Autonomous Exploration Launch File

Launches the autonomous exploration system with SLAM and navigation.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    exploration_radius = LaunchConfiguration('exploration_radius', default='10.0')
    min_frontier_size = LaunchConfiguration('min_frontier_size', default='15')
    exploration_interval = LaunchConfiguration('exploration_interval')
    robot_radius = LaunchConfiguration('robot_radius')
    gaussian_splat_mode = LaunchConfiguration('gaussian_splat_mode')
    
    # Autonomous Explorer Node
    autonomous_explorer_node = Node(
        package='robot_navigation',
        executable='autonomous_explorer',
        name='autonomous_explorer',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'exploration_radius': exploration_radius},
            {'min_frontier_size': min_frontier_size},
            {'exploration_interval': exploration_interval},
            {'robot_radius': robot_radius},
            {'goal_timeout': 45.0},
            {'map_frame': 'map'},
            {'base_frame': 'base_link'},
            {'gaussian_splat_mode': gaussian_splat_mode}
        ],
        arguments=['--ros-args', '--log-level', 'debug'],
        respawn=True
    )
    
    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'
        ),
        DeclareLaunchArgument(
            'exploration_radius',
            default_value='10.0',
            description='Maximum distance to explore frontiers'
        ),
        DeclareLaunchArgument(
            'min_frontier_size',
            default_value='5',
            description='Minimum number of points to form a frontier cluster'
        ),
        DeclareLaunchArgument(
            'exploration_interval',
            default_value='0.5',
            description='Time interval between exploration loops (seconds)'
        ),
        DeclareLaunchArgument(
            'robot_radius',
            default_value='0.22',
            description='Robot radius for collision checking'
        ),
        DeclareLaunchArgument(
            'gaussian_splat_mode',
            default_value='false',
            description='Enable optimization for Gaussian Splatting (360 spins)'
        ),
        
        # Launch nodes
        autonomous_explorer_node,
    ])