from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'robot_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=[
        'setuptools',
        'rclpy',
        'std_msgs',
        'sensor_msgs',
        'vision_msgs',
        'nav_msgs',
        'diagnostic_msgs',
        'geometry_msgs',
    ],
    zip_safe=True,
    maintainer='robosync',
    maintainer_email='robosync@example.com',
    description='Robot bringup package with system validation and launch coordination',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'system_validator = robot_bringup.system_validator:main',
        ],
    },
    python_requires='>=3.8',
)