import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import numpy as np


class PotatoDiseaseDetection(Node):
    def __init__(self):
        super().__init__('potato_disease_detection_node')

        self.subscription = self.create_subscription(
            Image,
            '/image',
            self.listener_callback,
            10)
        self.publisher_ = self.create_publisher(String, '/inference_result', 10)

        self.bridge = CvBridge()
        self.get_logger().info("Potato Disease Detection Node has started.")


    def listener_callback(self, msg):
        # Convert ROS Image to OpenCV format
        cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        # Run inference (placeholder ML model)
        result = self.run_inference(cv_image)

        # Publish inference result
        result_msg = String()
        result_msg.data = result
        self.publisher_.publish(result_msg)

        self.get_logger().info(f'Published result: {result}')


    def run_inference(self, image: np.ndarray) -> str:
        """
        Placeholder ML inference for testing flow.
        """
        # Dummy classifier: detects if average pixel intensity > 127
        avg_intensity = np.mean(image)
        if avg_intensity > 127:
            return "Healthy Potato"
        else:
            return "Diseased Potato"


def main(args=None):
    rclpy.init(args=args)
    node = PotatoDiseaseDetection()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
