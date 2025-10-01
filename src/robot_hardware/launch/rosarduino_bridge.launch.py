#!/usr/bin/env python3

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
    
    debug_arg = DeclareLaunchArgument(
        'debug',
        default_value='true',
        description='Enable debug output'
    )
    
    # Get config file path
    config_file = PathJoinSubstitution([
        FindPackageShare('robot_hardware'),
        'config',
        'rosarduino_bridge.yaml'
    ])
    
    # Arduino driver node
    arduino_driver_node = Node(
        package='robot_hardware',
        executable='arduino_driver',
        name='arduino_driver',
        parameters=[
            config_file,
            {
                'port': LaunchConfiguration('port'),
                'debug': LaunchConfiguration('debug')
            }
        ],
        output='screen',
        emulate_tty=True,
        respawn=True,
        respawn_delay=2.0
    )
    
    return LaunchDescription([
        port_arg,
        debug_arg,
        arduino_driver_node
    ])