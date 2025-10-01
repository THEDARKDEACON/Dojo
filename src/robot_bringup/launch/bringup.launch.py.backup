#!/usr/bin/env python3
"""
Improved Robot Bringup Launch File
Uses new modular hardware architecture
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Launch arguments
    use_hardware = LaunchConfiguration('use_hardware', default='true')
    use_control = LaunchConfiguration('use_control', default='true')
    use_perception = LaunchConfiguration('use_perception', default='false')
    use_navigation = LaunchConfiguration('use_navigation', default='false')
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    use_robot_description = LaunchConfiguration('use_robot_description', default='true')
    # New flags
    use_gazebo = LaunchConfiguration('use_gazebo', default='false')
    use_arduino = LaunchConfiguration('use_arduino', default='true')
    use_camera = LaunchConfiguration('use_camera', default='true')
    use_lidar = LaunchConfiguration('use_lidar', default='true')
    
    # Robot description
    robot_description_content = Command([
        'xacro ', 
        PathJoinSubstitution([
            FindPackageShare('robot_description'),
            'urdf',
            'dojo_robot.urdf.xacro'
        ]),
        ' ',
        'use_gazebo:=', use_gazebo
    ])
    
    robot_description = {'robot_description': robot_description_content}
    
    # Robot state publisher
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[robot_description, {'use_sim_time': use_sim_time}],
        output='screen',
        condition=IfCondition(use_robot_description)
    )
    
    # Hardware layer - new unified hardware interface
    hardware_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('robot_hardware'), 'launch', 'hardware.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'use_arduino': use_arduino,
            'use_camera': use_camera,
            'use_lidar': use_lidar,
        }.items(),
        condition=IfCondition(use_hardware)
    )
    
    # Control layer - high-level control coordination
    control_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('robot_control'), 'launch', 'control.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time
        }.items(),
        condition=IfCondition(use_control)
    )
    
    # Perception layer - optional computer vision and AI
    perception_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('robot_perception'), 'launch', 'perception.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'camera_topic': 'image_raw',
            'camera_info_topic': 'camera_info',
            'enable_vision': 'true',
            'enable_detector': 'true'
        }.items(),
        condition=IfCondition(use_perception)
    )
    
    # Navigation layer - optional autonomous navigation
    navigation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('robot_navigation'), 'launch', 'nav2.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time
        }.items(),
        condition=IfCondition(use_navigation)
    )
    
    # Group all launches for better organization
    robot_group = GroupAction([
        robot_state_publisher_node,
        hardware_launch,
        control_launch,
        perception_launch,
        navigation_launch
    ])
    
    # Launch argument declarations
    declares = [
        DeclareLaunchArgument('use_hardware', default_value='true', 
                            description='Launch hardware drivers'),
        DeclareLaunchArgument('use_control', default_value='true',
                            description='Launch control system'),
        DeclareLaunchArgument('use_perception', default_value='false',
                            description='Launch perception system'),
        DeclareLaunchArgument('use_navigation', default_value='false',
                            description='Launch navigation system'),
        DeclareLaunchArgument('use_sim_time', default_value='false',
                            description='Use simulation clock'),
        DeclareLaunchArgument('use_robot_description', default_value='true',
                            description='Launch robot state publisher'),
        # New flags
        DeclareLaunchArgument('use_gazebo', default_value='false',
                            description='Include Gazebo-specific elements in robot description'),
        DeclareLaunchArgument('use_arduino', default_value='true',
                            description='Enable Arduino driver'),
        DeclareLaunchArgument('use_camera', default_value='true',
                            description='Enable camera driver'),
        DeclareLaunchArgument('use_lidar', default_value='true',
                            description='Enable LiDAR driver'),
    ]

    return LaunchDescription([
        *declares,
        robot_group
    ])
