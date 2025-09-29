from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package="rdj2025_potato_disease_detection",
            executable="camera_image_publisher",
            name="camera_image_publisher",
            output="screen"
        ),
        Node(
            package="rdj2025_potato_disease_detection",
            executable="potato_disease_detection_node",
            name="potato_disease_detection_node",
            output="screen"
        )
    ])
