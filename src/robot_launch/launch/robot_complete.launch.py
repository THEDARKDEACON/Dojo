#!/usr/bin/env python3
from launch import LaunchDescription, LaunchContext
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, RegisterEventHandler, OpaqueFunction
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory, PackageNotFoundError
import os

def check_package(package_name):
    try:
        get_package_share_directory(package_name)
        return True
    except PackageNotFoundError:
        print(f"Warning: Package {package_name} not found, skipping...")
        return False

def generate_launch_description():
    # Configuration parameters
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    rviz_config = os.path.join(
        get_package_share_directory('robot_description'),
        'rviz',
        'dojo_robot.rviz'
    )

    # Declare launch arguments
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true'
    )

    # Create the launch description
    ld = LaunchDescription()
    ld.add_action(declare_use_sim_time)

    # Helper function to conditionally include launch files
    def include_launch(package, launch_file, **kwargs):
        try:
            pkg_share = get_package_share_directory(package)
            return IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg_share, 'launch', launch_file)
                ),
                launch_arguments=kwargs.get('launch_arguments', {}).items()
            )
        except PackageNotFoundError:
            print(f"Warning: Could not find package {package}, skipping {launch_file}")
            return None

    # Include components if available
    components = []
    
    # Add twist_mux for command velocity multiplexing
    twist_mux = Node(
        package="twist_mux",
        executable="twist_mux",
        parameters=[os.path.join(
            get_package_share_directory('robot_control'),
            'config',
            'twist_mux.yaml'
        )],
        remappings=[('/cmd_vel_out','/cmd_vel')],
        output='screen'
    )
    ld.add_action(twist_mux)
    
    # Add ros2arduino_bridge as a Node since it's a Python package
    try:
        bridge_node = Node(
            package='ros2arduino_bridge',
            executable='ros2arduino_bridge',
            name='ros2arduino_bridge',
            output='screen',
            parameters=[{
                'port': '/dev/ttyACM0',
                'baud': 115200,
                'debug': False
            }]
        )
        ld.add_action(bridge_node)
    except Exception as e:
        print(f"Warning: Could not create ros2arduino_bridge node: {e}")
    
    # Add other components
    components.extend([
        ('robot_description', 'robot_description/launch/robot_state_publisher.launch.py', {'launch_arguments': {'use_sim_time': use_sim_time}}),
        ('robot_sensors', 'robot_sensors/launch/sensors.launch.py', {'launch_arguments': {'use_sim_time': use_sim_time}}),
        ('robot_control', 'robot_control/launch/control.launch.py', {'launch_arguments': {'use_sim_time': use_sim_time}})
    ])

    actions = []
    for pkg, launch_file, kwargs in components:
        action = include_launch(pkg, launch_file, **kwargs)
        if action:
            ld.add_action(action)
            actions.append(action)

    # Launch RViz if available
    if check_package('rviz2'):
        rviz = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen'
        )
        if actions:
            ld.add_action(RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=actions[-1],
                    on_exit=[rviz]
                )
            ))
        else:
            ld.add_action(rviz)

    return ld
