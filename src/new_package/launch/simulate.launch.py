from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess, TimerAction
from launch.substitutions import Command, PathJoinSubstitution, FindExecutable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    pkg_name = 'new_package'
    pkg_share = get_package_share_directory(pkg_name)

    # Paths
    urdf_file = PathJoinSubstitution([pkg_share, 'urdf', 'zeta.urdf.xacro'])
    world_file = os.path.join(pkg_share, 'worlds', 'empty.world')
    gazebo_ros = get_package_share_directory('gazebo_ros')

    # Robot description from xacro
    robot_description = Command([FindExecutable(name='xacro'), ' ', urdf_file])

    return LaunchDescription([
        # Launch Gazebo Classic with custom world
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(gazebo_ros, 'launch', 'gazebo.launch.py')
            ),
            launch_arguments={'world': world_file}.items()
        ),

        # Publish robot description
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': True
            }],
            output='screen'
        ),

        # Spawn robot in Gazebo
        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=[
                '-topic', 'robot_description',
                '-entity', 'zeta'
            ],
            output='screen'
        ),

        # Delay controller loading to ensure Gazebo and robot are ready
        TimerAction(
            period=15.0,
            actions=[
                ExecuteProcess(
                    cmd=['ros2', 'control', 'load_controller', '--set-state', 'active', 'joint_state_broadcaster'],
                    shell=True,
                    output='screen'
                ),
                ExecuteProcess(
                    cmd=['ros2', 'control', 'load_controller', '--set-state', 'active', 'diff_drive_controller'],
                    shell=True,
                    output='screen'
                )
            ]
        ),

        # Teleop keyboard control
        Node(
            package='teleop_twist_keyboard',
            executable='teleop_twist_keyboard',
            name='teleop_twist_keyboard',
            output='screen',
            prefix='xterm -e',
            remappings=[('/cmd_vel', '/diff_drive_controller/cmd_vel')]
        )
    ])
