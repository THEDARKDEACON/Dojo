#!/usr/bin/env python3
"""
Launch file for multi-robot swarm system.

This launch file starts:
- Swarm coordinator for each robot
- Formation controller (optional)
- Collaborative mapper
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.conditions import IfCondition
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    """Generate launch description for swarm system."""
    
    # Declare launch arguments
    robot_id_arg = DeclareLaunchArgument(
        'robot_id',
        default_value='robot_0',
        description='Unique ID for this robot'
    )
    
    robot_index_arg = DeclareLaunchArgument(
        'robot_index',
        default_value='0',
        description='Index of this robot in the swarm (0-based)'
    )
    
    num_robots_arg = DeclareLaunchArgument(
        'num_robots',
        default_value='1',
        description='Total number of robots in the swarm'
    )
    
    enable_formation_arg = DeclareLaunchArgument(
        'enable_formation',
        default_value='false',
        description='Enable formation control'
    )
    
    enable_collaborative_mapping_arg = DeclareLaunchArgument(
        'enable_collaborative_mapping',
        default_value='true',
        description='Enable collaborative mapping'
    )
    
    # Get launch configurations
    robot_id = LaunchConfiguration('robot_id')
    robot_index = LaunchConfiguration('robot_index')
    num_robots = LaunchConfiguration('num_robots')
    enable_formation = LaunchConfiguration('enable_formation')
    enable_collaborative_mapping = LaunchConfiguration('enable_collaborative_mapping')
    
    # Get config file path
    config_file = PathJoinSubstitution([
        FindPackageShare('robot_swarm'),
        'config',
        'swarm_params.yaml'
    ])
    
    # Swarm Coordinator Node
    swarm_coordinator_node = Node(
        package='robot_swarm',
        executable='swarm_coordinator',
        name='swarm_coordinator',
        namespace=robot_id,
        parameters=[
            config_file,
            {
                'robot_id': robot_id,
            }
        ],
        output='screen'
    )
    
    # Formation Controller Node (optional)
    formation_controller_node = Node(
        package='robot_swarm',
        executable='formation_controller',
        name='formation_controller',
        namespace=robot_id,
        parameters=[
            config_file,
            {
                'robot_id': robot_id,
                'robot_index': robot_index,
                'num_robots': num_robots,
            }
        ],
        output='screen',
        condition=IfCondition(enable_formation)
    )
    
    # Collaborative Mapper Node (optional)
    collaborative_mapper_node = Node(
        package='robot_swarm',
        executable='collaborative_mapper',
        name='collaborative_mapper',
        namespace=robot_id,
        parameters=[
            config_file,
            {
                'robot_id': robot_id,
            }
        ],
        output='screen',
        condition=IfCondition(enable_collaborative_mapping)
    )
    
    return LaunchDescription([
        robot_id_arg,
        robot_index_arg,
        num_robots_arg,
        enable_formation_arg,
        enable_collaborative_mapping_arg,
        swarm_coordinator_node,
        formation_controller_node,
        collaborative_mapper_node,
    ])
