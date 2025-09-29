from setuptools import find_packages
from setuptools import setup

setup(
    name='robot_perception',
    version='0.2.0',
    packages=find_packages(
        include=('robot_perception', 'robot_perception.*')),
)
