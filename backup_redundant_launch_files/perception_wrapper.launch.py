#!/usr/bin/env python3
"""
Perception Wrapper Launch File
Provides graceful degradation for robot_perception package
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
import os

def check_perception_availability(context, *args, **kwargs):
    """Check if robot_perception package is available and properly installed"""
    try:
        # Try to find the package
        package_share = FindPackageShare('robot_perception').perform(context)
        
        # Check if launch file exists
        launch_file = os.path.join(package_share, 'launch', 'perception.launch.py')
        if not os.path.exists(launch_file):
            return [LogInfo(msg="robot_perception launch file not found. Skipping perception nodes.")]
        
        # Check if executables exist
        lib_dir = os.path.join(package_share, '..', '..', 'lib', 'robot_perception')
        camera_processor = os.path.join(lib_dir, 'camera_processor')
        object_detector = os.path.join(lib_dir, 'object_detector')
        
        if not (os.path.exists(camera_processor) and os.path.exists(object_detector)):
            return [LogInfo(msg="robot_perception executables not found. Please rebuild the package. Skipping perception nodes.")]
        
        # If everything checks out, launch perception
        use_sim_time = LaunchConfiguration('use_sim_time')
        
        perception_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('robot_perception'),
                    'launch',
                    'perception.launch.py'
                ])
            ]),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'enable_vision': 'true',
                'enable_detector': 'true',
                'camera_topic': 'image_raw',
                'camera_info_topic': 'camera_info'
            }.items()
        )
        
        return [
            LogInfo(msg="robot_perception package found and verified. Starting perception nodes..."),
            perception_launch
        ]
        
    except Exception as e:
        return [LogInfo(msg=f"robot_perception package not available: {str(e)}. Simulation will continue without perception.")]

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'
        ),
        
        OpaqueFunction(function=check_perception_availability)
    ])