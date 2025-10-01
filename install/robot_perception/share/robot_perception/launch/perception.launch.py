from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.conditions import IfCondition
import os

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    enable_vision = LaunchConfiguration('enable_vision', default='true')
    enable_detector = LaunchConfiguration('enable_detector', default='true')
    camera_topic = LaunchConfiguration('camera_topic', default='image_raw')
    camera_info_topic = LaunchConfiguration('camera_info_topic', default='camera_info')
    
    # Configuration file
    config_file = PathJoinSubstitution([
        FindPackageShare('robot_perception'),
        'config',
        'robot_perception_params.yaml'
    ])
    
    # Camera processing node
    camera_processor = Node(
        package='robot_perception',
        executable='camera_processor',
        name='camera_processor',
        output='screen',
        parameters=[
            config_file,
            {'use_sim_time': use_sim_time},
            {'camera_topic': camera_topic},
            {'camera_info_topic': camera_info_topic}
        ],
        remappings=[
            ('image_raw', camera_topic),
            ('camera_info', camera_info_topic)
        ],
        condition=IfCondition(enable_vision)
    )
    
    # Object detection node (placeholder for your model)
    object_detector = Node(
        package='robot_perception',
        executable='object_detector',
        name='object_detector',
        output='screen',
        parameters=[
            config_file,
            {'use_sim_time': use_sim_time}
        ],
        remappings=[
            ('image_raw', camera_topic)
        ],
        condition=IfCondition(enable_detector)
    )
    
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation (Gazebo) clock if true'),
            
        DeclareLaunchArgument(
            'enable_vision',
            default_value='true',
            description='Enable vision processing nodes'),
        
        DeclareLaunchArgument(
            'enable_detector',
            default_value='true',
            description='Enable object detector node'),
            
        DeclareLaunchArgument(
            'camera_topic',
            default_value='image_raw',
            description='Camera image topic name'),
            
        DeclareLaunchArgument(
            'camera_info_topic',
            default_value='camera_info',
            description='Camera info topic name'),
        
        camera_processor,
        object_detector,
    ])
