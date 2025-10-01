#!/usr/bin/env python3
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    use_nav = LaunchConfiguration('use_nav')
    use_sim_time = LaunchConfiguration('use_sim_time')

    sensors_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('robot_sensors'), 'launch', 'sensors.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time
        }.items()
    )

    control_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('robot_control'), 'launch', 'control.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time
        }.items()
    )

    # Commented out until perception is properly set up
    # perception_launch = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource(
    #         os.path.join(get_package_share_directory('robot_perception'), 'launch', 'perception.launch.py')
    #     ),
    #     launch_arguments={
    #         'use_sim_time': use_sim_time
    #     }.items()
    # )

    nav_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('robot_navigation'), 'launch', 'nav2.launch.py')
        ),
        condition=None,
        launch_arguments={
            'use_sim_time': use_sim_time
        }.items()
    )

    declares = [
        DeclareLaunchArgument('use_nav', default_value='false', description='Launch Nav2 stack'),
        DeclareLaunchArgument('use_sim_time', default_value='false', description='Use simulation clock'),
    ]

    return LaunchDescription([
        *declares,
        sensors_launch,
        control_launch,
        # perception_launch,  # Commented out until properly set up
        # nav_launch  # Uncomment to include nav
    ])
