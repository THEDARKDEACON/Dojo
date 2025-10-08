#!/usr/bin/env python3
"""
Bypass Mode Hardware Launch File
This launch file provides Arduino Integration Bypass Mode for real hardware.
It excludes Gazebo simulation components and focuses on direct Arduino communication.

Usage Examples:
  # Basic bypass mode for hardware
  ros2 launch bypass_mode_hardware.launch.py
  
  # Bypass mode with custom Arduino port
  ros2 launch bypass_mode_hardware.launch.py arduino_port:=/dev/ttyUSB0
  
  # Bypass mode with RViz visualization
  ros2 launch bypass_mode_hardware.launch.py rviz:=true
  
  # Bypass mode with teleop control
  ros2 launch bypass_mode_hardware.launch.py teleop:=true
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    arduino_port = LaunchConfiguration('arduino_port', default='/dev/ttyACM0')
    rviz = LaunchConfiguration('rviz', default='false')
    teleop = LaunchConfiguration('teleop', default='true')
    debug = LaunchConfiguration('debug', default='false')
    
    # Get robot description
    robot_description_content = Command([
        'xacro ', 
        PathJoinSubstitution([
            FindPackageShare('robot_description'),
            'urdf',
            'robot.urdf.xacro'
        ])
    ])
    
    robot_description = {'robot_description': robot_description_content}
    
    # Bypass Mode Launch (core bypass functionality)
    bypass_mode_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_control'),
                'launch',
                'bypass_mode.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'arduino_port': arduino_port,
            'debug': debug
        }.items()
    )
    
    # Robot state publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[robot_description, {'use_sim_time': use_sim_time}],
        output='screen'
    )
    
    # RViz for visualization (optional)
    rviz_config_file = PathJoinSubstitution([
        FindPackageShare('robot_description'),
        'rviz',
        'robot_display.rviz'
    ])
    
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(rviz)
    )
    
    # Teleop keyboard (delayed start to ensure robot is ready)
    teleop_node = TimerAction(
        period=3.0,
        actions=[
            ExecuteProcess(
                cmd=['xterm', '-e', 'ros2', 'run', 'teleop_twist_keyboard', 'teleop_twist_keyboard'],
                output='screen'
            )
        ],
        condition=IfCondition(teleop)
    )
    
    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument('use_sim_time', default_value='false',
                            description='Use simulation (Gazebo) clock if true'),
        DeclareLaunchArgument('arduino_port', default_value='/dev/ttyACM0',
                            description='Arduino serial port (e.g., /dev/ttyACM0, /dev/ttyUSB0)'),
        DeclareLaunchArgument('rviz', default_value='false',
                            description='Start RViz visualization'),
        DeclareLaunchArgument('teleop', default_value='true',
                            description='Start teleop keyboard control'),
        DeclareLaunchArgument('debug', default_value='false',
                            description='Enable debug logging for bypass mode components'),
        
        # Launch components for hardware bypass mode
        bypass_mode_launch,
        robot_state_publisher,
        rviz_node,
        teleop_node,
    ])