#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, LaserScan
from rosgraph_msgs.msg import Clock
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

class ImuToClock(Node):
    def __init__(self):
        super().__init__('imu_to_clock')
        
        # QoS for high-speed sensor data
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        # Subscribe to Lidar (Reliable source of simulation time)
        self.scan_sub = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            qos
        )
        
        self.clock_pub = self.create_publisher(Clock, '/clock', 10)
        self.get_logger().info("Clock Generator Started - Listening to /scan")
        self.last_time = 0
        self.msg_count = 0

    def scan_callback(self, msg):
        # Create Clock message from Lidar timestamp
        clock_msg = Clock()
        clock_msg.clock = msg.header.stamp
        self.clock_pub.publish(clock_msg)
        
        # Log occasionally
        sec = msg.header.stamp.sec
        nanosec = msg.header.stamp.nanosec
        current_time = sec + nanosec * 1e-9
        
        if self.msg_count < 5:
            self.get_logger().info(f"Received Scan. Time: {current_time:.2f}s")
            self.msg_count += 1
        
        # Debug print every 1 second
        if current_time - self.last_time > 1.0:
            self.get_logger().info(f"Bridging Simulation Time: {current_time:.2f}s")
            self.last_time = current_time

def main(args=None):
    rclpy.init(args=args)
    node = ImuToClock()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
