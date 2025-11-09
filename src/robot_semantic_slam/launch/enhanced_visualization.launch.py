#!/usr/bin/env python3
"""
Enhanced Visualization Launch File
Launches 3D visualization and performance monitoring
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Launch arguments
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation time'
    )
    
    visualization_rate_arg = DeclareLaunchArgument(
        'visualization_rate',
        default_value='10.0',
        description='Visualization update rate in Hz'
    )
    
    use_rviz_arg = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Launch RViz with enhanced config'
    )
    
    # Launch configurations
    use_sim_time = LaunchConfiguration('use_sim_time')
    visualization_rate = LaunchConfiguration('visualization_rate')
    use_rviz = LaunchConfiguration('use_rviz')
    
    # Enhanced Visualizer Node
    enhanced_viz_node = Node(
        package='robot_semantic_slam',
        executable='enhanced_visualizer',
        name='enhanced_visualizer',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'visualization_rate': visualization_rate,
            'performance_monitoring': True,
            'path_history_length': 1000,
            'marker_lifetime': 5.0,
        }]
    )
    
    # PointCloud Processor Node
    pointcloud_processor_node = Node(
        package='robot_semantic_slam',
        executable='pointcloud_processor',
        name='pointcloud_processor',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'update_rate': 10.0,  # 10 Hz as per requirements
            'z_height': 0.3,  # Default height for 2D scan
            'point_size': 0.05,
            # Task 3.2: Scan accumulation parameters
            'accumulation_time': 10.0,  # 10 seconds accumulation window
            'voxel_size': 0.05,  # 5cm voxel size for downsampling
            'max_points': 1000000,  # 1 million points maximum
            'enable_accumulation': True,  # Enable dense mapping
            # Task 3.3: Height-based color mapping parameters
            'color_mode': 'height',  # 'height', 'intensity', or 'fixed'
            'min_height': -0.5,  # Minimum height for color mapping (red)
            'max_height': 2.0,  # Maximum height for color mapping (violet)
            'color_scheme': 'rainbow',  # 'rainbow', 'jet', 'hot', 'cool'
        }]
    )
    
    # RViz with enhanced 3D point cloud configuration
    rviz_config_file = PathJoinSubstitution([
        FindPackageShare('robot_gazebo'),
        'rviz',
        'pointcloud_3d_visualization.rviz'
    ])
    
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2_enhanced',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen'
    )
    
    return LaunchDescription([
        use_sim_time_arg,
        visualization_rate_arg,
        use_rviz_arg,
        enhanced_viz_node,
        pointcloud_processor_node,
        rviz_node,
    ])