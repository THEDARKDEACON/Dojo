#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rosgraph_msgs.msg import Clock
import time

class FakeClock(Node):
    def __init__(self):
        super().__init__('fake_clock')
        self.publisher_ = self.create_publisher(Clock, '/clock', 10)
        self.timer = self.create_timer(0.01, self.publish_clock) # 100 Hz
        self.start_time = time.time()
        self.get_logger().info("Fake Clock Generator Started")

    def publish_clock(self):
        current_time = time.time() - self.start_time
        msg = Clock()
        # Convert seconds to sec and nanosec
        msg.clock.sec = int(current_time)
        msg.clock.nanosec = int((current_time - int(current_time)) * 1e9)
        self.publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = FakeClock()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
