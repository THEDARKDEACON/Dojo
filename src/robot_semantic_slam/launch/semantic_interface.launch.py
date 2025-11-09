#!/usr/bin/env python3
"""
Semantic Interface Launch File
Launches natural language command processing
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
    
    enable_voice_arg = DeclareLaunchArgument(
        'enable_voice_commands',
        default_value='false',
        description='Enable voice command recognition'
    )
    
    command_timeout_arg = DeclareLaunchArgument(
        'command_timeout',
        default_value='30.0',
        description='Command timeout in seconds'
    )
    
    # Launch configurations
    use_sim_time = LaunchConfiguration('use_sim_time')
    enable_voice = LaunchConfiguration('enable_voice_commands')
    command_timeout = LaunchConfiguration('command_timeout')
    
    # Semantic Interface Node
    semantic_interface_node = Node(
        package='robot_semantic_slam',
        executable='semantic_interface',
        name='semantic_interface',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'enable_voice_commands': enable_voice,
            'enable_text_commands': True,
            'command_timeout': command_timeout,
        }]
    )
    
    return LaunchDescription([
        use_sim_time_arg,
        enable_voice_arg,
        command_timeout_arg,
        semantic_interface_node,
    ])