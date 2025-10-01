from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Get the package share directory
    pkg_share = get_package_share_directory('robot_perception')
    
    # RViz config file path
    rviz_config_path = os.path.join(pkg_share, 'rviz', 'perception_integration.rviz')
    
    # Perception Integrator Node
    perception_integrator_node = Node(
        package='robot_perception',
        executable='perception_integrator',
        name='perception_integrator',
        output='screen',
        parameters=[{
            'use_sim_time': False,
        }]
    )
    
    # RViz Node
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_path]
    )
    
    return LaunchDescription([
        perception_integrator_node,
        rviz_node
    ])
