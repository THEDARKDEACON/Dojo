"""Launch file for sensor fusion system."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    """Generate launch description for sensor fusion."""
    
    # Declare launch arguments
    config_file_arg = DeclareLaunchArgument(
        'config_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('robot_sensor_fusion'),
            'config',
            'sensor_fusion_params.yaml'
        ]),
        description='Path to sensor fusion configuration file'
    )
    
    # Sensor fusion node
    sensor_fusion_node = Node(
        package='robot_sensor_fusion',
        executable='sensor_fusion_node',
        name='sensor_fusion_node',
        output='screen',
        parameters=[LaunchConfiguration('config_file')],
        remappings=[
            ('/slam_pose', '/robot_pose'),  # Remap to actual SLAM pose topic
        ]
    )
    
    return LaunchDescription([
        config_file_arg,
        sensor_fusion_node,
    ])
