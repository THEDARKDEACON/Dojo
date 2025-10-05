#!/usr/bin/env python3
"""
Primary Simulation Launch File for Dojo Robot
Launches complete robot simulation with Gazebo, controllers, and RViz
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Launch arguments
    world = LaunchConfiguration('world', default='empty.world')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    gui = LaunchConfiguration('gui', default='true')
    rviz = LaunchConfiguration('rviz', default='true')
    spawn_x = LaunchConfiguration('spawn_x', default='0.0')
    spawn_y = LaunchConfiguration('spawn_y', default='0.0')
    spawn_z = LaunchConfiguration('spawn_z', default='0.1')
    spawn_yaw = LaunchConfiguration('spawn_yaw', default='0.0')
    
    # Include the basic Gazebo launch file
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_gazebo'),
                'launch',
                'gazebo.launch.py'
            ])
        ]),
        launch_arguments={
            'world': world,
            'use_sim_time': use_sim_time,
            'gui': gui,
            'rviz': rviz,
            'spawn_x': spawn_x,
            'spawn_y': spawn_y,
            'spawn_z': spawn_z,
            'spawn_yaw': spawn_yaw,
            'use_config_manager': 'true'
        }.items()
    )
    
    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument('world', default_value='empty.world',
                            description='Gazebo world file name'),
        DeclareLaunchArgument('use_sim_time', default_value='true',
                            description='Use simulation (Gazebo) clock if true'),
        DeclareLaunchArgument('gui', default_value='true',
                            description='Start Gazebo GUI'),
        DeclareLaunchArgument('rviz', default_value='true',
                            description='Start RViz visualization'),
        DeclareLaunchArgument('spawn_x', default_value='0.0',
                            description='Robot spawn X position'),
        DeclareLaunchArgument('spawn_y', default_value='0.0',
                            description='Robot spawn Y position'),
        DeclareLaunchArgument('spawn_z', default_value='0.1',
                            description='Robot spawn Z position'),
        DeclareLaunchArgument('spawn_yaw', default_value='0.0',
                            description='Robot spawn yaw angle'),
        
        # Launch Gazebo simulation
        gazebo_launch,
    ])
