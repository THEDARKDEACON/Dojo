"""
Complete Simulation Launch File for Dojo Robot
Full-featured simulation with SLAM, navigation, perception, and teleop
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    RegisterEventHandler,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node, SetParameter
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Launch arguments
    world_name = LaunchConfiguration('world', default='empty.world')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    gui = LaunchConfiguration('gui', default='true')
    use_rviz = LaunchConfiguration('use_rviz', default='true')
    use_teleop = LaunchConfiguration('use_teleop', default='true')
    use_slam = LaunchConfiguration('use_slam', default='true')
    use_nav2 = LaunchConfiguration('use_nav2', default='true')
    use_perception = LaunchConfiguration('use_perception', default='true')

    # Path definitions
    pkg_robot_gazebo = FindPackageShare('robot_gazebo')
    pkg_robot_description = FindPackageShare('robot_description')
    pkg_robot_navigation = FindPackageShare('robot_navigation')
    pkg_robot_perception = FindPackageShare('robot_perception')

    # Basic Gazebo simulation
    gazebo_simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [PathJoinSubstitution([pkg_robot_gazebo, 'launch', 'gazebo.launch.py'])]
        ),
        launch_arguments={
            'world': world_name,
            'use_sim_time': use_sim_time,
            'gui': gui,
            'rviz': 'false',  # We'll launch RViz separately with our config
            'use_config_manager': 'true'
        }.items(),
    )



    # SLAM Toolbox
    slam_toolbox = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            PathJoinSubstitution([pkg_robot_gazebo, 'config', 'slam_config.yaml']),
            {'use_sim_time': use_sim_time}
        ],
        condition=IfCondition(use_slam)
    )

    # Navigation
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([pkg_robot_navigation, 'launch', 'nav2.launch.py'])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
        }.items(),
        condition=IfCondition(use_nav2)
    )

    # Perception
    perception = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([pkg_robot_perception, 'launch', 'perception.launch.py'])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'camera_topic': 'image_raw',
            'camera_info_topic': 'camera_info',
            'enable_vision': 'true',
            'enable_detector': 'true'
        }.items(),
        condition=IfCondition(use_perception)
    )

    # Teleop
    teleop = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop',
        output='screen',
        prefix='xterm -e',
        remappings=[
            ('/cmd_vel', '/diff_drive_controller/cmd_vel_unstamped')
        ],
        condition=IfCondition(use_teleop)
    )

    # RViz
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', PathJoinSubstitution([
            pkg_robot_gazebo, 'rviz', 'simulation.rviz'
        ])],
        condition=IfCondition(use_rviz)
    )

    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument('world', default_value='empty.world',
                            description='Gazebo world file'),
        DeclareLaunchArgument('use_sim_time', default_value='true',
                            description='Use simulation clock'),
        DeclareLaunchArgument('gui', default_value='true',
                            description='Start Gazebo GUI'),
        DeclareLaunchArgument('use_rviz', default_value='true',
                            description='Launch RViz'),
        DeclareLaunchArgument('use_teleop', default_value='true',
                            description='Launch teleop keyboard'),
        DeclareLaunchArgument('use_slam', default_value='true',
                            description='Launch SLAM'),
        DeclareLaunchArgument('use_nav2', default_value='true',
                            description='Launch Nav2'),
        DeclareLaunchArgument('use_perception', default_value='true',
                            description='Launch perception'),
        
        # Set use_sim_time parameter
        SetParameter(name='use_sim_time', value=use_sim_time),
        
        # Core simulation
        gazebo_simulation,

        
        # SLAM
        slam_toolbox,
        
        # Navigation
        navigation,
        
        # Perception
        perception,
        
        # Teleop
        teleop,
        
        # Visualization
        rviz,
    ])
