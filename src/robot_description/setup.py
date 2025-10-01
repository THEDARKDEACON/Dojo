from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'robot_description'

def get_data_files():
    """Get all data files for the package."""
    data_files = [
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ]

    # Add launch files
    launch_dir = os.path.join('launch')
    if os.path.isdir(launch_dir):
        data_files.append(
            (os.path.join('share', package_name, 'launch'),
             [f for f in glob(os.path.join(launch_dir, '*.launch.py'))])
        )

    # Add config files
    config_dir = os.path.join('config')
    if os.path.isdir(config_dir):
        data_files.append(
            (os.path.join('share', package_name, 'config'),
             [f for f in glob(os.path.join(config_dir, '*.yaml'))])
        )

    # Add model files
    for directory in ['urdf', 'rviz', 'worlds', 'meshes', 'models']:
        if os.path.isdir(directory):
            data_files.append(
                (os.path.join('share', package_name, directory),
                 [f for f in glob(os.path.join(directory, '*'))])
            )

    return data_files

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    data_files=get_data_files(),
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Gareth Joel',
    maintainer_email='garethjoel@example.com',
    description='URDF and Xacro description of the Dojo robot with Gazebo support',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'display_robot = robot_description.display_robot:main',
        ],
    },
)
