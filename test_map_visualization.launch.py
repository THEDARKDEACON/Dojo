#!/usr/bin/env python3
"""
Test Launch File for Map Visualization
Tests SLAM and RViz map display functionality
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Get package directories
    pkg_robot_bringup = get_package_share_directory('robot_bringup')
    pkg_robot_gazebo = get_package_share_directory('robot_gazebo')
    
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world = LaunchConfiguration('world', default='empty.world')
    
    # Declare launch arguments
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true')
    
    declare_world = DeclareLaunchArgument(
        'world',
        default_value='empty.world',
        description='Gazebo world file')
    
    # Launch Gazebo simulation
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_robot_gazebo, 'launch', 'gazebo.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'world': world,
            'gui': 'true',
            'rviz': 'false'  # We'll launch RViz separately
        }.items()
    )
    
    # Launch enhanced RViz with SLAM
    enhanced_rviz_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_robot_bringup, 'launch', 'enhanced_rviz.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'use_slam': 'true',
            'use_rviz': 'true'
        }.items()
    )
    
    # Delay enhanced RViz to ensure Gazebo is ready
    delayed_enhanced_rviz = TimerAction(
        period=5.0,
        actions=[enhanced_rviz_launch]
    )
    
    return LaunchDescription([
        # Launch arguments
        declare_use_sim_time,
        declare_world,
        
        # Launch Gazebo first
        gazebo_launch,
        
        # Launch enhanced RViz with SLAM after delay
        delayed_enhanced_rviz,
    ])