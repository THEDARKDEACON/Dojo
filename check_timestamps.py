#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from rosgraph_msgs.msg import Clock
from tf2_msgs.msg import TFMessage
import time

class TimestampVerifier(Node):
    def __init__(self):
        super().__init__('timestamp_verifier')
        self.clock_time = 0.0
        self.scan_time = 0.0
        self.tf_time = 0.0

        self.create_subscription(Clock, '/clock', self.clock_callback, 10)
        self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        self.create_subscription(TFMessage, '/tf', self.tf_callback, 10)

        self.timer = self.create_timer(1.0, self.check_status)

    def clock_callback(self, msg):
        self.clock_time = msg.clock.sec + msg.clock.nanosec * 1e-9

    def scan_callback(self, msg):
        self.scan_time = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9

    def tf_callback(self, msg):
        for transform in msg.transforms:
            if transform.header.frame_id == 'odom' and transform.child_frame_id == 'base_link':
                self.tf_time = transform.header.stamp.sec + transform.header.stamp.nanosec * 1e-9

    def check_status(self):
        self.get_logger().info(f"Clock: {self.clock_time:.2f}, Scan: {self.scan_time:.2f}, TF(odom->base): {self.tf_time:.2f}")
        
        if abs(self.clock_time - self.scan_time) > 1.0:
            self.get_logger().warn(f"⚠️ Scan time mismatch! Diff: {self.clock_time - self.scan_time:.2f}")
        
        if abs(self.clock_time - self.tf_time) > 1.0:
            self.get_logger().warn(f"⚠️ TF time mismatch! Diff: {self.clock_time - self.tf_time:.2f}")

def main(args=None):
    rclpy.init(args=args)
    node = TimestampVerifier()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
