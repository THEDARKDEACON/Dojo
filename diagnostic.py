import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from rosgraph_msgs.msg import Clock
from tf2_msgs.msg import TFMessage

class DiagnosticNode(Node):
    def __init__(self):
        super().__init__('diagnostic_node')
        self.create_subscription(Clock, '/clock', self.clock_cb, 10)
        self.create_subscription(JointState, '/joint_states', self.joint_cb, 10)
        self.create_subscription(Odometry, '/odom', self.odom_cb, 10)
        self.create_subscription(Twist, '/cmd_vel', self.cmd_cb, 10)
        self.create_subscription(TFMessage, '/tf', self.tf_cb, 10)
        
        self.clock_count = 0
        self.joint_count = 0
        self.odom_count = 0
        self.cmd_count = 0
        self.tf_count = 0
        
        self.create_timer(1.0, self.timer_cb)

    def clock_cb(self, msg): self.clock_count += 1
    def joint_cb(self, msg): self.joint_count += 1
    def odom_cb(self, msg): self.odom_count += 1
    def cmd_cb(self, msg): self.cmd_count += 1
    def tf_cb(self, msg): self.tf_count += 1

    def timer_cb(self):
        self.get_logger().info(f"Rates: Clock={self.clock_count}, Joints={self.joint_count}, Odom={self.odom_count}, Cmd={self.cmd_count}, TF={self.tf_count}")
        self.clock_count = 0
        self.joint_count = 0
        self.odom_count = 0
        self.cmd_count = 0
        self.tf_count = 0

def main():
    rclpy.init()
    node = DiagnosticNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
