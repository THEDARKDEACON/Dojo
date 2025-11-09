#!/usr/bin/env python3
"""
Launch file for Autonomous Movement Controller

This launch file starts the autonomous movement controller that provides
map-independent navigation capabilities.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    # Declare launch arguments
    default_linear_speed_arg = DeclareLaunchArgument(
        'default_linear_speed',
        default_value='0.3',
        description='Default linear velocity for autonomous movement'
    )
    
    default_angular_speed_arg = DeclareLaunchArgument(
        'default_angular_speed',
        default_value='0.5',
        description='Default angular velocity for autonomous movement'
    )
    
    obstacle_threshold_arg = DeclareLaunchArgument(
        'obstacle_threshold',
        default_value='0.8',
        description='Distance threshold for obstacle detection (meters)'
    )
    
    safety_threshold_arg = DeclareLaunchArgument(
        'safety_threshold',
        default_value='0.5',
        description='Distance threshold for emergency stop (meters)'
    )
    
    spiral_increment_arg = DeclareLaunchArgument(
        'spiral_increment',
        default_value='0.1',
        description='Increment for spiral pattern expansion'
    )
    
    grid_cell_size_arg = DeclareLaunchArgument(
        'grid_cell_size',
        default_value='2.0',
        description='Size of grid cells for grid pattern (meters)'
    )
    
    wall_follow_distance_arg = DeclareLaunchArgument(
        'wall_follow_distance',
        default_value='0.6',
        description='Desired distance from wall for wall-following (meters)'
    )
    
    movement_timeout_arg = DeclareLaunchArgument(
        'movement_timeout',
        default_value='30.0',
        description='Timeout for movement patterns (seconds)'
    )
    
    base_frame_arg = DeclareLaunchArgument(
        'base_frame',
        default_value='base_link',
        description='Base frame of the robot'
    )
    
    map_frame_arg = DeclareLaunchArgument(
        'map_frame',
        default_value='map',
        description='Map frame for navigation'
    )
    
    # Autonomous Movement Controller Node
    autonomous_movement_controller_node = Node(
        package='robot_navigation',
        executable='autonomous_movement_controller',
        name='autonomous_movement_controller',
        output='screen',
        parameters=[{
            'default_linear_speed': LaunchConfiguration('default_linear_speed'),
            'default_angular_speed': LaunchConfiguration('default_angular_speed'),
            'obstacle_threshold': LaunchConfiguration('obstacle_threshold'),
            'safety_threshold': LaunchConfiguration('safety_threshold'),
            'spiral_increment': LaunchConfiguration('spiral_increment'),
            'grid_cell_size': LaunchConfiguration('grid_cell_size'),
            'wall_follow_distance': LaunchConfiguration('wall_follow_distance'),
            'movement_timeout': LaunchConfiguration('movement_timeout'),
            'base_frame': LaunchConfiguration('base_frame'),
            'map_frame': LaunchConfiguration('map_frame'),
        }],
        remappings=[
            ('/scan', '/scan'),
            ('/map', '/map'),
            ('/cmd_vel_autonomous', '/cmd_vel_autonomous'),
        ]
    )
    
    return LaunchDescription([
        # Launch arguments
        default_linear_speed_arg,
        default_angular_speed_arg,
        obstacle_threshold_arg,
        safety_threshold_arg,
        spiral_increment_arg,
        grid_cell_size_arg,
        wall_follow_distance_arg,
        movement_timeout_arg,
        base_frame_arg,
        map_frame_arg,
        
        # Log info
        LogInfo(msg="Starting Autonomous Movement Controller..."),
        
        # Nodes
        autonomous_movement_controller_node,
        
        LogInfo(msg="Autonomous Movement Controller launched successfully!"),
    ])