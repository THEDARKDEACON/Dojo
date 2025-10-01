import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription, LaunchContext
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, RegisterEventHandler, OpaqueFunction, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch.event_handlers import OnProcessStart, OnProcessExit
from launch.conditions import IfCondition

def generate_launch_description():
    # Get the package directory
    pkg_robot_gazebo = get_package_share_directory('robot_gazebo')
    pkg_robot_description = get_package_share_directory('robot_description')
    
    # Debug: Print paths
    print("Package directories:")
    print(f"- robot_gazebo: {pkg_robot_gazebo}")
    print(f"- robot_description: {pkg_robot_description}")
    
    # Paths
    world_path = os.path.join(pkg_robot_gazebo, 'worlds', 'empty.world')
    urdf_path = os.path.join(pkg_robot_description, 'urdf', 'robot.urdf')
    rviz_config_path = os.path.join(pkg_robot_gazebo, 'rviz', 'robot_simulation.rviz')
    controller_config_path = os.path.join(pkg_robot_gazebo, 'config', 'diff_drive_controller.yaml')
    
    # Debug: Print file paths
    print("\nFile paths:")
    print(f"- World: {world_path} (exists: {os.path.exists(world_path)})")
    print(f"- URDF: {urdf_path} (exists: {os.path.exists(urdf_path)})")
    print(f"- RViz config: {rviz_config_path} (exists: {os.path.exists(rviz_config_path)})")
    print(f"- Controller config: {controller_config_path} (exists: {os.path.exists(controller_config_path)})")
    
    # Debug: Print controller config content
    if os.path.exists(controller_config_path):
        print("\nController config content:")
        with open(controller_config_path, 'r') as f:
            print(f.read())
    
    # Launch configuration
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    use_rviz = LaunchConfiguration('use_rviz', default='true')
    
    # Robot description
    robot_description = {'robot_description': f'$(cat {urdf_path})' if os.path.exists(urdf_path) else f'$(xacro {urdf_path})'}
    
    # Add twist_mux for command velocity multiplexing
    twist_mux = Node(
        package="twist_mux",
        executable="twist_mux",
        parameters=[os.path.join(
            get_package_share_directory('robot_control'),
            'config',
            'twist_mux.yaml'
        )],
        remappings=[
            ('/cmd_vel_out', '/diff_drive_controller/cmd_vel_unstamped')
        ],
        output='screen'
    )

    # Robot state publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'robot_description': Command(['xacro ', urdf_path])
        }]
    )
    
    # Gazebo launch
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')
        ),
        launch_arguments={
            'world': world_path,
            'verbose': 'false',
            'pause': 'false',
            'use_sim_time': use_sim_time,
            'gui': 'true',
            'debug': 'false'
        }.items()
    )
    
    # Spawn entity
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description', '-entity', 'robot'],
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )
    
    # Debug: Print controller config path before creating controller manager
    debug_info = [
        LogInfo(msg=f"Controller config path: {controller_config_path}"),
        LogInfo(msg=f"Controller config exists: {os.path.exists(controller_config_path)}")
    ]
    
    # Controller manager
    controller_manager = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[
            {'robot_description': Command(['xacro ', urdf_path])},
            {'use_sim_time': use_sim_time},
            controller_config_path
        ],
        output='screen',
        arguments=['--ros-args', '--log-level', 'debug']
    )
    
    # Spawn joint state broadcaster
    spawn_joint_state_broadcaster = Node(
        package='controller_manager',
        executable='spawner',
        name='spawner_joint_state_broadcaster',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen'
    )
    
    # Spawn diff drive controller
    spawn_diff_drive_controller = Node(
        package='controller_manager',
        executable='spawner',
        name='spawner_diff_drive_controller',
        arguments=['diff_drive_controller', '--controller-manager', '/controller_manager'],
        output='screen'
    )
    
    # RViz
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_path],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(use_rviz)
    )
    
    # Set use_sim_time for Gazebo
    set_use_sim_time = ExecuteProcess(
        cmd=['ros2', 'param', 'set', '/gazebo', 'use_sim_time', use_sim_time],
        output='screen'
    )
    
    # Define launch description
    ld = LaunchDescription([
        # Nodes
        twist_mux,
        robot_state_publisher,
        set_use_sim_time,
        gazebo,
        spawn_entity,
        controller_manager,
        spawn_joint_state_broadcaster,
        spawn_diff_drive_controller,
        rviz
    ])
    
    # Add debug info
    for info in debug_info:
        ld.add_action(info)
    
    # Add launch arguments
    ld.add_action(DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    ))
    
    ld.add_action(DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Whether to start RViz'
    ))
    
    # Add nodes
    ld.add_action(set_use_sim_time)
    ld.add_action(robot_state_publisher)
    ld.add_action(gazebo)
    ld.add_action(spawn_entity)
    ld.add_action(controller_manager)
    
    # Add event handlers to ensure proper startup order
    ld.add_action(RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=controller_manager,
            on_start=[spawn_joint_state_broadcaster]
        )
    ))
    
    ld.add_action(RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=spawn_joint_state_broadcaster,
            on_start=[spawn_diff_drive_controller]
        )
    ))
    
    ld.add_action(RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=spawn_diff_drive_controller,
            on_start=[rviz]
        )
    ))
    
    return ld
