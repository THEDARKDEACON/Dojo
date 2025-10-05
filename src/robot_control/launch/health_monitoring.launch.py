#!/usr/bin/env python3
"""
Launch file for comprehensive health monitoring system

This launch file starts all health monitoring components:
- Enhanced Hardware Manager
- Graceful Degradation System  
- Comprehensive Diagnostic System
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition


def generate_launch_description():
    # Declare launch arguments
    enable_hardware_manager_arg = DeclareLaunchArgument(
        'enable_hardware_manager',
        default_value='true',
        description='Enable enhanced hardware manager'
    )
    
    enable_degradation_system_arg = DeclareLaunchArgument(
        'enable_degradation_system',
        default_value='true',
        description='Enable graceful degradation system'
    )
    
    enable_diagnostic_system_arg = DeclareLaunchArgument(
        'enable_diagnostic_system',
        default_value='true',
        description='Enable comprehensive diagnostic system'
    )
    
    health_check_interval_arg = DeclareLaunchArgument(
        'health_check_interval',
        default_value='1.0',
        description='Health check interval in seconds'
    )
    
    diagnostic_rate_arg = DeclareLaunchArgument(
        'diagnostic_rate',
        default_value='2.0',
        description='Diagnostic publishing rate in Hz'
    )
    
    # Enhanced Hardware Manager
    hardware_manager_node = Node(
        package='robot_control',
        executable='hardware_manager',
        name='enhanced_hardware_manager',
        output='screen',
        parameters=[{
            'health_check_interval': LaunchConfiguration('health_check_interval'),
            'max_recovery_attempts': 3,
            'recovery_cooldown': 30.0,
            'enable_auto_recovery': True,
            'enable_graceful_degradation': True
        }],
        condition=IfCondition(LaunchConfiguration('enable_hardware_manager'))
    )
    
    # Graceful Degradation System
    degradation_system_node = Node(
        package='robot_control',
        executable='graceful_degradation',
        name='graceful_degradation_system',
        output='screen',
        parameters=[{
            'enable_degradation': True,
            'max_linear_velocity': 0.5,
            'max_angular_velocity': 1.0,
            'emergency_stop_on_critical': True,
            'auto_recovery_enabled': True
        }],
        condition=IfCondition(LaunchConfiguration('enable_degradation_system'))
    )
    
    # Comprehensive Diagnostic System
    diagnostic_system_node = Node(
        package='robot_control',
        executable='diagnostic_system',
        name='comprehensive_diagnostic_system',
        output='screen',
        parameters=[{
            'diagnostic_rate': LaunchConfiguration('diagnostic_rate'),
            'metric_history_size': 1000,
            'enable_system_monitoring': True,
            'enable_performance_tracking': True,
            'alert_cooldown_period': 30.0
        }],
        condition=IfCondition(LaunchConfiguration('enable_diagnostic_system'))
    )
    
    # Hardware Discovery Service (dependency)
    hardware_discovery_node = Node(
        package='robot_control',
        executable='hardware_discovery',
        name='hardware_discovery',
        output='screen',
        parameters=[{
            'scan_interval': 5.0,
            'arduino_vendor_ids': ['2341', '1a86', '0403'],
            'lidar_vendor_ids': ['10c4', '0483'],
            'enable_monitoring': True
        }]
    )
    
    # Device Manager (dependency)
    device_manager_node = Node(
        package='robot_control',
        executable='device_manager',
        name='device_manager',
        output='screen'
    )
    
    return LaunchDescription([
        # Launch arguments
        enable_hardware_manager_arg,
        enable_degradation_system_arg,
        enable_diagnostic_system_arg,
        health_check_interval_arg,
        diagnostic_rate_arg,
        
        # Core dependency nodes
        hardware_discovery_node,
        device_manager_node,
        
        # Health monitoring nodes
        hardware_manager_node,
        degradation_system_node,
        diagnostic_system_node,
    ])