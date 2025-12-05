"""
Nav2 Launch File for Dojo Robot
Provides complete navigation stack integration using available Nav2 packages
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import IfCondition

def generate_launch_description():
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    params_file = LaunchConfiguration('params_file', default=PathJoinSubstitution([
        FindPackageShare('robot_navigation'), 'config', 'nav2_params.yaml'
    ]))
    
    # Since nav2_bringup is not available, we'll create a simple navigation launch
    # This is a simplified version that launches the essential Nav2 components
    
    # Lifecycle manager for Nav2
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'autostart': True},
            {'node_names': ['controller_server', 'planner_server', 'behavior_server', 'bt_navigator']},
            {'bond_timeout': 4.0},  # Increase timeout for slower systems
            {'attempt_respawn_reconnection': True},  # Retry on failure
        ]
    )
    
    # Controller server
    controller_server = Node(
        package='nav2_controller',
        executable='controller_server',
        output='screen',
        parameters=[params_file],
        remappings=[('cmd_vel', 'cmd_vel_nav')]  # Remap to mux input
        # remappings=[('cmd_vel', '/rosbot_xl_base_controller/cmd_vel')]  # Removed to use relay
    )
    
    # Planner server
    planner_server = Node(
        package='nav2_planner',
        executable='planner_server',
        output='screen',
        parameters=[params_file]
    )
    
    # BT Navigator
    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        output='screen',
        parameters=[params_file]
    )
    
    # Behavior server (replaces deprecated recoveries_server)
    behavior_server = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        output='screen',
        parameters=[params_file]
    )
    
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation (Gazebo) clock if true'
        ),
        DeclareLaunchArgument(
            'params_file',
            default_value=params_file,
            description='Full path to the ROS2 parameters file to use'
        ),
        controller_server,
        planner_server,
        behavior_server,
        bt_navigator,
        lifecycle_manager,  # Last - manages above nodes
    ])

