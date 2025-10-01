#!/usr/bin/env python3
"""
Launch file for the robot simulation in Gazebo.
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, RegisterEventHandler
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch.event_handlers import OnProcessExit

def generate_launch_description():
    # Get the package directories
    pkg_robot_gazebo = get_package_share_directory('robot_gazebo')
    pkg_robot_description = get_package_share_directory('robot_description')
    
    # Launch configuration variables
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world = LaunchConfiguration('world', default='empty.world')
    
    # Declare launch arguments
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    )
    
    declare_world = DeclareLaunchArgument(
        'world',
        default_value='empty',
        description='Gazebo world file name (without .world extension)'
    )
    
    # Start Gazebo with the specified world
    start_gazebo = ExecuteProcess(
        cmd=['gazebo', '--verbose', '-s', 'libgazebo_ros_init.so',
             '-s', 'libgazebo_ros_factory.so',
             os.path.join(pkg_robot_gazebo, 'worlds', world + '.world')],
        output='screen'
    )
    
    # Get the robot description
    robot_description_content = Command([
        'xacro ', 
        PathJoinSubstitution([pkg_robot_description, 'urdf', 'robot.urdf.xacro']),
        ' use_ros2_control:=true',
        ' use_sim:=true',
        ' sim_mode:=gazebo'
    ])
    
    # Robot state publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_content,
            'use_sim_time': use_sim_time,
            'publish_frequency': 50.0
        }]
    )
    
    # Spawn the robot
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description',
                  '-entity', 'robot',
                  '-x', '0.0',
                  '-y', '0.0',
                  '-z', '0.1',
                  '-Y', '0.0'],
        output='screen'
    )
    
    # Load controllers
    load_joint_state_controller = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
             'joint_state_broadcaster'],
        output='screen'
    )
    
    load_diff_drive_controller = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
             'diff_drive_controller'],
        output='screen'
    )
    
    # RViz
    rviz_config = os.path.join(pkg_robot_gazebo, 'rviz', 'simulation.rviz')
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen'
    )
    
    # Controller manager
    controller_manager = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[
            os.path.join(pkg_robot_gazebo, 'config', 'gazebo_controllers.yaml'),
            {'use_sim_time': use_sim_time}
        ],
        output='screen'
    )
    
    # Delay loading controllers after Gazebo is up
    delay_controllers = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_entity,
            on_exit=[load_joint_state_controller, load_diff_drive_controller]
        )
    )
    
    return LaunchDescription([
        declare_use_sim_time,
        declare_world,
        
        # Start Gazebo
        start_gazebo,
        
        # Robot state publisher
        robot_state_publisher,
        
        # Spawn robot
        spawn_entity,
        
        # Controller manager
        controller_manager,
        
        # RViz
        rviz,
        
        # Delay loading controllers
        delay_controllers,
    ])
