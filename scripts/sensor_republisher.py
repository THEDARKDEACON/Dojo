#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, Image, CameraInfo, PointCloud2
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

class SensorRepublisher(Node):
    def __init__(self):
        super().__init__('sensor_republisher')
        
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        # Lidar Relay
        self.scan_sub = self.create_subscription(LaserScan, '/scan', self.scan_callback, qos)
        self.scan_pub = self.create_publisher(LaserScan, '/scan_relayed', 10)
        
        # Camera Relay (Optional, but good for VSLAM)
        # self.img_sub = self.create_subscription(Image, '/camera/color/image_raw', self.img_callback, qos)
        # self.img_pub = self.create_publisher(Image, '/camera/color/image_raw_relayed', 10)
        
        self.get_logger().info("Sensor Republisher Started - Relaying /scan to /scan_relayed with System Time")

    def scan_callback(self, msg):
        # Overwrite timestamp with current system time
        msg.header.stamp = self.get_clock().now().to_msg()
        self.scan_pub.publish(msg)

    # def img_callback(self, msg):
    #     msg.header.stamp = self.get_clock().now().to_msg()
    #     self.img_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = SensorRepublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
