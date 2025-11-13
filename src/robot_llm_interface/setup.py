from setuptools import setup
import os
from glob import glob

package_name = 'robot_llm_interface'

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
    description='Embodied AI with Large Language Models for natural language robot control',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'llm_controller = robot_llm_interface.llm_controller:main',
            'task_planner = robot_llm_interface.task_planner:main',
            'explanation_generator = robot_llm_interface.explanation_generator:main',
        ],
    },
)
