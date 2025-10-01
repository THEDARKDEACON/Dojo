#!/usr/bin/env python3
"""
Simple Dojo Robot Simulation (No External Dependencies)
Basic simulation without SLAM or robot_localization
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Launch arguments
    world_name = LaunchConfiguration('world', default='dojo_world.world')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    gui = LaunchConfiguration('gui', default='true')
    rviz = LaunchConfiguration('rviz', default='true')
    use_teleop = LaunchConfiguration('use_teleop', default='true')
    
    # === GAZEBO SIMULATION ===
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_gazebo'),
                'launch',
                'gazebo.launch.py'
            ])
        ]),
        launch_arguments={
            'world': world_name,
            'gui': gui,
            'use_sim_time': use_sim_time,
            'rviz': 'false'  # We'll launch RViz separately
        }.items()
    )
    
    # === ROBOT CONTROL SYSTEM ===
    control_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_control'),
                'launch',
                'control.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'use_legacy_nodes': 'false',
            'use_control_manager': 'true'
        }.items()
    )
    
    # === TELEOP KEYBOARD CONTROL ===
    teleop_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_keyboard',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        remappings=[
            ('cmd_vel', 'cmd_vel_manual')  # Connect to control manager
        ],
        condition=IfCondition(use_teleop),
        prefix='xterm -e'  # Run in separate terminal
    )
    
    # === RVIZ WITH BASIC CONFIG ===
    rviz_config_file = PathJoinSubstitution([
        FindPackageShare('robot_gazebo'),
        'rviz',
        'simulation.rviz'  # Use basic simulation config
    ])
    
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
        condition=IfCondition(rviz)
    )
    
    # === DELAYED RVIZ ===
    delayed_rviz = TimerAction(
        period=3.0,  # Wait 3 seconds for Gazebo to start
        actions=[rviz_node]
    )
    
    # === GROUP ALL SIMULATION COMPONENTS ===
    simulation_group = GroupAction([
        gazebo_launch,
        control_launch,
        teleop_node,
        delayed_rviz
    ])
    
    return LaunchDescription([
        # === LAUNCH ARGUMENTS ===
        DeclareLaunchArgument('world', default_value='dojo_world.world',
                            description='Gazebo world file'),
        DeclareLaunchArgument('gui', default_value='true',
                            description='Start Gazebo GUI'),
        DeclareLaunchArgument('rviz', default_value='true',
                            description='Start RViz'),
        DeclareLaunchArgument('use_sim_time', default_value='true',
                            description='Use simulation clock'),
        DeclareLaunchArgument('use_teleop', default_value='true',
                            description='Start keyboard teleop'),
        
        # === LAUNCH SIMULATION ===
        simulation_group
    ])