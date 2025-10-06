from setuptools import setup

package_name = 'robot_navigation'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='your.email@example.com',
    description='Robot Navigation Package',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'map_diagnostic_node.py = robot_navigation.map_diagnostic_node:main',
            'map_status_monitor.py = robot_navigation.map_status_monitor:main',
            'frame_validator.py = robot_navigation.frame_validator:main',
        ],
    },
)
