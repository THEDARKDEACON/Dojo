#!/usr/bin/env python3
"""
Basic Gazebo Launch File for Dojo Robot
Launches Gazebo with robot, controllers, and optional RViz
Use this for basic simulation setup without additional features
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, RegisterEventHandler, OpaqueFunction
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory, PackageNotFoundError
import os
import sys

def check_gazebo_availability():
    """Check if required Gazebo packages are available."""
    required_packages = ['ros_gz_sim', 'controller_manager', 'diff_drive_controller']
    missing_packages = []
    
    for package in required_packages:
        try:
            get_package_share_directory(package)
        except PackageNotFoundError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"ERROR: Missing required packages for Gazebo simulation: {missing_packages}")
        print("Please install the missing packages or run in hardware mode.")
        sys.exit(1)

def generate_launch_description():
    # Check package availability first
    check_gazebo_availability()
    
    # Launch arguments
    world_name = LaunchConfiguration('world', default='empty.world')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    gui = LaunchConfiguration('gui', default='true')
    headless = LaunchConfiguration('headless', default='false')
    debug = LaunchConfiguration('debug', default='false')
    verbose = LaunchConfiguration('verbose', default='false')
    spawn_x = LaunchConfiguration('spawn_x', default='0.0')
    spawn_y = LaunchConfiguration('spawn_y', default='0.0')
    spawn_z = LaunchConfiguration('spawn_z', default='0.1')
    spawn_yaw = LaunchConfiguration('spawn_yaw', default='0.0')
    use_config_manager = LaunchConfiguration('use_config_manager', default='true')
    
    # Configuration manager (loads mode-specific parameters)
    config_manager_node = Node(
        package='robot_control',
        executable='configuration_manager.py',
        name='configuration_manager',
        parameters=[{'operation_mode': 'simulation'}],
        output='screen',
        condition=IfCondition(use_config_manager)
    )
    
    # Get robot description
    robot_description_content = Command([
        'xacro ', 
        PathJoinSubstitution([
            FindPackageShare('robot_description'),
            'urdf',
            'robot.urdf.xacro'
        ]),
        ' use_gazebo:=true',
        ' use_sim_time:=', use_sim_time
    ])
    
    robot_description = {'robot_description': robot_description_content}
    
    # Gazebo world file
    world_file = PathJoinSubstitution([
        FindPackageShare('robot_gazebo'),
        'worlds',
        world_name
    ])
    
    # Start Gazebo Harmonic (combined server and client)
    gazebo_server = ExecuteProcess(
        cmd=['gz', 'sim', '-v', '4', '-r', world_file],
        output='screen'
    )
    
    # Robot state publisher
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[robot_description, {'use_sim_time': use_sim_time}],
        output='screen'
    )
    
    # Spawn robot in Gazebo
    spawn_robot_node = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-entity', 'dojo_robot',
            '-topic', 'robot_description',
            '-x', spawn_x,
            '-y', spawn_y,
            '-z', spawn_z,
            '-Y', spawn_yaw
        ],
        output='screen'
    )
    
    # Joint state publisher for wheel joints (since we're using Gazebo plugin)
    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen'
    )
    
    # RViz (optional)
    def get_rviz_config():
        """Get RViz config file, with fallback options."""
        possible_configs = [
            'simulation.rviz',
            'robot_simulation.rviz'
        ]
        
        gazebo_share = get_package_share_directory('robot_gazebo')
        for config_name in possible_configs:
            config_path = os.path.join(gazebo_share, 'rviz', config_name)
            if os.path.exists(config_path):
                return config_path
        
        # Fallback to robot_description if available
        try:
            desc_share = get_package_share_directory('robot_description')
            fallback_configs = ['robot_display.rviz', 'robot_simulation.rviz']
            for config_name in fallback_configs:
                config_path = os.path.join(desc_share, 'rviz', config_name)
                if os.path.exists(config_path):
                    return config_path
        except PackageNotFoundError:
            pass
        return None
    
    rviz_config_file = get_rviz_config()
    
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file] if rviz_config_file else [],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
        condition=IfCondition(LaunchConfiguration('rviz', default='false'))
    ) if rviz_config_file else None
    
    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument('world', default_value='empty.world',
                            description='Gazebo world file'),
        DeclareLaunchArgument('gui', default_value='true',
                            description='Start Gazebo GUI'),
        DeclareLaunchArgument('headless', default_value='false',
                            description='Run Gazebo headless'),
        DeclareLaunchArgument('debug', default_value='false',
                            description='Start Gazebo in debug mode'),
        DeclareLaunchArgument('verbose', default_value='false',
                            description='Start Gazebo in verbose mode'),
        DeclareLaunchArgument('use_sim_time', default_value='true',
                            description='Use simulation clock'),
        DeclareLaunchArgument('rviz', default_value='false',
                            description='Start RViz'),
        DeclareLaunchArgument('spawn_x', default_value='0.0',
                            description='Robot spawn X position'),
        DeclareLaunchArgument('spawn_y', default_value='0.0',
                            description='Robot spawn Y position'),
        DeclareLaunchArgument('spawn_z', default_value='0.1',
                            description='Robot spawn Z position'),
        DeclareLaunchArgument('spawn_yaw', default_value='0.0',
                            description='Robot spawn yaw angle'),
        DeclareLaunchArgument('use_config_manager', default_value='true',
                            description='Use configuration manager for parameter loading'),
        
        # Launch nodes
        config_manager_node,
        gazebo_server,
        robot_state_publisher_node,
        spawn_robot_node,
        joint_state_publisher_node,
    ] + ([rviz_node] if rviz_node else []))