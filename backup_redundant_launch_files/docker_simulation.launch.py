#!/usr/bin/env python3
"""
Docker-Optimized Dojo Robot Simulation
Designed for headless Docker environments with optional GUI forwarding
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
    gui = LaunchConfiguration('gui', default='false')  # Default headless for Docker
    rviz = LaunchConfiguration('rviz', default='false')  # Default no RViz for Docker
    slam = LaunchConfiguration('slam', default='true')
    headless = LaunchConfiguration('headless', default='true')
    
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
            'headless': headless,
            'use_sim_time': use_sim_time,
            'rviz': 'false'
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
    
    # === SLAM TOOLBOX (for mapping) ===
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
    
    # === ROBOT LOCALIZATION ===
    robot_localization_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[
            PathJoinSubstitution([
                FindPackageShare('robot_gazebo'),
                'config',
                'ekf_config.yaml'
            ]),
            {'use_sim_time': use_sim_time}
        ],
        condition=IfCondition(LaunchConfiguration('use_ekf', default='true'))
    )
    
    # === RVIZ (only if GUI is enabled and X11 forwarding works) ===
    rviz_config_file = PathJoinSubstitution([
        FindPackageShare('robot_gazebo'),
        'rviz',
        'full_simulation.rviz'
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
    
    # === STATUS MONITORING NODE ===
    status_monitor_node = Node(
        package='robot_hardware',
        executable='hardware_manager',
        name='simulation_monitor',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )
    
    # === DELAYED NODES ===
    delayed_slam = TimerAction(
        period=5.0,  # Wait longer for Docker
        actions=[slam_toolbox_node]
    )
    
    delayed_rviz = TimerAction(
        period=3.0,
        actions=[rviz_node]
    )
    
    # === GROUP ALL COMPONENTS ===
    simulation_group = GroupAction([
        gazebo_launch,
        control_launch,
        delayed_slam,
        delayed_rviz,
        robot_localization_node,
        status_monitor_node
    ])
    
    return LaunchDescription([
        # === LAUNCH ARGUMENTS ===
        DeclareLaunchArgument('world', default_value='dojo_world.world',
                            description='Gazebo world file'),
        DeclareLaunchArgument('gui', default_value='false',
                            description='Start Gazebo GUI (requires X11 forwarding)'),
        DeclareLaunchArgument('headless', default_value='true',
                            description='Run Gazebo headless (Docker optimized)'),
        DeclareLaunchArgument('rviz', default_value='false',
                            description='Start RViz (requires X11 forwarding)'),
        DeclareLaunchArgument('use_sim_time', default_value='true',
                            description='Use simulation clock'),
        DeclareLaunchArgument('slam', default_value='true',
                            description='Start SLAM for mapping'),
        DeclareLaunchArgument('use_ekf', default_value='true',
                            description='Use Extended Kalman Filter'),
        
        # === LAUNCH SIMULATION ===
        simulation_group
    ])