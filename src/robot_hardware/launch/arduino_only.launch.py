#!/usr/bin/env python3
"""
Minimal Arduino-only launch file for teleop testing
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Declare launch arguments
    port_arg = DeclareLaunchArgument(
        'port',
        default_value='/dev/ttyACM0',
        description='Arduino serial port'
    )
    
    protocol_arg = DeclareLaunchArgument(
        'protocol',
        default_value='rosarduino_bridge',
        description='Arduino protocol: rosarduino_bridge or dojo_native'
    )
    
    debug_arg = DeclareLaunchArgument(
        'debug',
        default_value='true',
        description='Enable debug output'
    )
    
    # Select config file based on protocol
    config_file = PathJoinSubstitution([
        FindPackageShare('robot_hardware'),
        'config',
        [LaunchConfiguration('protocol'), '.yaml']
    ])
    
    # Arduino driver node
    arduino_driver_node = Node(
        package='robot_hardware',
        executable='arduino_driver',
        name='arduino_driver',
        parameters=[config_file, {
            'port': LaunchConfiguration('port'),
            'debug': LaunchConfiguration('debug')
        }],
        output='screen'
    )
    
    return LaunchDescription([
        port_arg,
        protocol_arg,
        debug_arg,
        arduino_driver_node
    ])