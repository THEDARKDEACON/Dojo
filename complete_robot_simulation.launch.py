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
  
  # Arduino Integration Bypass Mode (simplified motion control)
  ros2 launch complete_robot_simulation.launch.py bypass_mode:=true
  
  # Bypass mode with minimal components (no GUI, no vision)
  ros2 launch complete_robot_simulation.launch.py bypass_mode:=true gui:=false vision:=false
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Launch arguments with sensible defaults
    world = LaunchConfiguration('world', default='mapping_world.world')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    gui = LaunchConfiguration('gui', default='true')
    rviz = LaunchConfiguration('rviz', default='true')
    teleop = LaunchConfiguration('teleop', default='false')  # Disabled by default for autonomous operation
    slam = LaunchConfiguration('slam', default='true')
    navigation = LaunchConfiguration('navigation', default='false')
    vision = LaunchConfiguration('vision', default='false')  # Disabled by default until ultralytics is installed
    bypass_mode = LaunchConfiguration('bypass_mode', default='false')
    autonomous_exploration = LaunchConfiguration('autonomous_exploration', default='true')  # Enable by default for autonomous mapping
    
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
    
    # Start Gazebo Harmonic simulation
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            ])
        ]),
        launch_arguments={
            'gz_args': [world_file, ' -r -v 4'],
            'on_exit_shutdown': 'true'
        }.items()
    )
    
    # Robot state publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[robot_description, {'use_sim_time': use_sim_time}],
        output='screen'
    )
    
    # Spawn robot in Gazebo Harmonic
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-entity', 'dojo_robot',
            '-topic', 'robot_description',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.1'
        ],
        output='screen'
    )
    
    # ROS-Gazebo Bridge for topic communication (sensors temporarily disabled due to Ogre2 conflicts)
    gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry',
            '/joint_states@sensor_msgs/msg/JointState@gz.msgs.Model',
            '/tf@tf2_msgs/msg/TFMessage@gz.msgs.Pose_V',
            '/clock@rosgraph_msgs/msg/Clock@gz.msgs.Clock'
        ],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen'
    )
    
    # LiDAR bridge for scan data (required for SLAM)
    lidar_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/lidar@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan'
        ],
        remappings=[
            ('/lidar', '/scan')
        ],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen'
    )
    
    # Twist Mux for command velocity multiplexing (disabled in bypass mode)
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
        output='screen',
        condition=UnlessCondition(bypass_mode)
    )
    
    # SLAM Toolbox for mapping (available in bypass mode but optional)
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
    
    # Vision Detection System (disabled in bypass mode)
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
    
    # Bypass Mode Launch (when bypass_mode is enabled)
    bypass_mode_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_control'),
                'launch',
                'bypass_mode.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'debug': 'false'
        }.items(),
        condition=IfCondition(bypass_mode)
    )
    
    # Simple Autonomous Movement (starts immediately)
    simple_autonomous_movement = TimerAction(
        period=10.0,  # Start after 10 seconds to let system initialize
        actions=[
            ExecuteProcess(
                cmd=['python3', 'start_autonomous_movement.py'],
                output='screen',
                name='start_autonomous_movement',
                cwd='.'
            )
        ]
    )
    
    # Autonomous Exploration (when enabled)
    autonomous_exploration_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_navigation'),
                'launch',
                'autonomous_exploration.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'exploration_radius': '4.0',
            'min_frontier_size': '20'
        }.items(),
        condition=IfCondition(autonomous_exploration)
    )
    
    # Advanced features are now launched separately for modularity
    # Use: ros2 launch robot_semantic_slam cutting_edge_features.launch.py
    
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
        DeclareLaunchArgument('world', default_value='mapping_world.world',
                            description='Gazebo world file name (e.g., mapping_world.world, house.world, empty.world)'),
        DeclareLaunchArgument('use_sim_time', default_value='true',
                            description='Use simulation (Gazebo) clock if true'),
        DeclareLaunchArgument('gui', default_value='true',
                            description='Start Gazebo GUI'),
        DeclareLaunchArgument('rviz', default_value='true',
                            description='Start RViz visualization'),
        DeclareLaunchArgument('teleop', default_value='false',
                            description='Start teleop keyboard control (disabled by default for autonomous operation)'),
        DeclareLaunchArgument('slam', default_value='true',
                            description='Start SLAM for mapping'),
        DeclareLaunchArgument('navigation', default_value='false',
                            description='Start Navigation2 stack (requires existing map or SLAM)'),
        DeclareLaunchArgument('vision', default_value='false',
                            description='Start Vision Detection system with object detection (requires ultralytics)'),
        DeclareLaunchArgument('bypass_mode', default_value='false',
                            description='Enable Arduino Integration Bypass Mode (disables safety systems)'),
        DeclareLaunchArgument('autonomous_exploration', default_value='true',
                            description='Enable autonomous frontier-based exploration for mapping (enabled by default)'),
        
        # Launch all components
        gazebo_launch,
        robot_state_publisher,
        spawn_robot,
        gz_bridge,
        lidar_bridge,
        twist_mux,
        slam_toolbox,
        simple_autonomous_movement,
        nav2_launch,
        vision_detection_launch,
        bypass_mode_launch,
        autonomous_exploration_launch,
        rviz_node,
        teleop_node,
    ])