"""
Improved Robot Bringup Launch File
Uses new modular hardware architecture with unified simulation support
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Launch arguments
    use_hardware = LaunchConfiguration('use_hardware', default='true')
    use_control = LaunchConfiguration('use_control', default='true')
    use_perception = LaunchConfiguration('use_perception', default='false')
    use_navigation = LaunchConfiguration('use_navigation', default='false')
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    use_robot_description = LaunchConfiguration('use_robot_description', default='true')
    # New flags
    use_gazebo = LaunchConfiguration('use_gazebo', default='false')
    use_arduino = LaunchConfiguration('use_arduino', default='true')
    use_camera = LaunchConfiguration('use_camera', default='true')
    use_lidar = LaunchConfiguration('use_lidar', default='true')
    
    # Robot description
    robot_description_content = Command([
        'xacro ', 
        PathJoinSubstitution([
            FindPackageShare('robot_description'),
            'urdf',
            'robot.urdf.xacro'  # Changed from dojo_robot.urdf.xacro to robot.urdf.xacro
        ]),
        ' ',
        'use_gazebo:=', use_gazebo,
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
    
    # Unified simulation launch (when use_gazebo=true)
    unified_simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('robot_gazebo'), 'launch', 'unified_simulation.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'use_slam': 'true',
            'use_nav2': use_navigation,
            'use_perception': use_perception,
            'use_rviz': 'true',
            'use_teleop': 'true'
        }.items(),
        condition=IfCondition(use_gazebo)
    )
    
    # Hardware layer - new unified hardware interface (when use_gazebo=false)
    hardware_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('robot_hardware'), 'launch', 'hardware.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'use_arduino': use_arduino,
            'use_camera': use_camera,
            'use_lidar': use_lidar,
        }.items(),
        condition=IfCondition(use_hardware)
    )
    
    # Control layer - high-level control coordination (when use_gazebo=false)
    control_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('robot_control'), 'launch', 'control.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time
        }.items(),
        condition=IfCondition(use_control)
    )
    
    # Perception layer - optional computer vision and AI (when use_gazebo=false)
    perception_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('robot_perception'), 'launch', 'perception.launch.py')
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
    
    # Navigation layer - optional autonomous navigation (when use_gazebo=false)
    navigation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('robot_navigation'), 'launch', 'nav2.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time
        }.items(),
        condition=IfCondition(use_navigation)
    )
    
    # Group all launches for better organization
    robot_group = GroupAction([
        robot_state_publisher_node,
        unified_simulation,  # This will be ignored if use_gazebo=false
        hardware_launch,     # This will be ignored if use_gazebo=true
        control_launch,      # This will be ignored if use_gazebo=true
        perception_launch,   # This will be ignored if use_gazebo=true
        navigation_launch,   # This will be ignored if use_gazebo=true
    ])
    
    # Launch argument declarations
    return LaunchDescription([
        DeclareLaunchArgument('use_hardware', default_value='true',
                           description='Enable hardware interfaces'),
        DeclareLaunchArgument('use_control', default_value='true',
                           description='Enable control system'),
        DeclareLaunchArgument('use_perception', default_value='false',
                           description='Enable perception stack'),
        DeclareLaunchArgument('use_navigation', default_value='false',
                           description='Enable navigation stack'),
        DeclareLaunchArgument('use_sim_time', default_value='true' if use_gazebo == 'true' else 'false',
                           description='Use simulation (Gazebo) clock if true'),
        DeclareLaunchArgument('use_robot_description', default_value='true',
                           description='Load robot description'),
        DeclareLaunchArgument('use_gazebo', default_value='false',
                           description='Enable Gazebo simulation'),
        DeclareLaunchArgument('use_arduino', default_value='true',
                           description='Enable Arduino interface'),
        DeclareLaunchArgument('use_camera', default_value='true',
                           description='Enable camera driver'),
        DeclareLaunchArgument('use_lidar', default_value='true',
                           description='Enable LiDAR driver'),
        
        # Include Gazebo launch file if use_gazebo is true
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('robot_gazebo'),
                    'launch',
                    'gazebo.launch.py'
                ])
            ]),
            condition=IfCondition(use_gazebo),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'world': 'empty.world'
            }.items()
        ),
        
        # Add all robot components
        robot_group
    ])
