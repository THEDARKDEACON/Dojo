#!/usr/bin/env python3
"""
Complete Simulation Launch with Teleop and SLAM Support
Launches Gazebo simulation with proper teleop control, camera feed, LiDAR, and SLAM mapping
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Launch arguments
    world = LaunchConfiguration('world', default='empty.world')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    gui = LaunchConfiguration('gui', default='true')
    rviz = LaunchConfiguration('rviz', default='true')
    teleop = LaunchConfiguration('teleop', default='true')
    slam = LaunchConfiguration('slam', default='true')
    
    # Include the basic Gazebo launch file
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_gazebo'),
                'launch',
                'gazebo.launch.py'
            ])
        ]),
        launch_arguments={
            'world': world,
            'use_sim_time': use_sim_time,
            'gui': gui,
            'rviz': 'false',  # We'll launch our own RViz with sensor config
            'use_config_manager': 'false'  # Disable to avoid conflicts
        }.items()
    )
    
    # Twist Mux for command velocity multiplexing
    twist_mux_node = Node(
        package='twist_mux',
        executable='twist_mux',
        parameters=[
            PathJoinSubstitution([
                FindPackageShare('robot_control'),
                'config',
                'twist_mux_config.yaml'
            ]),
            {'use_sim_time': use_sim_time}
        ],
        remappings=[
            ('/cmd_vel_out', '/cmd_vel')
        ],
        output='screen'
    )
    
    # SLAM Toolbox for mapping
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            PathJoinSubstitution([
                FindPackageShare('robot_gazebo'),
                'config',
                'slam_config.yaml'
            ]),
            {'use_sim_time': use_sim_time}
        ],
        condition=IfCondition(slam)
    )
    
    # RViz with sensor visualization
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', PathJoinSubstitution([
            FindPackageShare('robot_gazebo'),
            'rviz',
            'simulation_with_sensors.rviz'
        ])],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(rviz)
    )
    
    # Teleop keyboard
    teleop_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_keyboard',
        output='screen',
        prefix='xterm -e',
        remappings=[
            ('/cmd_vel', '/cmd_vel_teleop')
        ],
        condition=IfCondition(teleop)
    )
    
    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument('world', default_value='empty.world',
                            description='Gazebo world file name'),
        DeclareLaunchArgument('use_sim_time', default_value='true',
                            description='Use simulation (Gazebo) clock if true'),
        DeclareLaunchArgument('gui', default_value='true',
                            description='Start Gazebo GUI'),
        DeclareLaunchArgument('rviz', default_value='true',
                            description='Start RViz visualization'),
        DeclareLaunchArgument('teleop', default_value='true',
                            description='Start teleop keyboard'),
        DeclareLaunchArgument('slam', default_value='true',
                            description='Start SLAM for mapping'),
        
        # Launch simulation
        gazebo_launch,
        
        # Launch sensor processing and visualization
        slam_toolbox_node,
        rviz_node,
        
        # Launch teleop support
        twist_mux_node,
        teleop_node,
    ])