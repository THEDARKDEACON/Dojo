#!/usr/bin/env python3
"""
Simple relay node to forward and optionally scale velocity commands.
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

class CmdVelRelay(Node):
    def __init__(self):
        super().__init__('cmd_vel_relay')
        
        # Parameters
        self.declare_parameter('input_topic', '/cmd_vel_scaled')
        self.declare_parameter('output_topic', '/diff_drive_controller/cmd_vel_unstamped')
        self.declare_parameter('scale_linear', 1.0)
        self.declare_parameter('scale_angular', 1.0)
        
        self.input_topic = self.get_parameter('input_topic').value
        self.output_topic = self.get_parameter('output_topic').value
        self.scale_linear = self.get_parameter('scale_linear').value
        self.scale_angular = self.get_parameter('scale_angular').value
        
        # Create publisher and subscriber
        self.publisher = self.create_publisher(Twist, self.output_topic, 10)
        self.subscription = self.create_subscription(
            Twist,
            self.input_topic,
            self.cmd_vel_callback,
            10
        )
        
        self.get_logger().info(f'Relaying messages from {self.input_topic} to {self.output_topic}')
        self.get_logger().info(f'Scaling: linear={self.scale_linear}, angular={self.scale_angular}')
    
    def cmd_vel_callback(self, msg):
        # Scale the velocity commands
        msg.linear.x *= self.scale_linear
        msg.angular.z *= self.scale_angular
        self.publisher.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = CmdVelRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
