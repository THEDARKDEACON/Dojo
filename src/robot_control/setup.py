from setuptools import setup

package_name = 'robot_control'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/control.launch.py']),
        ('share/' + package_name + '/config', 
            [
                'config/arduino.yaml',
                'config/twist_mux.yaml'
            ]
        )
    ],
    install_requires=['setuptools', 'pyserial'],
    zip_safe=True,
    maintainer='You',
    maintainer_email='you@example.com',
    description='Arduino serial bridge and motor control for the robot.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'arduino_bridge = robot_control.arduino_bridge:main',
            'cmd_vel_to_motors = robot_control.cmd_vel_to_motors:main',
            'control_manager = robot_control.control_manager:main',
        ],
    },
)
