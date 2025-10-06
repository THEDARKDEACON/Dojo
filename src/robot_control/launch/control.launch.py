#!/usr/bin/env python3
"""
Updated Robot Control Launch File
Uses new control manager architecture with backward compatibility
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    use_legacy_nodes = LaunchConfiguration('use_legacy_nodes', default='false')
    use_control_manager = LaunchConfiguration('use_control_manager', default='true')
    remap_cmd_vel_to_diff = LaunchConfiguration('remap_cmd_vel_to_diff', default='false')
    
    # New Control Manager Node (recommended)
    control_manager_node = Node(
        package='robot_control',
        executable='control_manager.py',
        name='control_manager',
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
        condition=IfCondition(use_control_manager)
    )

    # Control Manager with topic remap for Gazebo diff_drive_controller
    control_manager_node_sim = Node(
        package='robot_control',
        executable='control_manager.py',
        name='control_manager',
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
        remappings=[
            ('cmd_vel', '/diff_drive_controller/cmd_vel_unstamped')
        ],
        condition=IfCondition(remap_cmd_vel_to_diff)
    )
    
    # Legacy Arduino Bridge Node (for backward compatibility)
    arduino_bridge_node = Node(
        package='robot_control',
        executable='arduino_bridge',
        name='arduino_bridge',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            PathJoinSubstitution([
                FindPackageShare('robot_control'),
                'config',
                'arduino.yaml'
            ])
        ],
        condition=IfCondition(use_legacy_nodes)
    )
    
    # Legacy Command Velocity to Motors Node (for backward compatibility)
    cmd_vel_to_motors_node = Node(
        package='robot_control',
        executable='cmd_vel_to_motors',
        name='cmd_vel_to_motors',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'wheel_separation': 0.3},
            {'wheel_radius': 0.05},
            {'max_motor_speed': 255},
            {'min_motor_speed': 50}
        ],
        condition=IfCondition(use_legacy_nodes)
    )
    
    # Static Transform Publisher (base_footprint to base_link)
    static_tf_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='base_link_to_base_footprint',
        arguments=['0', '0', '0.1', '0', '0', '0', 'base_footprint', 'base_link'],
        output='screen'
    )
    
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false', 
                            description='Use simulation clock'),
        DeclareLaunchArgument('use_legacy_nodes', default_value='false',
                            description='Use legacy arduino_bridge and cmd_vel_to_motors nodes'),
        DeclareLaunchArgument('use_control_manager', default_value='true',
                            description='Use new control manager'),
        DeclareLaunchArgument('remap_cmd_vel_to_diff', default_value='false',
                            description='Remap /cmd_vel to /diff_drive_controller/cmd_vel_unstamped for Gazebo'),
        
        control_manager_node,
        control_manager_node_sim,
        arduino_bridge_node,
        cmd_vel_to_motors_node,
        static_tf_node
    ])