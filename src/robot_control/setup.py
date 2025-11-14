from setuptools import setup

package_name = 'robot_control'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', [
            'launch/control.launch.py',
            'launch/configuration_manager.launch.py',
            'launch/health_monitoring.launch.py',
            'launch/safety_system.launch.py'
        ]),
        ('share/' + package_name + '/config', 
            [
                'config/arduino.yaml',
                'config/controllers.yaml',
                'config/twist_mux.yaml'
            ]
        ),
        ('share/' + package_name + '/../../config', ['../../config/robot_config.yaml'])
    ],
    install_requires=['setuptools', 'pyserial', 'opencv-python', 'numpy', 'psutil'],
    zip_safe=True,
    maintainer='You',
    maintainer_email='you@example.com',
    description='Arduino serial bridge and motor control for the robot.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'arduino_bridge.py = robot_control.arduino_bridge:main',
            'cmd_vel_to_motors.py = robot_control.cmd_vel_to_motors:main',
            'control_manager.py = robot_control.control_manager:main',
            'configuration_manager.py = robot_control.configuration_manager:main',
            'hardware_discovery.py = robot_control.hardware_discovery:main',
            'device_manager.py = robot_control.device_abstraction:main',
            'camera_driver.py = robot_control.camera_driver:main',
            'lidar_driver.py = robot_control.lidar_driver:main',
            'hardware_manager.py = robot_control.hardware_manager:main',
            'graceful_degradation.py = robot_control.graceful_degradation:main',
            'diagnostic_system.py = robot_control.diagnostic_system:main',
            'safety_supervisor.py = robot_control.safety_supervisor:main',
            'emergency_stop_handler.py = robot_control.emergency_stop_handler:main',
            'velocity_limiter.py = robot_control.velocity_limiter:main',
            'watchdog_system.py = robot_control.watchdog_system:main',
        ],
    },
)
