from setuptools import setup
import os
from glob import glob

package_name = 'robot_quantum'

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
    description='Quantum-inspired optimization for multi-robot path planning',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'quantum_planner = robot_quantum.quantum_planner:main',
            'qubo_solver = robot_quantum.qubo_solver:main',
        ],
    },
)
