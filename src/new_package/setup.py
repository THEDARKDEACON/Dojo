from setuptools import setup
import os
from glob import glob

package_name = 'new_package'

setup(
    name=package_name,
    version='0.0.0',
    packages=[],  # No Python modules, just share data
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*')),
        (os.path.join('share', package_name, 'meshes'), glob('meshes/*')),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='annette-robosync',
    maintainer_email='annetteoundo@gmail.com',
    description='Robot description and simulation package for Zeta',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [],
    },
)

