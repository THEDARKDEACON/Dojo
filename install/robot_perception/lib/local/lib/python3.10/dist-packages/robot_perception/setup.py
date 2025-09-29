from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'robot_perception'

def get_data_files():
    """Get all data files for the package."""
    # Base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Data files to install
    data_files = [
        # Package manifest
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

    # Add RViz config files
    rviz_dir = os.path.join('rviz')
    if os.path.isdir(rviz_dir):
        data_files.append(
            (os.path.join('share', package_name, 'rviz'),
             [f for f in glob(os.path.join(rviz_dir, '*.rviz'))])
        )

    # Add model files
    models_dir = os.path.join('robot_perception')
    model_files = []
    for ext in ('*.pt', '*.pth', '*.onnx', '*.engine', '*.tflite'):
        model_files.extend(glob(os.path.join(models_dir, '**', ext), recursive=True))
    
    if model_files:
        data_files.append(
            (os.path.join('share', package_name, 'models'), model_files)
        )

    return data_files

# Find all packages in the robot_perception directory
packages = find_packages(where='.')

setup(
    name=package_name,
    version='0.2.0',
    packages=packages,
    data_files=get_data_files(),
    package_data={
        'robot_perception': [
            '*.yaml', '*.rviz', '*.pt', 'config/*.yaml', 'launch/*.launch.py'
        ]
    },
    install_requires=[
        'setuptools>=42.0.0',
        'opencv-python>=4.5.0',
        'numpy>=1.19.0',
        'scipy>=1.5.0',
        'scikit-learn>=0.24.0',
        'PyYAML>=5.4.1',
        'sensor-msgs-py>=4.0.0',
    ],
    extras_require={
        'deep_learning': [
            'torch>=1.8.0',
            'torchvision>=0.9.0',
            'ultralytics>=8.0.0',
            'onnxruntime>=1.8.0',
            'tensorflow>=2.5.0;platform_system!="Windows"',
        ],
        'docs': [
            'sphinx>=4.0.0',
            'sphinx-rtd-theme>=0.5.0',
            'sphinx-autodoc-typehints>=1.12.0',
        ],
        'test': [
            'pytest>=6.0.0',
            'pytest-cov>=2.12.0',
            'pytest-mock>=3.6.1',
        ],
    },
    zip_safe=False,
    maintainer='robosync',
    maintainer_email='robosync@example.com',
    description='Advanced robot perception package with camera, LiDAR, and sensor fusion capabilities',
    long_description=(
        'This package provides advanced perception capabilities for robots, '
        'including camera processing, LiDAR processing, object detection, and sensor fusion.'
    ),
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'camera_processor = robot_perception.nodes.camera_processor:main',
            'object_detector = robot_perception.nodes.object_detector:main',
            'lidar_processor = robot_perception.nodes.lidar_processor:main',
            'perception_integrator = robot_perception.nodes.perception_integrator:main',
        ],
    },
    python_requires='>=3.8',
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Software Development',
    ],
    keywords=['ROS2', 'perception', 'computer vision', 'LiDAR', 'sensor fusion', 'robotics'],
)
