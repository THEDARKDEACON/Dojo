#!/usr/bin/env python3
"""
Launch file for the Configuration Manager.

This launch file starts the configuration manager node which handles:
- Loading and validating the master configuration
- Detecting and resolving configuration conflicts
- Propagating parameters to all subsystems
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition, UnlessCondition


def generate_launch_description():
    """Generate the launch description for the configuration manager."""
    
    # Declare launch arguments
    config_path_arg = DeclareLaunchArgument(
        'config_path',
        default_value='',
        description='Path to the master configuration file (optional)'
    )
    
    validate_only_arg = DeclareLaunchArgument(
        'validate_only',
        default_value='false',
        description='Only validate configuration without starting the node'
    )
    
    auto_propagate_arg = DeclareLaunchArgument(
        'auto_propagate',
        default_value='true',
        description='Automatically propagate parameters to subsystem configs'
    )
    
    log_level_arg = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='Log level for the configuration manager'
    )
    
    # Configuration manager node
    configuration_manager_node = Node(
        package='robot_control',
        executable='configuration_manager',
        name='configuration_manager',
        output='screen',
        parameters=[{
            'config_path': LaunchConfiguration('config_path'),
            'auto_propagate': LaunchConfiguration('auto_propagate'),
        }],
        arguments=['--ros-args', '--log-level', LaunchConfiguration('log_level')],
        condition=UnlessCondition(LaunchConfiguration('validate_only'))
    )
    
    # Log message for validation-only mode
    validation_info = LogInfo(
        msg='Configuration validation completed. Check logs for results.',
        condition=IfCondition(LaunchConfiguration('validate_only'))
    )
    
    return LaunchDescription([
        config_path_arg,
        validate_only_arg,
        auto_propagate_arg,
        log_level_arg,
        
        LogInfo(msg='Starting Configuration Manager...'),
        configuration_manager_node,
        validation_info,
        LogInfo(msg='Configuration Manager launch completed.'),
    ])