#!/usr/bin/env python3
"""
Launch file for the robot navigation stack with Nav2.
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, 
    IncludeLaunchDescription, 
    ExecuteProcess,
    RegisterEventHandler,
    TimerAction,
    LogInfo
)
from launch.event_handlers import OnProcessExit, OnProcessStart, OnExecutionComplete
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration, 
    PathJoinSubstitution, 
    Command, 
    PythonExpression
)
from launch_ros.actions import Node, LifecycleNode
from launch_ros.substitutions import FindPackageShare
from launch.conditions import IfCondition, UnlessCondition

def generate_launch_description():
    # Get package directories
    pkg_robot_navigation = get_package_share_directory('robot_navigation')
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')
    
    # Default paths
    default_params_file = os.path.join(pkg_robot_navigation, 'config', 'nav2_params.yaml')
    default_rviz_config = os.path.join(pkg_robot_navigation, 'config', 'navigation.rviz')
    default_map = os.path.join(pkg_robot_navigation, 'maps', 'map.yaml')
    
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    autostart = LaunchConfiguration('autostart', default='true')
    params_file = LaunchConfiguration('params_file', default=default_params_file)
    rviz_config = LaunchConfiguration('rviz_config', default=default_rviz_config)
    use_rviz = LaunchConfiguration('use_rviz', default='true')
    map_yaml_file = LaunchConfiguration('map', default=default_map)
    
    # Declare launch arguments
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true')
    
    declare_autostart = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically startup the nav2 stack')
    
    declare_params_file = DeclareLaunchArgument(
        'params_file',
        default_value=default_params_file,
        description='Full path to the ROS2 parameters file to use')
    
    declare_rviz_config = DeclareLaunchArgument(
        'rviz_config',
        default_value=default_rviz_config,
        description='Full path to the RVIZ config file to use')
    
    declare_use_rviz = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Whether to start RVIZ')
    
    declare_map_yaml = DeclareLaunchArgument(
        'map',
        default_value=default_map,
        description='Full path to map yaml file to load')
    
    # Include the Nav2 launch file
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav2_bringup, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'autostart': autostart,
            'params_file': params_file,
            'use_lifecycle_mgr': 'true',
        }.items()
    )
    
    # Map server
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[
            {'yaml_filename': map_yaml_file},
            {'use_sim_time': use_sim_time},
            {'frame_id': 'map'}
        ]
    )
    
    # AMCL
    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[
            os.path.join(pkg_robot_navigation, 'config', 'amcl_params.yaml'),
            {'use_sim_time': use_sim_time}
        ]
    )
    
    # Lifecycle manager
    lifecycle_nodes = ['map_server', 'amcl']
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'autostart': autostart},
            {'node_names': lifecycle_nodes}
        ]
    )
    
    # RViz
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
        condition=IfCondition(use_rviz)
    )
    
    # Create event handlers for lifecycle manager
    load_nodes = RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=map_server,
            on_start=[
                LogInfo(msg='Map server started, starting AMCL'),
                amcl,
                lifecycle_manager
            ]
        )
    )
    
    # Delay RViz to ensure everything is ready
    delayed_rviz = TimerAction(
        period=3.0,
        actions=[rviz]
    )
    
    return LaunchDescription([
        # Launch arguments
        declare_use_sim_time,
        declare_autostart,
        declare_params_file,
        declare_rviz_config,
        declare_use_rviz,
        declare_map_yaml,
        
        # Launch Nav2
        nav2_launch,
        
        # Map server and localization
        map_server,
        
        # Event handlers
        load_nodes,
        
        # Delayed actions
        delayed_rviz,
    ])
