#!/usr/bin/env python3
"""
Bypass Mode Launch File
This launch file provides minimal component loading for Arduino Integration Bypass Mode.
It includes only essential components and excludes problematic safety and hardware discovery systems.

Usage Examples:
  # Basic bypass mode
  ros2 launch robot_control bypass_mode.launch.py
  
  # Bypass mode with custom Arduino port
  ros2 launch robot_control bypass_mode.launch.py arduino_port:=/dev/ttyUSB0
  
  # Bypass mode with debug logging
  ros2 launch robot_control bypass_mode.launch.py debug:=true
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    arduino_port = LaunchConfiguration('arduino_port', default='/dev/ttyACM0')
    debug = LaunchConfiguration('debug', default='false')
    
    # Bypass Controller Node - Central coordinator for bypass mode
    bypass_controller_node = Node(
        package='robot_control',
        executable='bypass_controller.py',
        name='bypass_controller',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'debug': debug},
            PathJoinSubstitution([
                FindPackageShare('robot_control'),
                'config',
                'bypass_config.yaml'
            ])
        ],
        output='screen'
    )
    
    # Direct Arduino Driver Node - Simplified Arduino communication
    direct_arduino_driver_node = Node(
        package='robot_control',
        executable='direct_arduino_driver.py',
        name='direct_arduino_driver',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'arduino_port': arduino_port},
            {'debug': debug},
            PathJoinSubstitution([
                FindPackageShare('robot_control'),
                'config',
                'bypass_config.yaml'
            ])
        ],
        output='screen'
    )
    
    # Configuration Override Node - Apply robosync-compatible parameters
    configuration_override_node = Node(
        package='robot_control',
        executable='configuration_override.py',
        name='configuration_override',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'mode': 'bypass'},
            PathJoinSubstitution([
                FindPackageShare('robot_control'),
                'config',
                'bypass_config.yaml'
            ])
        ],
        output='screen'
    )
    
    # Safety Override Manager Node - Manage selective safety system disabling
    safety_override_manager_node = Node(
        package='robot_control',
        executable='safety_override_manager.py',
        name='safety_override_manager',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'bypass_mode': True},
            {'preserve_emergency_stop': True}
        ],
        output='screen'
    )
    
    # Robot State Publisher - Essential for TF tree
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[
            {'use_sim_time': use_sim_time},
            PathJoinSubstitution([
                FindPackageShare('robot_description'),
                'urdf',
                'robot.urdf'
            ])
        ],
        output='screen'
    )
    
    # Static Transform Publisher (base_footprint to base_link) - Essential for navigation
    static_tf_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='base_link_to_base_footprint',
        arguments=['0', '0', '0.1', '0', '0', '0', 'base_footprint', 'base_link'],
        output='screen'
    )
    
    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument('use_sim_time', default_value='false',
                            description='Use simulation (Gazebo) clock if true'),
        DeclareLaunchArgument('arduino_port', default_value='/dev/ttyACM0',
                            description='Arduino serial port (e.g., /dev/ttyACM0, /dev/ttyUSB0)'),
        DeclareLaunchArgument('debug', default_value='false',
                            description='Enable debug logging for bypass mode components'),
        
        # Essential bypass mode components only
        bypass_controller_node,
        direct_arduino_driver_node,
        configuration_override_node,
        safety_override_manager_node,
        robot_state_publisher,
        static_tf_node,
        
        # Note: Excluded components for bypass mode:
        # - EmergencyStopHandler (disabled by SafetyOverrideManager)
        # - SafetySupervisor (disabled by SafetyOverrideManager)
        # - HardwareManager (replaced by DirectArduinoDriver)
        # - Camera/LiDAR drivers (not required for basic motion)
        # - Complex control managers (replaced by BypassController)
    ])