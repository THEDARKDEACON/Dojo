from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command, PathJoinSubstitution, FindExecutable
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_name = 'new_package'
    pkg_share = get_package_share_directory(pkg_name)

    urdf_file = PathJoinSubstitution([pkg_share, 'urdf', 'zeta.urdf.xacro'])
    rviz_config_file = PathJoinSubstitution([pkg_share, 'config', 'zeta.rviz'])

    robot_description_content = Command([
        FindExecutable(name='xacro'),
        ' ',
        urdf_file
    ])

    return LaunchDescription([
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            output='screen'
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[{
                'robot_description': robot_description_content
            }],
            output='screen'
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config_file],
            output='screen'
        ),
    ])
