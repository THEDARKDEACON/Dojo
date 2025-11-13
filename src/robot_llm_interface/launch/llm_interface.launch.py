#!/usr/bin/env python3
"""
Launch file for LLM Interface system.

Launches:
- LLM Controller
- Task Planner
- Explanation Generator
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Declare launch arguments
    llm_provider_arg = DeclareLaunchArgument(
        'llm_provider',
        default_value='ollama',
        description='LLM provider: openai, anthropic, ollama, llama'
    )
    
    verbosity_arg = DeclareLaunchArgument(
        'verbosity',
        default_value='medium',
        description='Explanation verbosity: low, medium, high'
    )
    
    config_file_arg = DeclareLaunchArgument(
        'config_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('robot_llm_interface'),
            'config',
            'llm_config.yaml'
        ]),
        description='Path to LLM configuration file'
    )
    
    # Get launch configurations
    llm_provider = LaunchConfiguration('llm_provider')
    verbosity = LaunchConfiguration('verbosity')
    config_file = LaunchConfiguration('config_file')
    
    # LLM Controller Node
    llm_controller_node = Node(
        package='robot_llm_interface',
        executable='llm_controller',
        name='llm_controller',
        output='screen',
        parameters=[
            config_file,
            {'llm_provider': llm_provider}
        ],
        remappings=[
            ('/llm/command', '/llm/command'),
            ('/llm/explanation', '/llm/explanation'),
            ('/semantic_map', '/semantic_map'),
            ('/robot_pose', '/robot_pose'),
        ]
    )
    
    # Task Planner Node
    task_planner_node = Node(
        package='robot_llm_interface',
        executable='task_planner',
        name='task_planner',
        output='screen',
        parameters=[config_file]
    )
    
    # Explanation Generator Node
    explanation_generator_node = Node(
        package='robot_llm_interface',
        executable='explanation_generator',
        name='explanation_generator',
        output='screen',
        parameters=[
            config_file,
            {'verbosity': verbosity}
        ]
    )
    
    # Log info
    log_info = LogInfo(
        msg=['Launching LLM Interface with provider: ', llm_provider]
    )
    
    return LaunchDescription([
        llm_provider_arg,
        verbosity_arg,
        config_file_arg,
        log_info,
        llm_controller_node,
        task_planner_node,
        explanation_generator_node,
    ])
