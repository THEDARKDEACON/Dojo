#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TwistStamped

class CmdVelRelay(Node):
    def __init__(self):
        super().__init__('cmd_vel_relay')
        # Subscribe to /cmd_vel (Twist) from Teleop/Nav2
        self.sub = self.create_subscription(Twist, '/cmd_vel', self.listener_callback, 10)
        
        # Publish to controller topic (TwistStamped)
        # Note: Controller in Jazzy seems to enforce TwistStamped even if configured otherwise
        self.pub = self.create_publisher(TwistStamped, '/rosbot_xl_base_controller/cmd_vel', 10)
        
        self.get_logger().info('Relaying /cmd_vel (Twist) -> /rosbot_xl_base_controller/cmd_vel (TwistStamped)')

    def listener_callback(self, msg):
        # Debug logging (throttled)
        if hasattr(self, 'last_log_time'):
            if (self.get_clock().now() - self.last_log_time).nanoseconds > 1e9: # 1 second
                if abs(msg.linear.x) > 0.01 or abs(msg.angular.z) > 0.01:
                    self.get_logger().info(f'Relaying cmd_vel: lin={msg.linear.x:.2f}, ang={msg.angular.z:.2f}')
                self.last_log_time = self.get_clock().now()
        else:
            self.last_log_time = self.get_clock().now()

        stamped_msg = TwistStamped()
        stamped_msg.header.stamp = self.get_clock().now().to_msg()
        stamped_msg.header.frame_id = 'base_link'
        stamped_msg.twist = msg
        self.pub.publish(stamped_msg)

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
