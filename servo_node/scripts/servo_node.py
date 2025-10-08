#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import serial
import time

class ServoNode(Node):
    def __init__(self):
        super().__init__('servo_node')
        
        # Replace with your Arduino serial port and baudrate
        self.ser = serial.Serial('/dev/ttyACM0', 57600, timeout=1)
        time.sleep(2)  # give Arduino time to reset

        self.subscription = self.create_subscription(
            String,
            '/trapdoor_cmd',
            self.listener_callback,
            10
        )
        self.get_logger().info("Servo Node started, listening on /trapdoor_cmd")

    def listener_callback(self, msg):
        cmd = msg.data.upper()
        if cmd in ['O', 'C']:
            self.ser.write(cmd.encode())
            self.get_logger().info(f"Sent command to Arduino: {cmd}")
        else:
            self.get_logger().warn(f"Ignored invalid command: {cmd}")

def main(args=None):
    rclpy.init(args=args)
    node = ServoNode()
    rclpy.spin(node)
    node.ser.close()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
