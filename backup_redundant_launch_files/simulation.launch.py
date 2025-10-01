#!/usr/bin/env python3
"""
Complete Dojo Robot Simulation Launch
Includes Gazebo + Control System + Visualization
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.actions import GroupAction
from launch_ros.parameters_type import SomeParameters

def generate_launch_description():
    # Launch arguments
    world_name = LaunchConfiguration('world', default='empty.world')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    gui = LaunchConfiguration('gui', default='true')
    rviz = LaunchConfiguration('rviz', default='true')
    use_control = LaunchConfiguration('use_control', default='true')
    use_teleop = LaunchConfiguration('use_teleop', default='true')
    use_perception = LaunchConfiguration('use_perception', default='true')
    
    # Gazebo simulation
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
    
    # Control system (simulation mode)
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
            'use_legacy_nodes': 'false',  # Use new control manager
            'use_control_manager': 'true'
        }.items(),
        condition=IfCondition(use_control)
    )
    
    # Teleop keyboard control
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
    
    # RViz with simulation config
    rviz_config_file = PathJoinSubstitution([
        FindPackageShare('robot_gazebo'),
        'rviz',
        'simulation.rviz'
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
    
    # Perception stack (camera + object detection)
    perception_group = GroupAction([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('robot_perception'),
                    'launch',
                    'perception.launch.py'
                ])
            ]),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'enable_vision': 'true',
                'enable_detector': 'true',
                'camera_topic': 'image_raw',
                'camera_info_topic': 'camera_info'
            }.items()
        )
    ], condition=IfCondition(use_perception))
    
    # Robot diagnostics
    diagnostics_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='diagnostics_aggregator',
        parameters=[
            {'use_sim_time': use_sim_time},
            PathJoinSubstitution([
                FindPackageShare('robot_gazebo'),
                'config',
                'diagnostics.yaml'
            ])
        ],
        condition=IfCondition(LaunchConfiguration('diagnostics', default='false'))
    )
    
    # Group simulation components
    simulation_group = GroupAction([
        gazebo_launch,
        control_launch,
        teleop_node,
        rviz_node,
        diagnostics_node,
        perception_group
    ])
    
    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument('world', default_value='empty.world',
                            description='Gazebo world file'),
        DeclareLaunchArgument('gui', default_value='true',
                            description='Start Gazebo GUI'),
        DeclareLaunchArgument('rviz', default_value='true',
                            description='Start RViz'),
        DeclareLaunchArgument('use_sim_time', default_value='true',
                            description='Use simulation clock'),
        DeclareLaunchArgument('use_control', default_value='true',
                            description='Start control system'),
        DeclareLaunchArgument('use_teleop', default_value='true',
                            description='Start keyboard teleop'),
        DeclareLaunchArgument('diagnostics', default_value='false',
                            description='Start diagnostics'),
        DeclareLaunchArgument(
    'use_perception',
    default_value='true',
    description='Enable perception stack (camera + object detection)'
),
        
        # Launch simulation
        simulation_group
    ])