from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'robot_swarm'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Launch files
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
        # Config files
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Dojo Robot Team',
    maintainer_email='dev@dojorobot.com',
    description='Multi-robot swarm coordination for Dojo Robot',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'swarm_coordinator = robot_swarm.swarm_coordinator:main',
            'formation_controller = robot_swarm.formation_controller:main',
            'collaborative_mapper = robot_swarm.collaborative_mapper:main',
        ],
    },
)
