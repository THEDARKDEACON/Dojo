"""
Complete Robot Bringup Launch File
Provides comprehensive robot functionality with automatic mode detection:
- Intelligent simulation vs hardware mode detection
- Complete simulation with SLAM, vision, and teleop (like complete_robot_simulation.launch.py)
- Full hardware support with Arduino, camera, and LiDAR drivers
- Modular architecture with optional perception and navigation
- RViz visualization and keyboard control

Usage Examples:
  # Auto-detected mode with full features
  ros2 launch robot_bringup bringup.launch.py
  
  # Force simulation mode with navigation
  ros2 launch robot_bringup bringup.launch.py use_gazebo:=true use_navigation:=true
  
  # Hardware mode with perception
  ros2 launch robot_bringup bringup.launch.py use_hardware:=true use_perception:=true
  
  # Minimal mode (no SLAM, RViz, or teleop)
  ros2 launch robot_bringup bringup.launch.py use_slam:=false use_rviz:=false use_teleop:=false
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction, OpaqueFunction, TimerAction, ExecuteProcess
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory, PackageNotFoundError
import os
import sys

def detect_operation_mode():
    """Detect operation mode based on environment and available packages."""
    # Check environment variables
    use_simulation = os.getenv('USE_SIMULATION', 'false').lower() == 'true'
    use_gazebo_env = os.getenv('USE_GAZEBO', 'false').lower() == 'true'
    
    if use_simulation or use_gazebo_env:
        # Check if Gazebo packages are available
        try:
            get_package_share_directory('robot_gazebo')
            get_package_share_directory('gazebo_ros')
            return 'simulation'
        except PackageNotFoundError:
            print("WARNING: Simulation requested but Gazebo packages not available, using hardware mode")
    
    return 'hardware'

def validate_mode_requirements(mode):
    """Validate that requirements for the mode are met."""
    missing_packages = []
    
    if mode == 'simulation':
        required_sim_packages = ['robot_gazebo', 'gazebo_ros', 'controller_manager']
        for package in required_sim_packages:
            try:
                get_package_share_directory(package)
            except PackageNotFoundError:
                missing_packages.append(package)
    else:  # hardware mode
        required_hw_packages = ['robot_hardware', 'robot_control']
        for package in required_hw_packages:
            try:
                get_package_share_directory(package)
            except PackageNotFoundError:
                missing_packages.append(package)
    
    if missing_packages:
        print(f"ERROR: Missing required packages for {mode} mode: {missing_packages}")
        print("Please install missing packages or switch modes.")
        return False
    
    return True

def generate_launch_description():
    # Detect operation mode
    detected_mode = detect_operation_mode()
    
    # Launch arguments with mode-aware defaults
    operation_mode = LaunchConfiguration('operation_mode', default=detected_mode)
    use_sim_time = LaunchConfiguration('use_sim_time', default='true' if detected_mode == 'simulation' else 'false')
    use_gazebo = LaunchConfiguration('use_gazebo', default='true' if detected_mode == 'simulation' else 'false')
    use_hardware = LaunchConfiguration('use_hardware', default='false' if detected_mode == 'simulation' else 'true')
    
    # Component flags - enable key features by default for complete robot functionality
    use_control = LaunchConfiguration('use_control', default='true')
    use_perception = LaunchConfiguration('use_perception', default='true')  # Enable vision by default
    use_navigation = LaunchConfiguration('use_navigation', default='false')  # Keep disabled, requires map
    use_robot_description = LaunchConfiguration('use_robot_description', default='true')
    use_config_manager = LaunchConfiguration('use_config_manager', default='true')
    
    # Simulation-specific features
    use_slam = LaunchConfiguration('use_slam', default='true')  # Enable SLAM by default
    use_rviz = LaunchConfiguration('use_rviz', default='true')  # Enable RViz by default
    use_teleop = LaunchConfiguration('use_teleop', default='true')  # Enable teleop by default
    
    # Hardware component flags (auto-detected based on available packages)
    use_arduino = LaunchConfiguration('use_arduino', default='true')
    use_camera = LaunchConfiguration('use_camera', default='true')
    use_lidar = LaunchConfiguration('use_lidar', default='true')
    
    # Configuration manager (loads mode-specific parameters)
    config_manager_node = Node(
        package='robot_control',
        executable='configuration_manager.py',
        name='configuration_manager',
        parameters=[{'operation_mode': operation_mode}],
        output='screen',
        condition=IfCondition(use_config_manager)
    )
    
    # Robot description
    robot_description_content = Command([
        'xacro ', 
        PathJoinSubstitution([
            FindPackageShare('robot_description'),
            'urdf',
            'robot.urdf.xacro'
        ]),
        ' use_gazebo:=', use_gazebo,
        ' use_sim_time:=', use_sim_time
    ])
    
    robot_description = {'robot_description': robot_description_content}
    
    # Robot state publisher
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[robot_description, {'use_sim_time': use_sim_time}],
        output='screen',
        condition=IfCondition(use_robot_description)
    )
    
    # Simulation launch (when use_gazebo=true)
    def get_simulation_launch():
        """Get simulation launch if packages are available."""
        try:
            gazebo_share = get_package_share_directory('robot_gazebo')
            return IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(gazebo_share, 'launch', 'gazebo.launch.py')
                ),
                launch_arguments={
                    'use_sim_time': use_sim_time,
                    'world': LaunchConfiguration('world', default='empty.world'),
                    'gui': LaunchConfiguration('gui', default='true'),
                    'use_config_manager': 'false',  # We already have one
                }.items(),
                condition=IfCondition(use_gazebo)
            )
        except PackageNotFoundError:
            print("WARNING: robot_gazebo package not found, simulation not available")
            return None
    
    simulation_launch = get_simulation_launch()
    
    # Hardware layer - new unified hardware interface (when use_gazebo=false)
    def get_hardware_launch():
        """Get hardware launch if packages are available."""
        try:
            hardware_share = get_package_share_directory('robot_hardware')
            return IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(hardware_share, 'launch', 'hardware.launch.py')
                ),
                launch_arguments={
                    'use_sim_time': use_sim_time,
                    'use_arduino': use_arduino,
                    'use_camera': use_camera,
                    'use_lidar': use_lidar,
                }.items(),
                condition=IfCondition(use_hardware)
            )
        except PackageNotFoundError:
            print("WARNING: robot_hardware package not found, hardware interface not available")
            return None
    
    hardware_launch = get_hardware_launch()
    
    # Control layer - high-level control coordination (hardware mode only)
    def get_control_launch():
        """Get control launch if packages are available."""
        try:
            control_share = get_package_share_directory('robot_control')
            return IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(control_share, 'launch', 'control.launch.py')
                ),
                launch_arguments={
                    'use_sim_time': use_sim_time,
                    'operation_mode': operation_mode,
                }.items(),
                condition=IfCondition(use_control)
            )
        except PackageNotFoundError:
            print("WARNING: robot_control package not found, control layer not available")
            return None
    
    control_launch = get_control_launch()
    
    # Perception layer - optional computer vision and AI
    def get_perception_launch():
        """Get perception launch if packages are available."""
        try:
            perception_share = get_package_share_directory('robot_perception')
            return IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(perception_share, 'launch', 'perception.launch.py')
                ),
                launch_arguments={
                    'use_sim_time': use_sim_time,
                    'camera_topic': 'image_raw',
                    'camera_info_topic': 'camera_info',
                    'enable_vision': 'true',
                    'enable_detector': 'true'
                }.items(),
                condition=IfCondition(use_perception)
            )
        except PackageNotFoundError:
            print("INFO: robot_perception package not found, perception not available")
            return None
    
    perception_launch = get_perception_launch()
    
    # Navigation layer - optional autonomous navigation
    def get_navigation_launch():
        """Get navigation launch if packages are available."""
        try:
            navigation_share = get_package_share_directory('robot_navigation')
            return IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(navigation_share, 'launch', 'nav2.launch.py')
                ),
                launch_arguments={
                    'use_sim_time': use_sim_time
                }.items(),
                condition=IfCondition(use_navigation)
            )
        except PackageNotFoundError:
            print("INFO: robot_navigation package not found, navigation not available")
            return None
    
    navigation_launch = get_navigation_launch()
    
    # Add direct components for both simulation and hardware modes
    def get_direct_components():
        """Get direct components for complete functionality in both modes."""
        components = []
        
        # SLAM Toolbox - works for both simulation and hardware
        slam_config_path = None
        if detected_mode == 'simulation':
            slam_config_path = PathJoinSubstitution([
                FindPackageShare('robot_gazebo'),
                'config',
                'slam_config.yaml'
            ])
        else:  # hardware mode
            try:
                slam_config_path = PathJoinSubstitution([
                    FindPackageShare('robot_hardware'),
                    'config',
                    'slam_config.yaml'
                ])
            except:
                # Fallback to robot_control config
                slam_config_path = PathJoinSubstitution([
                    FindPackageShare('robot_control'),
                    'config',
                    'slam_config.yaml'
                ])
        
        slam_toolbox = Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[
                slam_config_path,
                {'use_sim_time': use_sim_time}
            ],
            condition=IfCondition(use_slam)
        )
        components.append(slam_toolbox)
        
        if detected_mode == 'simulation':
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
                condition=IfCondition(use_slam)
            )
            components.append(slam_toolbox)
            
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
            components.append(twist_mux)
            
            # RViz with comprehensive visualization
            try:
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
                    condition=IfCondition(use_rviz)
                )
                components.append(rviz_node)
            except:
                print("INFO: RViz config not found, using default")
                
            # Teleop keyboard (delayed start to ensure robot is spawned)
            teleop_node = TimerAction(
                period=5.0,
                actions=[
                    ExecuteProcess(
                        cmd=['xterm', '-e', 'ros2', 'run', 'teleop_twist_keyboard', 'teleop_twist_keyboard', '--ros-args', '-r', '/cmd_vel:=/cmd_vel_teleop'],
                        output='screen'
                    )
                ],
                condition=IfCondition(use_teleop)
            )
            components.append(teleop_node)
            
        return components
    
    direct_components = get_direct_components()
    
    # Build launch list dynamically based on available packages
    launch_nodes = [
        config_manager_node,
        robot_state_publisher_node,
    ]
    
    # Add mode-specific launches
    if simulation_launch:
        launch_nodes.append(simulation_launch)
    if hardware_launch:
        launch_nodes.append(hardware_launch)
    if control_launch:
        launch_nodes.append(control_launch)
    if perception_launch:
        launch_nodes.append(perception_launch)
    if navigation_launch:
        launch_nodes.append(navigation_launch)
    
    # Add direct components for complete functionality
    launch_nodes.extend(direct_components)
    
    # Group all launches for better organization
    robot_group = GroupAction(launch_nodes)
    
    # Validate mode requirements
    if not validate_mode_requirements(detected_mode):
        sys.exit(1)
    
    # Print mode information
    print(f"Complete Robot bringup starting in {detected_mode} mode")
    print(f"Available launches: simulation={simulation_launch is not None}, "
          f"hardware={hardware_launch is not None}, control={control_launch is not None}, "
          f"perception={perception_launch is not None}, navigation={navigation_launch is not None}")
    if detected_mode == 'simulation':
        print(f"Simulation features: SLAM=enabled, RViz=enabled, Teleop=enabled, Vision=enabled")
    else:
        print(f"Hardware features: Arduino=enabled, Camera=enabled, LiDAR=enabled, SLAM=enabled, Vision=enabled")
    
    # Launch argument declarations
    return LaunchDescription([
        # Mode and core arguments
        DeclareLaunchArgument('operation_mode', default_value=detected_mode,
                           description='Operation mode: simulation or hardware'),
        DeclareLaunchArgument('use_sim_time', 
                           default_value='true' if detected_mode == 'simulation' else 'false',
                           description='Use simulation (Gazebo) clock if true'),
        DeclareLaunchArgument('use_gazebo', 
                           default_value='true' if detected_mode == 'simulation' else 'false',
                           description='Enable Gazebo simulation'),
        DeclareLaunchArgument('use_hardware', 
                           default_value='false' if detected_mode == 'simulation' else 'true',
                           description='Enable hardware interfaces'),
        
        # Component arguments
        DeclareLaunchArgument('use_control', default_value='true',
                           description='Enable control system'),
        DeclareLaunchArgument('use_perception', default_value='true',
                           description='Enable perception stack'),
        DeclareLaunchArgument('use_navigation', default_value='false',
                           description='Enable navigation stack'),
        DeclareLaunchArgument('use_robot_description', default_value='true',
                           description='Load robot description'),
        DeclareLaunchArgument('use_config_manager', default_value='true',
                           description='Use configuration manager'),
        
        # Simulation-specific arguments
        DeclareLaunchArgument('use_slam', default_value='true',
                           description='Enable SLAM for mapping'),
        DeclareLaunchArgument('use_rviz', default_value='true',
                           description='Start RViz visualization'),
        DeclareLaunchArgument('use_teleop', default_value='true',
                           description='Start teleop keyboard control'),
        
        # Hardware component arguments
        DeclareLaunchArgument('use_arduino', default_value='true',
                           description='Enable Arduino interface'),
        DeclareLaunchArgument('use_camera', default_value='true',
                           description='Enable camera driver'),
        DeclareLaunchArgument('use_lidar', default_value='true',
                           description='Enable LiDAR driver'),
        
        # Simulation arguments
        DeclareLaunchArgument('world', default_value='empty.world',
                           description='Gazebo world file'),
        DeclareLaunchArgument('gui', default_value='true',
                           description='Start Gazebo GUI'),
        
        # Add all robot components
        robot_group
    ])
