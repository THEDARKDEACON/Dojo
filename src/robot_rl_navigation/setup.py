from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'robot_rl_navigation'

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
        # Model checkpoints directory
        (os.path.join('share', package_name, 'models'), []),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Dojo Robot Team',
    maintainer_email='dev@dojorobot.com',
    description='Reinforcement Learning based navigation for Dojo Robot',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'rl_navigator = robot_rl_navigation.rl_navigator:main',
            'navigation_env = robot_rl_navigation.navigation_env:main',
            'train_agent = robot_rl_navigation.train_agent:main',
            'policy_manager = robot_rl_navigation.policy_manager:main',
        ],
    },
)
