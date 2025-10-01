#!/usr/bin/env python3
"""
Complete Dojo Robot Simulation with Camera and LiDAR
Includes: Robot + Sensors + Perception + Visualization
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction, TimerAction, LogInfo, ExecuteProcess
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import os

def generate_launch_description():
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world_name = LaunchConfiguration('world', default='dojo_world.world')
    gui = LaunchConfiguration('gui', default='true')
    rviz = LaunchConfiguration('rviz', default='true')
    perception = LaunchConfiguration('perception', default='true')
    
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
    
    # === ROBOT CONTROL ===
    # Note: In simulation, robot control is handled entirely by gazebo_ros2_control
    # The gazebo.launch.py spawns the diff_drive_controller and joint_state_broadcaster
    # No additional control nodes are needed
    
    # === SLAM MAPPING ===
    slam_node = Node(
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
        ]
    )
    
    # === ROBOT PERCEPTION (WITH GRACEFUL DEGRADATION) ===
    # Use perception wrapper for robust error handling
    perception_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_gazebo'),
                'launch',
                'perception_wrapper.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time
        }.items(),
        condition=IfCondition(perception)
    )
    
    # Fallback message when perception is disabled
    perception_disabled_msg = LogInfo(
        msg="Robot perception is disabled. Simulation will run without object detection.",
        condition=UnlessCondition(perception)
    )
    
    # === TELEOP CONTROL ===
    teleop_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_keyboard',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        remappings=[
            ('cmd_vel', '/diff_drive_controller/cmd_vel_unstamped')
        ],
        prefix='xterm -e'  # Run in separate terminal
    )
    
    # === RVIZ VISUALIZATION ===
    rviz_config_file = PathJoinSubstitution([
        FindPackageShare('robot_gazebo'),
        'rviz',
        'complete_simulation.rviz'
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
    
    # === CAMERA VIEWER (separate window) ===
    camera_viewer = Node(
        package='rqt_image_view',
        executable='rqt_image_view',
        name='camera_viewer',
        arguments=['/image_raw'],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(LaunchConfiguration('camera_view', default='true'))
    )
    

    
    # === DELAYED LAUNCHES ===
    # Delayed perception launch to ensure camera topics are available
    delayed_perception = TimerAction(
        period=8.0,  # Wait for Gazebo, robot, and camera to be ready
        actions=[
            LogInfo(msg="Attempting to start robot_perception after 8 second delay..."),
            perception_launch
        ]
    )
    
    delayed_rviz = TimerAction(
        period=3.0,
        actions=[rviz_node]
    )
    
    delayed_teleop = TimerAction(
        period=4.0,
        actions=[teleop_node]
    )
    

    
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
        DeclareLaunchArgument('perception', default_value='true',
                            description='Start perception nodes'),
        DeclareLaunchArgument('camera_view', default_value='true',
                            description='Open separate camera viewer'),
        
        # === LAUNCH SEQUENCE ===
        gazebo_launch,
        slam_node,
        perception_disabled_msg,  # Show message when perception is disabled
        delayed_perception,       # Now enabled with proper error handling
        delayed_rviz,
        delayed_teleop,
        camera_viewer
    ])