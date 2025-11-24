#!/usr/bin/env python3
"""
Simple Autonomous Movement Launch (NO NAV2)
Uses basic movement controller to auto-explore without Nav2 lifecycle issues
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, SetParameter
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import IncludeLaunchDescription

def generate_launch_description():
    """Launch autonomous movement without Nav2"""
    
    # Arguments
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation time'
    )
    
    use_sim_time = LaunchConfiguration('use_sim_time')
    
    # Simple autonomous movement controller (no Nav2 dependency)
    autonomous_movement = Node(
        package='robot_navigation',
        executable='autonomous_movement_controller',  # Actual executable name
        name='autonomous_movement_controller',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'linear_speed': 0.15,  # m/s - conservative
            'angular_speed': 0.4,  # rad/s
            'min_obstacle_distance': 0.8,  # m - safety margin
            'wander_mode': True,  # Random exploration
        }]
    )
    
    return LaunchDescription([
        use_sim_time_arg,
        SetParameter(name='use_sim_time', value=use_sim_time),
        
        LogInfo(msg="🤖 Starting autonomous movement (no Nav2)"),
        
        # Start autonomous movement
        TimerAction(
            period=2.0,
            actions=[autonomous_movement]
        ),
    ])
