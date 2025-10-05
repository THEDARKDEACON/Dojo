#!/usr/bin/env python3

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.conditions import IfCondition


def generate_launch_description():
    """
    Launch file for the integrated safety system
    
    This launch file starts all safety system components:
    - Safety Supervisor: Main safety coordination and monitoring
    - Emergency Stop Handler: Emergency stop coordination across components
    - Velocity Limiter: Command filtering and velocity limiting
    - Watchdog System: Component health monitoring
    """
    
    # Declare launch arguments
    use_safety_system_arg = DeclareLaunchArgument(
        'use_safety_system',
        default_value='true',
        description='Whether to start the safety system'
    )
    
    enable_watchdog_arg = DeclareLaunchArgument(
        'enable_watchdog',
        default_value='true',
        description='Whether to enable watchdog monitoring'
    )
    
    safety_config_file_arg = DeclareLaunchArgument(
        'safety_config_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('robot_control'),
            'config',
            'safety_config.yaml'
        ]),
        description='Path to safety configuration file'
    )
    
    # Safety Supervisor Node
    safety_supervisor_node = Node(
        package='robot_control',
        executable='safety_supervisor',
        name='safety_supervisor',
        output='screen',
        parameters=[
            LaunchConfiguration('safety_config_file'),
            {
                'use_sim_time': False,
                'log_level': 'INFO'
            }
        ],
        remappings=[
            ('/cmd_vel', '/cmd_vel'),
            ('/cmd_vel_filtered', '/cmd_vel_filtered'),
            ('/scan', '/scan'),
            ('/emergency_stop', '/emergency_stop'),
            ('/safety_status', '/safety_status')
        ],
        condition=IfCondition(LaunchConfiguration('use_safety_system'))
    )
    
    # Emergency Stop Handler Node
    emergency_stop_handler_node = Node(
        package='robot_control',
        executable='emergency_stop_handler',
        name='emergency_stop_handler',
        output='screen',
        parameters=[
            LaunchConfiguration('safety_config_file'),
            {
                'use_sim_time': False,
                'log_level': 'INFO'
            }
        ],
        remappings=[
            ('/emergency_stop', '/emergency_stop'),
            ('/emergency_stop_trigger', '/emergency_stop_trigger'),
            ('/emergency_stop_ack', '/emergency_stop_ack'),
            ('/component_heartbeat', '/component_heartbeat'),
            ('/recovery_ready', '/recovery_ready'),
            ('/safety_reset', '/safety_reset')
        ],
        condition=IfCondition(LaunchConfiguration('use_safety_system'))
    )
    
    # Velocity Limiter Node
    velocity_limiter_node = Node(
        package='robot_control',
        executable='velocity_limiter',
        name='velocity_limiter',
        output='screen',
        parameters=[
            LaunchConfiguration('safety_config_file'),
            {
                'use_sim_time': False,
                'log_level': 'INFO'
            }
        ],
        remappings=[
            ('/cmd_vel', '/cmd_vel'),
            ('/cmd_vel_limited', '/cmd_vel_limited'),
            ('/scan', '/scan'),
            ('/emergency_stop', '/emergency_stop'),
            ('/safety_status', '/safety_status'),
            ('/velocity_limit_mode', '/velocity_limit_mode')
        ],
        condition=IfCondition(LaunchConfiguration('use_safety_system'))
    )
    
    # Watchdog System Node
    watchdog_system_node = Node(
        package='robot_control',
        executable='watchdog_system',
        name='watchdog_system',
        output='screen',
        parameters=[
            LaunchConfiguration('safety_config_file'),
            {
                'use_sim_time': False,
                'log_level': 'INFO'
            }
        ],
        remappings=[
            ('/component_heartbeat', '/component_heartbeat'),
            ('/watchdog_reset', '/watchdog_reset'),
            ('/emergency_stop', '/emergency_stop'),
            ('/watchdog_status', '/watchdog_status'),
            ('/component_alert', '/component_alert')
        ],
        condition=IfCondition(LaunchConfiguration('enable_watchdog'))
    )
    
    # Group all safety system nodes
    safety_system_group = GroupAction([
        safety_supervisor_node,
        emergency_stop_handler_node,
        velocity_limiter_node,
        watchdog_system_node
    ])
    
    return LaunchDescription([
        use_safety_system_arg,
        enable_watchdog_arg,
        safety_config_file_arg,
        safety_system_group
    ])