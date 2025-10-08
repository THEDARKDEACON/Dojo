#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class KeyboardNode(Node):
    def __init__(self):
        super().__init__('trapdoor_keyboard')
        self.publisher = self.create_publisher(String, '/trapdoor_cmd', 10)
        self.get_logger().info("Press 'O' to open and 'C' to close the trapdoor")

        while rclpy.ok():
            cmd = input("Command (O/C): ").strip().upper()
            if cmd in ['O', 'C']:
                msg = String()
                msg.data = cmd
                self.publisher.publish(msg)
                self.get_logger().info(f"Published: {cmd}")
            else:
                self.get_logger().warn("Invalid input, use 'O' or 'C'")

def main(args=None):
    rclpy.init(args=args)
    node = KeyboardNode()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
