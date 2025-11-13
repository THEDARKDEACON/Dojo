from setuptools import setup
import os
from glob import glob

package_name = 'robot_digital_twin'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Robot Team',
    maintainer_email='robot@example.com',
    description='Digital twin technology for robot state prediction and mission planning',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'digital_twin = robot_digital_twin.digital_twin:main',
            'state_predictor = robot_digital_twin.state_predictor:main',
            'mission_planner = robot_digital_twin.mission_planner:main',
        ],
    },
)
