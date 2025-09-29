from setuptools import find_packages, setup

package_name = 'rdj2025_potato_disease_detection'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),

        # Launch files
        ('share/' + package_name + '/launch', [
            'launch/potato_test_launch.py',
            'launch/potato_camera_launch.py',
        ]),

        # Images
        ('share/' + package_name + '/images', [
            'images/healthy.jpg',
            'images/early.png',
            'images/late.jpg',
        ]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='lenny',
    maintainer_email='codewithlennylen254@gmail.com',
    description='Potato disease detection using test images and camera input',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'potato_disease_detection_node = rdj2025_potato_disease_detection.potato_disease_detection_node:main',
            'test_image_publisher = rdj2025_potato_disease_detection.test_image_publisher:main',
            'camera_image_publisher = rdj2025_potato_disease_detection.camera_image_publisher:main',
        ],
    },
)
