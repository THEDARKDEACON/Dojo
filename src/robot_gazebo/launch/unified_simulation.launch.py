"""
Unified Simulation Launch File for Dojo Robot
Complete simulation with SLAM, camera, and object detection
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

    # Robot description
    robot_description_content = Command([
        'xacro ',
        PathJoinSubstitution([pkg_robot_description, 'urdf', 'dojo_robot.urdf.xacro']),
        ' use_gazebo:=true'
    ])
    
    robot_description = {'robot_description': robot_description_content}

    # Robot state publisher
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[
            {'use_sim_time': use_sim_time},
            robot_description
        ],
        output='screen'
    )

    # Gazebo launch
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [PathJoinSubstitution([pkg_robot_gazebo, 'launch', 'gazebo.launch.py'])]
        ),
        launch_arguments={
            'world': PathJoinSubstitution([pkg_robot_gazebo, 'worlds', world_name]),
            'use_sim_time': use_sim_time,
            'gui': 'true',
            'verbose': 'false',
            'paused': 'false',
        }.items(),
    )

    # Spawn robot
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description', '-entity', 'dojo_robot'],
        output='screen',
    )

    # Controller manager
    controller_manager = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[
            robot_description,
            PathJoinSubstitution([pkg_robot_gazebo, 'config', 'ros2_control.yaml'])
        ],
        output='screen',
    )

    # Joint state broadcaster
    joint_state_broadcaster = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen',
    )

    # Diff drive controller
    diff_drive_controller = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_drive_controller', '--controller-manager', '/controller_manager'],
        output='screen',
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
            pkg_robot_description, 'rviz', 'robot.rviz'
        ])],
        condition=IfCondition(use_rviz)
    )

    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument('world', default_value='empty.world',
                            description='Gazebo world file'),
        DeclareLaunchArgument('use_sim_time', default_value='true',
                            description='Use simulation clock'),
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
        robot_state_publisher_node,
        gazebo,
        spawn_entity,
        
        # Control system
        controller_manager,
        joint_state_broadcaster,
        diff_drive_controller,
        
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
