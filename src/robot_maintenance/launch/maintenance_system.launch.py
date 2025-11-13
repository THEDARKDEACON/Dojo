#!/usr/bin/env python3
"""
Launch file for Predictive Maintenance System

Launches all maintenance components:
- Health Monitor
- Anomaly Detector
- Maintenance Scheduler
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    """Generate launch description for maintenance system."""
    
    # Declare arguments
    config_file_arg = DeclareLaunchArgument(
        'config_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('robot_maintenance'),
            'config',
            'maintenance_params.yaml'
        ]),
        description='Path to maintenance configuration file'
    )
    
    enable_logging_arg = DeclareLaunchArgument(
        'enable_logging',
        default_value='true',
        description='Enable health metrics logging'
    )
    
    enable_adaptive_arg = DeclareLaunchArgument(
        'enable_adaptive',
        default_value='true',
        description='Enable adaptive parameter adjustment'
    )
    
    # Get launch configurations
    config_file = LaunchConfiguration('config_file')
    
    # Health Monitor Node
    health_monitor_node = Node(
        package='robot_maintenance',
        executable='health_monitor',
        name='health_monitor',
        output='screen',
        parameters=[config_file],
        remappings=[
            ('/joint_states', '/joint_states'),
            ('/battery_state', '/battery_state'),
            ('/motor_temperature', '/motor_temperature'),
        ]
    )
    
    # Anomaly Detector Node
    anomaly_detector_node = Node(
        package='robot_maintenance',
        executable='anomaly_detector',
        name='anomaly_detector',
        output='screen',
        parameters=[config_file]
    )
    
    # Maintenance Scheduler Node
    maintenance_scheduler_node = Node(
        package='robot_maintenance',
        executable='maintenance_scheduler',
        name='maintenance_scheduler',
        output='screen',
        parameters=[config_file]
    )
    
    # Log info
    log_info = LogInfo(
        msg='Predictive Maintenance System launched'
    )
    
    return LaunchDescription([
        config_file_arg,
        enable_logging_arg,
        enable_adaptive_arg,
        log_info,
        health_monitor_node,
        anomaly_detector_node,
        maintenance_scheduler_node
    ])
