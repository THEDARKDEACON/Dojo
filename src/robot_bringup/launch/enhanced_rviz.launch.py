#!/usr/bin/env python3
"""
Enhanced RViz Launch File with SLAM and Vision Integration
Launches RViz with proper map visualization, camera feeds, and object detection displays
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, Node, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Get package directories
    pkg_robot_bringup = get_package_share_directory('robot_bringup')
    pkg_robot_navigation = get_package_share_directory('robot_navigation')
    pkg_robot_gazebo = get_package_share_directory('robot_gazebo')
    
    # Default paths
    default_rviz_config = os.path.join(pkg_robot_gazebo, 'rviz', 'simulation_with_sensors.rviz')
    
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    rviz_config = LaunchConfiguration('rviz_config', default=default_rviz_config)
    use_slam = LaunchConfiguration('use_slam', default='true')
    use_rviz = LaunchConfiguration('use_rviz', default='true')
    slam_params_file = LaunchConfiguration('slam_params_file', 
                                         default=os.path.join(pkg_robot_gazebo, 'config', 'slam_config.yaml'))
    
    # Declare launch arguments
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true')
    
    declare_rviz_config = DeclareLaunchArgument(
        'rviz_config',
        default_value=default_rviz_config,
        description='Full path to the RVIZ config file to use')
    
    declare_use_slam = DeclareLaunchArgument(
        'use_slam',
        default_value='true',
        description='Whether to start SLAM for mapping')
    
    declare_use_rviz = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Whether to start RVIZ')
    
    declare_slam_params_file = DeclareLaunchArgument(
        'slam_params_file',
        default_value=os.path.join(pkg_robot_gazebo, 'config', 'slam_config.yaml'),
        description='Full path to SLAM parameters file')
    
    # Include SLAM launch
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_robot_navigation, 'launch', 'slam.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'slam_params_file': slam_params_file,
            'use_lifecycle_manager': 'true',
            'autostart': 'true',
        }.items(),
        condition=IfCondition(use_slam)
    )
    
    # Map display diagnostic node
    map_diagnostic_node = Node(
        package='robot_navigation',
        executable='map_diagnostic_node.py',
        name='map_diagnostic_node',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'map_topic': '/map'},
            {'diagnostic_period': 2.0}
        ]
    )
    
    # Map status monitor for error handling and fallback visualization
    map_status_monitor = Node(
        package='robot_navigation',
        executable='map_status_monitor.py',
        name='map_status_monitor',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'map_topic': '/map'},
            {'fallback_marker_topic': '/map_fallback_markers'},
            {'robot_pose_topic': '/robot_pose'},
            {'check_interval': 1.0},
            {'map_timeout': 5.0}
        ]
    )
    
    # Frame validator for coordinate frame validation
    frame_validator = Node(
        package='robot_navigation',
        executable='frame_validator.py',
        name='frame_validator',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'diagnostic_period': 5.0},
            {'frame_timeout': 1.0}
        ]
    )
    
    # RViz node with enhanced configuration
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
        condition=IfCondition(use_rviz)
    )
    
    # Delay RViz to ensure SLAM is ready
    delayed_rviz = TimerAction(
        period=3.0,
        actions=[rviz_node]
    )
    
    return LaunchDescription([
        # Launch arguments
        declare_use_sim_time,
        declare_rviz_config,
        declare_use_slam,
        declare_use_rviz,
        declare_slam_params_file,
        
        # Launch SLAM first
        slam_launch,
        
        # Map diagnostics and monitoring
        map_diagnostic_node,
        map_status_monitor,
        frame_validator,
        
        # Delayed RViz launch
        delayed_rviz,
    ])