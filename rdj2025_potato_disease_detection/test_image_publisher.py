#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import os
import random
from ament_index_python.packages import get_package_share_directory


class TestImagePublisher(Node):
    def __init__(self):
        super().__init__('test_image_publisher')
        self.publisher_ = self.create_publisher(Image, 'test_image', 10)
        self.bridge = CvBridge()

        # ✅ Use installed share directory
        package_share = get_package_share_directory('rdj2025_potato_disease_detection')
        images_path = os.path.join(package_share, 'images')

        self.image_files = [
            os.path.join(images_path, 'healthy.jpg'),
            os.path.join(images_path, 'early.jpg'),
            os.path.join(images_path, 'late.jpg'),
        ]

        self.timer = self.create_timer(3.0, self.timer_callback)
        self.get_logger().info("TestImagePublisher started (publishing every 3s)")

    def timer_callback(self):
        img_path = random.choice(self.image_files)
        cv_image = cv2.imread(img_path)

        if cv_image is None:
            self.get_logger().error(f"Could not read image: {img_path}")
            return

        ros_image = self.bridge.cv2_to_imgmsg(cv_image, encoding='bgr8')
        self.publisher_.publish(ros_image)
        self.get_logger().info(f"Published: {os.path.basename(img_path)}")


def main(args=None):
    rclpy.init(args=args)
    node = TestImagePublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
