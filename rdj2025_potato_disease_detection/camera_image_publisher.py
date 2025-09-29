#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2


class CameraImagePublisher(Node):
    def __init__(self):
        super().__init__('camera_image_publisher')
        self.publisher_ = self.create_publisher(Image, 'camera_image', 10)
        self.bridge = CvBridge()

        # Open default camera (0 = first camera device)
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.get_logger().error("Could not open camera")
            return

        self.timer = self.create_timer(0.1, self.timer_callback)  # ~10 FPS
        self.get_logger().info("CameraImagePublisher started")

    def timer_callback(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().error("Failed to capture frame")
            return

        ros_image = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        self.publisher_.publish(ros_image)
        self.get_logger().info("Published camera frame")

    def destroy_node(self):
        if self.cap.isOpened():
            self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraImagePublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
