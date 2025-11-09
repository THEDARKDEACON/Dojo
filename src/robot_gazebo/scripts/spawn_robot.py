#!/usr/bin/env python3

import os
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription, LaunchContext
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node

def generate_launch_description():
    # Get the package directory
    pkg_robot_gazebo = get_package_share_directory('robot_gazebo')
    pkg_robot_description = get_package_share_directory('robot_description')
    
    # Path to the URDF file
    urdf_file = os.path.join(pkg_robot_description, 'urdf', 'robot.urdf.xacro')
    robot_description = xacro.process_file(urdf_file).toxml()
    
    # RViz configuration
    rviz_config = os.path.join(pkg_robot_gazebo, 'rviz', 'robot_simulation.rviz')
    
    # Robot state publisher node
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description, 'use_sim_time': True}],
    )
    
    # Spawn entity node
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-topic', 'robot_description', '-entity', 'robot', '-x', '0', '-y', '0', '-z', '0.1'],
        output='screen',
    )
    
    # RViz node
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
    )
    
    # Joint state publisher GUI
    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )
    
    return LaunchDescription([
        # Set use_sim_time to true
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'),
            
        # Launch nodes
        robot_state_publisher,
        spawn_entity,
        rviz,
        joint_state_publisher_gui,
    ])

if __name__ == '__main__':
    generate_launch_description()
