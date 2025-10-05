#!/usr/bin/env python3
"""
Simple test for robot movement with front-wheel drive
"""

from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
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
    
    # Start Gazebo with empty world
    gazebo_server = ExecuteProcess(
        cmd=['gzserver', '--verbose', '/opt/ros/humble/share/gazebo_ros/worlds/empty.world'],
        output='screen'
    )
    
    # Robot state publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[robot_description, {'use_sim_time': True}],
        output='screen'
    )
    
    # Spawn robot
    spawn_robot = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-entity', 'test_robot',
            '-topic', 'robot_description',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.1'
        ],
        output='screen'
    )
    
    # Test movement command after robot spawns
    test_movement = TimerAction(
        period=5.0,
        actions=[
            ExecuteProcess(
                cmd=['ros2', 'topic', 'pub', '/cmd_vel', 'geometry_msgs/Twist', 
                     '{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.1}}', 
                     '--times', '10'],
                output='screen'
            )
        ]
    )
    
    return LaunchDescription([
        gazebo_server,
        robot_state_publisher,
        spawn_robot,
        test_movement,
    ])