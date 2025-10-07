#!/usr/bin/env python3
"""
Complete Robot Simulation Launch File
This comprehensive launch file provides all robot simulation capabilities:
- Gazebo simulation with GUI
- Robot spawning and state publishing
- SLAM for mapping
- Navigation2 stack for autonomous navigation
- Vision detection system with object detection
- RViz visualization with all sensors
- Teleop keyboard control
- Command velocity multiplexing

Usage Examples:
  # Basic simulation with SLAM and vision
  ros2 launch complete_robot_simulation.launch.py
  
  # Full autonomous navigation setup
  ros2 launch complete_robot_simulation.launch.py navigation:=true
  
  # Headless simulation (no GUI)
  ros2 launch complete_robot_simulation.launch.py gui:=false rviz:=false
  
  # Vision-only mode (no SLAM)
  ros2 launch complete_robot_simulation.launch.py slam:=false navigation:=false
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Launch arguments with sensible defaults
    world = LaunchConfiguration('world', default='empty.world')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    gui = LaunchConfiguration('gui', default='true')
    rviz = LaunchConfiguration('rviz', default='true')
    teleop = LaunchConfiguration('teleop', default='true')
    slam = LaunchConfiguration('slam', default='true')
    navigation = LaunchConfiguration('navigation', default='false')
    vision = LaunchConfiguration('vision', default='true')
    
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
    
    # Gazebo world file
    world_file = PathJoinSubstitution([
        FindPackageShare('robot_gazebo'),
        'worlds',
        world
    ])
    
    # Start Gazebo server
    gazebo_server = ExecuteProcess(
        cmd=['gzserver', '--verbose', '-s', 'libgazebo_ros_init.so', '-s', 'libgazebo_ros_factory.so', world_file],
        output='screen'
    )
    
    # Start Gazebo client (GUI)
    gazebo_client = ExecuteProcess(
        cmd=['gzclient'],
        output='screen',
        condition=IfCondition(gui)
    )
    
    # Robot state publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[robot_description, {'use_sim_time': use_sim_time}],
        output='screen'
    )
    
    # Spawn robot in Gazebo
    spawn_robot = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-entity', 'dojo_robot',
            '-topic', 'robot_description',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.1'
        ],
        output='screen'
    )
    
    # Twist Mux for command velocity multiplexing
    twist_mux = Node(
        package='twist_mux',
        executable='twist_mux',
        parameters=[
            PathJoinSubstitution([
                FindPackageShare('robot_control'),
                'config',
                'twist_mux_config.yaml'
            ]),
            {'use_sim_time': use_sim_time}
        ],
        remappings=[
            ('/cmd_vel_out', '/cmd_vel')
        ],
        output='screen'
    )
    
    # SLAM Toolbox for mapping
    slam_toolbox = Node(
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
    
    # Navigation2 stack (when enabled)
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('nav2_bringup'),
                'launch',
                'navigation_launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'params_file': PathJoinSubstitution([
                FindPackageShare('robot_navigation'),
                'config',
                'nav2_params.yaml'
            ])
        }.items(),
        condition=IfCondition(navigation)
    )
    
    # Vision Detection System
    vision_detection_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_perception'),
                'launch',
                'vision_detection.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'confidence_threshold': '0.5',
            'debug_mode': 'false'
        }.items(),
        condition=IfCondition(vision)
    )
    
    # RViz with comprehensive visualization
    rviz_config_file = PathJoinSubstitution([
        FindPackageShare('robot_gazebo'),
        'rviz',
        'simulation_with_sensors.rviz'
    ])
    
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(rviz)
    )
    
    # Teleop keyboard (delayed start to ensure robot is spawned)
    teleop_node = TimerAction(
        period=5.0,
        actions=[
            ExecuteProcess(
                cmd=['xterm', '-e', 'ros2', 'run', 'teleop_twist_keyboard', 'teleop_twist_keyboard', '--ros-args', '-r', '/cmd_vel:=/cmd_vel_teleop'],
                output='screen'
            )
        ],
        condition=IfCondition(teleop)
    )
    
    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument('world', default_value='empty.world',
                            description='Gazebo world file name (e.g., empty.world, house.world)'),
        DeclareLaunchArgument('use_sim_time', default_value='true',
                            description='Use simulation (Gazebo) clock if true'),
        DeclareLaunchArgument('gui', default_value='true',
                            description='Start Gazebo GUI'),
        DeclareLaunchArgument('rviz', default_value='true',
                            description='Start RViz visualization'),
        DeclareLaunchArgument('teleop', default_value='true',
                            description='Start teleop keyboard control'),
        DeclareLaunchArgument('slam', default_value='true',
                            description='Start SLAM for mapping'),
        DeclareLaunchArgument('navigation', default_value='false',
                            description='Start Navigation2 stack (requires existing map or SLAM)'),
        DeclareLaunchArgument('vision', default_value='true',
                            description='Start Vision Detection system with object detection'),
        
        # Launch all components
        gazebo_server,
        gazebo_client,
        robot_state_publisher,
        spawn_robot,
        twist_mux,
        slam_toolbox,
        nav2_launch,
        vision_detection_launch,
        rviz_node,
        teleop_node,
    ])