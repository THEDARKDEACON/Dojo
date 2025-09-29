from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Get the package share directory
    pkg_share = get_package_share_directory('robot_perception')
    
    # Default model path (can be overridden with launch argument)
    default_model_path = os.path.join(pkg_share, 'models', 'yolov8n.pt')
    rviz_config_path = os.path.join(pkg_share, 'rviz', 'object_detection.rviz')
    
    # Declare launch arguments
    use_rviz = LaunchConfiguration('use_rviz', default='true')
    
    # Object Detector Node
    object_detector_node = Node(
        package='robot_perception',
        executable='object_detector',
        name='object_detector',
        output='screen',
        emulate_tty=True,
        parameters=[{
            'detection_method': 'yolo',
            'yolo.model_path': default_model_path,
            'yolo.confidence_threshold': 0.5,
            'debug': False,
            'publish_images': True,
            'visualize_in_rviz': True,
            'camera_frame': 'camera_link'
        }],
        remappings=[
            # Remap input topics
            ('/camera/image_raw', '/camera/color/image_raw'),
            ('/camera/camera_info', '/camera/color/camera_info'),
            # Remap output topics
            ('/perception/detections', '/perception/object_detections/image'),
            ('/perception/detection_info', '/perception/object_detections/info'),
            ('/perception/object_count', '/perception/object_detections/count'),
            ('/perception/detection_markers', '/perception/object_detections/markers')
        ]
    )
    
    # RViz Node
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_path],
        condition=launch.conditions.IfCondition(use_rviz)
    )
    
    # Create launch description
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Launch RViz2 with object detection visualization'),
            
        object_detector_node,
        rviz_node
    ])
