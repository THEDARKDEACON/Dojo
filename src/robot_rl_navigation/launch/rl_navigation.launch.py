#!/usr/bin/env python3
"""
Launch file for RL-based navigation

This launch file starts the RL navigator node with the trained policy.
It can optionally start Nav2 as a fallback system.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    # Declare launch arguments
    use_nav2_fallback = LaunchConfiguration('use_nav2_fallback', default='true')
    policy_path = LaunchConfiguration('policy_path', default='models/ppo_navigation_policy.zip')
    algorithm = LaunchConfiguration('algorithm', default='ppo')
    confidence_threshold = LaunchConfiguration('confidence_threshold', default='0.7')
    
    # Get package directories
    rl_nav_dir = FindPackageShare('robot_rl_navigation')
    
    # RL Navigator parameters
    rl_navigator_params = PathJoinSubstitution([
        rl_nav_dir,
        'config',
        'rl_navigator_params.yaml'
    ])
    
    # RL Navigator Node
    rl_navigator_node = Node(
        package='robot_rl_navigation',
        executable='rl_navigator',
        name='rl_navigator',
        output='screen',
        parameters=[
            rl_navigator_params,
            {
                'policy_path': policy_path,
                'algorithm': algorithm,
                'confidence_threshold': confidence_threshold,
            }
        ],
        remappings=[
            ('/scan', '/scan'),
            ('/odom', '/odom'),
            ('/goal_pose', '/goal_pose'),
            ('/cmd_vel', '/cmd_vel_rl'),
        ]
    )
    
    # Optional: Nav2 fallback system
    # nav2_launch = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource([
    #         PathJoinSubstitution([
    #             FindPackageShare('robot_navigation'),
    #             'launch',
    #             'nav2.launch.py'
    #         ])
    #     ]),
    #     condition=IfCondition(use_nav2_fallback)
    # )
    
    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument(
            'use_nav2_fallback',
            default_value='true',
            description='Enable Nav2 as fallback when RL confidence is low'
        ),
        DeclareLaunchArgument(
            'policy_path',
            default_value='models/ppo_navigation_policy.zip',
            description='Path to trained RL policy'
        ),
        DeclareLaunchArgument(
            'algorithm',
            default_value='ppo',
            description='RL algorithm used (ppo or sac)'
        ),
        DeclareLaunchArgument(
            'confidence_threshold',
            default_value='0.7',
            description='Minimum confidence to use RL policy'
        ),
        
        # Nodes
        rl_navigator_node,
        # nav2_launch,  # Uncomment when Nav2 integration is ready
    ])
