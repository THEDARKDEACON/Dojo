from setuptools import setup

package_name = 'robot_navigation'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/autonomous_exploration.launch.py',
                                               'launch/autonomous_movement.launch.py',
                                               'launch/localization.launch.py',
                                               'launch/map_server.launch.py',
                                               'launch/nav2.launch.py',
                                               'launch/navigation.launch.py',
                                               'launch/slam.launch.py']),
        ('share/' + package_name + '/config', ['config/bt_navigator_params.yaml',
                                               'config/controller_params.yaml',
                                               'config/costmap_common_params.yaml',
                                               'config/global_costmap_params.yaml',
                                               'config/local_costmap_params.yaml',
                                               'config/localization_params.yaml',
                                               'config/map_server_params.yaml',
                                               'config/nav2_params.yaml',
                                               'config/planner_params.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='your.email@example.com',
    description='Robot Navigation Package',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'map_diagnostic_node = robot_navigation.map_diagnostic_node:main',
            'map_status_monitor = robot_navigation.map_status_monitor:main',
            'frame_validator = robot_navigation.frame_validator:main',
            'autonomous_explorer = robot_navigation.autonomous_explorer:main',
            'autonomous_movement_controller = robot_navigation.autonomous_movement_controller:main',
            'simple_autonomous_movement = robot_navigation.simple_autonomous_movement:main',
            'semantic_navigator = robot_navigation.semantic_navigator:main',
        ],
    },
)
