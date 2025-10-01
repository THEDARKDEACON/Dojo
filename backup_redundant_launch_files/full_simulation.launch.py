#!/usr/bin/env python3
"""
Consolidated Dojo Robot Simulation Launch File
Handles everything from simulation to visualization in one place
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    RegisterEventHandler,
    TimerAction,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
    PythonExpression,
)
from launch_ros.actions import Node, SetParameter
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # ===== Launch Arguments =====
    world_name = LaunchConfiguration('world', default='empty.world')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    use_rviz = LaunchConfiguration('use_rviz', default='true')
    use_teleop = LaunchConfiguration('use_teleop', default='true')
    use_slam = LaunchConfiguration('use_slam', default='true')
    use_nav2 = LaunchConfiguration('use_nav2', default='true')

    # ===== Path Definitions =====
    pkg_robot_gazebo = FindPackageShare('robot_gazebo')
    pkg_robot_description = FindPackageShare('robot_description')
    pkg_robot_control = FindPackageShare('robot_control')

    # ===== Robot State Publisher =====
    robot_description_content = Command([
        'xacro ',
        PathJoinSubstitution([pkg_robot_description, 'urdf', 'dojo_robot.urdf.xacro']),
        ' use_gazebo:=true'
    ])
    
    robot_description = {'robot_description': robot_description_content}

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[
            {'use_sim_time': use_sim_time},
            robot_description
        ],
        output='screen'
    )

    # ===== Gazebo Launch =====
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

    # Spawn Robot
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description', '-entity', 'dojo_robot'],
        output='screen',
    )

    # ===== Control System =====
    # Controller Manager
    controller_manager = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[
            robot_description,
            PathJoinSubstitution([pkg_robot_gazebo, 'config', 'ros2_control.yaml'])
        ],
        output='screen',
    )

    # Joint State Broadcaster
    joint_state_broadcaster = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen',
    )

    # Diff Drive Controller
    diff_drive_controller = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_drive_controller', '--controller-manager', '/controller_manager'],
        output='screen',
    )

    # twist_mux for command multiplexing
    twist_mux_params = PathJoinSubstitution([pkg_robot_control, 'config', 'twist_mux.yaml'])
    twist_mux = Node(
        package='twist_mux',
        executable='twist_mux',
        name='twist_mux',
        parameters=[
            twist_mux_params,
            {'use_sim_time': use_sim_time},
        ],
        remappings=[
            ('/cmd_vel_out', '/diff_drive_controller/cmd_vel_unstamped')
        ],
        output='screen',
        arguments=['--ros-args', '--log-level', 'info'],
    )

    # ===== SLAM Toolbox =====
    slam_params_file = PathJoinSubstitution([pkg_robot_gazebo, 'config', 'slam_config.yaml'])
    
    start_async_slam_toolbox_node = Node(
        parameters=[
            slam_params_file,
            {'use_sim_time': use_sim_time},
            {'map_frame': 'map'},
            {'base_frame': 'base_footprint'},
            {'odom_frame': 'odom'},
            {'map_start_pose_required': False},
            {'scan_topic': '/scan'},
            {'queue_size': 10},
            {'publish_tf': True},
            {'publish_odom': True},
        ],
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        condition=IfCondition(use_slam),
    )

    # ===== RViz =====
    rviz_config = PathJoinSubstitution([pkg_robot_gazebo, 'rviz', 'full_simulation.rviz'])
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[
            {'use_sim_time': use_sim_time},
            # Add any additional parameters needed for visualization
        ],
        condition=IfCondition(use_rviz),
        remappings=[
            ('/initialpose', 'initialpose'),
            ('/goal_pose', 'goal_pose'),
        ],
    )
    
    # Camera image processing
    image_proc_node = Node(
        package='image_proc',
        executable='image_proc',
        name='image_proc',
        namespace='camera',
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    # ===== Teleop =====
    # Launch a custom teleop node with proper velocity scaling
    teleop_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        output='screen',
        prefix='xterm -e',
        remappings=[
            ('/cmd_vel', '/cmd_vel_scaled')
        ],
        parameters=[
            {'use_sim_time': use_sim_time},
            {'speed': 0.5},  # Max linear speed (m/s)
            {'turn': 1.0}    # Max angular speed (rad/s)
        ],
        condition=IfCondition(use_teleop)
    )
    
    # Add a node to scale the velocity commands
    cmd_vel_scaler = Node(
        package='robot_gazebo',
        executable='cmd_vel_relay.py',
        name='cmd_vel_relay',
        output='screen',
        parameters=[
            {'input_topic': '/cmd_vel_scaled'},
            {'output_topic': '/diff_drive_controller/cmd_vel_unstamped'},
            {'scale_linear': 0.5},  # Reduce linear speed to 50%
            {'scale_angular': 1.0}   # Full angular speed
        ],
        condition=IfCondition(use_teleop)
    )

    # ===== Event Handlers =====
    # Delay controller manager start after robot spawn
    delay_controller_manager = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_entity,
            on_exit=[controller_manager],
        )
    )

    # Delay joint state broadcaster after controller manager
    delay_joint_state_broadcaster = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=controller_manager,
            on_exit=[joint_state_broadcaster],
        )
    )

    # Delay diff drive controller start after joint state broadcaster
    delay_diff_drive_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster,
            on_exit=[diff_drive_controller],
        )
    )

    # ===== Return Launch Description =====
    return LaunchDescription([
        # Set use_sim_time for all nodes
        SetParameter(name='use_sim_time', value=use_sim_time),
        
        # Launch arguments
        DeclareLaunchArgument('world', default_value='empty.world',
                            description='Gazebo world file'),
        DeclareLaunchArgument('use_sim_time', default_value='true',
                            description='Use simulation (Gazebo) clock if true'),
        DeclareLaunchArgument('use_rviz', default_value='true',
                            description='Launch RViz if true'),
        DeclareLaunchArgument('use_teleop', default_value='true',
                            description='Enable teleop keyboard control if true'),
        DeclareLaunchArgument('use_slam', default_value='true',
                            description='Launch SLAM Toolbox if true'),
        DeclareLaunchArgument('use_nav2', default_value='true',
                            description='Launch Navigation2 if true'),

        # Nodes
        robot_state_publisher_node,
        gazebo,
        spawn_entity,
        
        # Event handlers for controller startup
        delay_controller_manager,
        delay_joint_state_broadcaster,
        delay_diff_drive_controller,
        
        # Teleop and command scaling
        teleop_node,
        cmd_vel_scaler,
        
        # Delayed RViz start
        TimerAction(
            period=2.0,
            actions=[rviz_node]
        ),

        # Delayed start of SLAM and image processing
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=diff_drive_controller,
                on_exit=[
                    TimerAction(
                        period=3.0,
                        actions=[
                            start_async_slam_toolbox_node,
                            image_proc_node,
                        ]
                    )
                ],
            )
        ),
    ])