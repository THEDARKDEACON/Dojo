from setuptools import setup
import os
from glob import glob

package_name = 'robot_maintenance'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Robot Developer',
    maintainer_email='dev@robot.com',
    description='Predictive maintenance system with AI-powered health monitoring',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'health_monitor = robot_maintenance.health_monitor:main',
            'anomaly_detector = robot_maintenance.anomaly_detector:main',
            'maintenance_scheduler = robot_maintenance.maintenance_scheduler:main',
        ],
    },
)
