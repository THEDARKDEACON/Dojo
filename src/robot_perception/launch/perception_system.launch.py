#!/usr/bin/env python3
# Copyright 2023 Your Name
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, IncludeLaunchDescription, ExecuteProcess, RegisterEventHandler
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit, OnProcessStart
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node, SetParameter
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Get the package share directory
    pkg_share = FindPackageShare('robot_perception')
    
    # Launch arguments
    config_file = LaunchConfiguration('config_file')
    use_rviz = LaunchConfiguration('use_rviz', default='true')
    use_lidar = LaunchConfiguration('use_lidar', default='true')
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    
    # RViz config file
    default_rviz_config = os.path.join(
        get_package_share_directory('robot_perception'),
        'rviz',
        'perception_integration.rviz'
    )
    
    # Declare launch arguments
    declare_config_file_cmd = DeclareLaunchArgument(
        'config_file',
        default_value=os.path.join(
            get_package_share_directory('robot_perception'),
            'config',
            'perception_params.yaml'
        ),
        description='Full path to the config file to use'
    )
    
    declare_use_rviz_cmd = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Whether to launch RViz'
    )
    
    declare_use_lidar_cmd = DeclareLaunchArgument(
        'use_lidar',
        default_value='true',
        description='Whether to use LiDAR processing'
    )
    
    # Create the launch configuration variables
    params = [config_file]
    
    # Camera Processor Node
    camera_processor_node = Node(
        package='robot_perception',
        executable='camera_processor',
        name='camera_processor',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'config_file': config_file
        }],
        remappings=[
            ('/camera/image_raw', '/camera/color/image_raw'),
            ('/camera/camera_info', '/camera/color/camera_info'),
            ('/perception/processed_image', '/perception/camera/processed_image'),
            ('/perception/detection_markers', '/perception/camera/detection_markers')
        ]
    )
    
    # Object Detector Node
    object_detector_node = Node(
        package='robot_perception',
        executable='object_detector',
        name='object_detector',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'config_file': config_file,
            'detection.model': 'yolov8n.pt',
            'detection.confidence_threshold': 0.5,
            'publish_images': True,
            'visualize_in_rviz': True,
            'camera_frame': 'camera_color_optical_frame'
        }],
        remappings=[
            ('/camera/image_raw', '/camera/color/image_raw'),
            ('/camera/camera_info', '/camera/color/camera_info'),
            ('/perception/detections', '/perception/object_detections/image'),
            ('/perception/detection_info', '/perception/object_detections/info'),
            ('/perception/object_count', '/perception/object_detections/count'),
            ('/perception/detection_markers', '/perception/object_detections/markers')
        ]
    )
    
    # LiDAR Processor Node (conditionally included)
    lidar_processor_node = Node(
        package='robot_perception',
        executable='lidar_processor',
        name='lidar_processor',
        output='screen',
        condition=IfCondition(use_lidar),
        parameters=[{
            'use_sim_time': use_sim_time,
            'config_file': config_file
        }],
        remappings=[
            ('/points2', '/velodyne_points'),
            ('/perception/pointcloud', '/perception/lidar/pointcloud'),
            ('/perception/clusters', '/perception/lidar/clusters'),
            ('/perception/cluster_markers', '/perception/lidar/cluster_markers')
        ]
    )
    
    # Perception Integrator Node
    perception_integrator_node = Node(
        package='robot_perception',
        executable='perception_integrator',
        name='perception_integrator',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'config_file': config_file,
            'use_pointcloud': use_lidar
        }],
        remappings=[
            ('/perception/objects', '/perception/tracking/objects'),
            ('/perception/object_markers', '/perception/tracking/object_markers')
        ]
    )
    
    # RViz Node
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', default_rviz_config],
        condition=IfCondition(use_rviz)
    )
    
    # Create the launch description
    ld = LaunchDescription()
    
    # Declare the launch options
    ld.add_action(declare_config_file_cmd)
    ld.add_action(declare_use_rviz_cmd)
    ld.add_action(declare_use_lidar_cmd)
    
    # Add nodes to the launch description
    ld.add_action(camera_processor_node)
    ld.add_action(object_detector_node)
    ld.add_action(lidar_processor_node)
    ld.add_action(perception_integrator_node)
    ld.add_action(rviz_node)
    
    return ld
