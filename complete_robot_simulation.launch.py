#!/usr/bin/env python3
"""
Complete Robot Simulation with Gazebo GUI, RViz, Teleop, and SLAM
This launch file provides everything you need to see and control your robot
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Launch arguments
    world = LaunchConfiguration('world', default='empty.world')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    gui = LaunchConfiguration('gui', default='true')
    rviz = LaunchConfiguration('rviz', default='true')
    teleop = LaunchConfiguration('teleop', default='true')
    slam = LaunchConfiguration('slam', default='true')
    
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
    
    # RViz with navigation and map visualization
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', PathJoinSubstitution([
            FindPackageShare('robot_gazebo'),
            'rviz',
            'navigation_with_map.rviz'
        ])],
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
                            description='Gazebo world file name'),
        DeclareLaunchArgument('use_sim_time', default_value='true',
                            description='Use simulation (Gazebo) clock if true'),
        DeclareLaunchArgument('gui', default_value='true',
                            description='Start Gazebo GUI'),
        DeclareLaunchArgument('rviz', default_value='true',
                            description='Start RViz visualization'),
        DeclareLaunchArgument('teleop', default_value='true',
                            description='Start teleop keyboard'),
        DeclareLaunchArgument('slam', default_value='true',
                            description='Start SLAM for mapping'),
        
        # Launch everything
        gazebo_server,
        gazebo_client,
        robot_state_publisher,
        spawn_robot,
        twist_mux,
        slam_toolbox,
        rviz_node,
        teleop_node,
    ])