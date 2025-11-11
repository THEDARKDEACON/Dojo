from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'robot_semantic_slam'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
    ],
    install_requires=[
        'setuptools',
        'rclpy',
        'sensor_msgs',
        'geometry_msgs',
        'vision_msgs',
        'nav_msgs',
        'std_msgs',
        'visualization_msgs',
        'cv_bridge',
        'opencv-python',
        'numpy',
        'ultralytics',  # YOLO
    ],
    zip_safe=True,
    maintainer='Dojo Robot Team',
    maintainer_email='team@dojorobot.ai',
    description='Advanced Semantic SLAM with AI-powered object detection and intelligent navigation',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'semantic_slam_node = robot_semantic_slam.semantic_slam_node:main',
            'enhanced_visualizer = robot_semantic_slam.enhanced_visualizer:main',
            'advanced_safety_system = robot_semantic_slam.advanced_safety_system:main',
            'semantic_interface = robot_semantic_slam.semantic_interface:main',
            'pointcloud_processor = robot_semantic_slam.pointcloud_processor:main',
            'performance_dashboard = robot_semantic_slam.performance_dashboard:main',
            'system_monitor = robot_semantic_slam.system_monitor:main',
        ],
    },
)
