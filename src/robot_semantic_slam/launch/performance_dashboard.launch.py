#!/usr/bin/env python3
"""
Performance Dashboard Launch File
Launches the dedicated performance monitoring and dashboard node
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # Declare launch arguments
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation time'
    )
    
    update_rate_arg = DeclareLaunchArgument(
        'update_rate',
        default_value='1.0',
        description='Dashboard update rate in Hz'
    )
    
    cpu_warning_arg = DeclareLaunchArgument(
        'cpu_warning_threshold',
        default_value='80.0',
        description='CPU usage warning threshold (%)'
    )
    
    cpu_critical_arg = DeclareLaunchArgument(
        'cpu_critical_threshold',
        default_value='90.0',
        description='CPU usage critical threshold (%)'
    )
    
    memory_warning_arg = DeclareLaunchArgument(
        'memory_warning_threshold',
        default_value='80.0',
        description='Memory usage warning threshold (%)'
    )
    
    memory_critical_arg = DeclareLaunchArgument(
        'memory_critical_threshold',
        default_value='90.0',
        description='Memory usage critical threshold (%)'
    )
    
    # Launch configurations
    use_sim_time = LaunchConfiguration('use_sim_time')
    update_rate = LaunchConfiguration('update_rate')
    cpu_warning = LaunchConfiguration('cpu_warning_threshold')
    cpu_critical = LaunchConfiguration('cpu_critical_threshold')
    memory_warning = LaunchConfiguration('memory_warning_threshold')
    memory_critical = LaunchConfiguration('memory_critical_threshold')
    
    # Performance Dashboard Node
    performance_dashboard_node = Node(
        package='robot_semantic_slam',
        executable='performance_dashboard',
        name='performance_dashboard',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'update_rate': update_rate,
            'cpu_warning_threshold': cpu_warning,
            'cpu_critical_threshold': cpu_critical,
            'memory_warning_threshold': memory_warning,
            'memory_critical_threshold': memory_critical,
        }],
        remappings=[
            ('/semantic_map', '/semantic_map'),
            ('/plan', '/plan'),
            ('/cmd_vel', '/cmd_vel'),
            ('/safety_status', '/safety_status'),
            ('/map', '/map'),
        ]
    )
    
    return LaunchDescription([
        # Launch arguments
        use_sim_time_arg,
        update_rate_arg,
        cpu_warning_arg,
        cpu_critical_arg,
        memory_warning_arg,
        memory_critical_arg,
        
        # Nodes
        performance_dashboard_node,
    ])
