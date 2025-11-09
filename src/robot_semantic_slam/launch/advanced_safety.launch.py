#!/usr/bin/env python3
"""
Advanced Safety System Launch File
Launches predictive collision avoidance and multi-layer safety
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
    
    safety_check_rate_arg = DeclareLaunchArgument(
        'safety_check_rate',
        default_value='10.0',
        description='Safety system check rate in Hz'
    )
    
    prediction_horizon_arg = DeclareLaunchArgument(
        'prediction_horizon',
        default_value='3.0',
        description='Collision prediction horizon in seconds'
    )
    
    critical_distance_arg = DeclareLaunchArgument(
        'critical_distance',
        default_value='0.3',
        description='Critical safety distance in meters'
    )
    
    # Launch configurations
    use_sim_time = LaunchConfiguration('use_sim_time')
    safety_check_rate = LaunchConfiguration('safety_check_rate')
    prediction_horizon = LaunchConfiguration('prediction_horizon')
    critical_distance = LaunchConfiguration('critical_distance')
    
    # Advanced Safety System Node
    advanced_safety_node = Node(
        package='robot_semantic_slam',
        executable='advanced_safety_system',
        name='advanced_safety_system',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'safety_check_rate': safety_check_rate,
            'prediction_horizon': prediction_horizon,
            'critical_distance': critical_distance,
            'warning_distance': 0.8,
            'caution_distance': 1.5,
            'enable_predictive_safety': True,
            'enable_visual_safety': True,
        }]
    )
    
    return LaunchDescription([
        use_sim_time_arg,
        safety_check_rate_arg,
        prediction_horizon_arg,
        critical_distance_arg,
        advanced_safety_node,
    ])