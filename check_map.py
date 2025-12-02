#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import OccupancyGrid
from tf2_ros import Buffer, TransformListener
import time

class MapVerifier(Node):
    def __init__(self):
        super().__init__('map_verifier')
        self.scan_received = False
        self.map_received = False
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        self.create_subscription(OccupancyGrid, '/map', self.map_callback, 10)

        self.timer = self.create_timer(1.0, self.check_status)
        self.start_time = time.time()

    def scan_callback(self, msg):
        self.scan_received = True

    def map_callback(self, msg):
        self.map_received = True

    def check_status(self):
        elapsed = time.time() - self.start_time
        
        # Check TFs
        odom_tf = False
        map_tf = False
        try:
            self.tf_buffer.lookup_transform('odom', 'base_link', rclpy.time.Time())
            odom_tf = True
        except Exception:
            pass

        try:
            self.tf_buffer.lookup_transform('map', 'odom', rclpy.time.Time())
            map_tf = True
        except Exception:
            pass

        self.get_logger().info(f"Status: Scan={self.scan_received}, Map={self.map_received}, TF_Odom={odom_tf}, TF_Map={map_tf}")

        if self.map_received:
            self.get_logger().info("✅ SUCCESS: Map received!")
            # Keep running to monitor stability
        
        if elapsed > 60 and not self.map_received:
            self.get_logger().error("❌ FAILURE: No map received after 60s.")
            # Don't exit, just log error

def main(args=None):
    rclpy.init(args=args)
    node = MapVerifier()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
