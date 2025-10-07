#!/usr/bin/env python3
"""
Robot Status Checker - Verify robot movement and visualization
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import time

class RobotStatusChecker(Node):
    def __init__(self):
        super().__init__('robot_status_checker')
        
        # Publishers
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel_teleop', 10)
        
        # Subscribers
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_callback, 10)
        
        self.last_odom = None
        self.initial_position = None
        
        self.get_logger().info('🤖 Robot Status Checker Started')
        self.get_logger().info('📍 Waiting for initial position...')
        
    def odom_callback(self, msg):
        if self.initial_position is None:
            self.initial_position = (msg.pose.pose.position.x, msg.pose.pose.position.y)
            self.get_logger().info(f'📍 Initial position: x={self.initial_position[0]:.2f}, y={self.initial_position[1]:.2f}')
        
        self.last_odom = msg
        
    def test_movement(self):
        """Test robot movement"""
        if self.last_odom is None:
            self.get_logger().warn('❌ No odometry data received!')
            return False
            
        self.get_logger().info('🚀 Testing robot movement...')
        
        # Send forward command
        twist = Twist()
        twist.linear.x = 0.2
        self.cmd_pub.publish(twist)
        self.get_logger().info('➡️  Sending forward command (0.2 m/s)')
        
        time.sleep(2)
        
        # Stop
        twist.linear.x = 0.0
        self.cmd_pub.publish(twist)
        self.get_logger().info('⏹️  Stopping robot')
        
        time.sleep(1)
        
        # Check if robot moved
        if self.last_odom and self.initial_position:
            current_pos = (self.last_odom.pose.pose.position.x, self.last_odom.pose.pose.position.y)
            distance_moved = ((current_pos[0] - self.initial_position[0])**2 + 
                            (current_pos[1] - self.initial_position[1])**2)**0.5
            
            self.get_logger().info(f'📏 Distance moved: {distance_moved:.2f} meters')
            
            if distance_moved > 0.1:
                self.get_logger().info('✅ Robot movement SUCCESSFUL!')
                return True
            else:
                self.get_logger().warn('❌ Robot did not move significantly')
                return False
        
        return False
    
    def check_topics(self):
        """Check if all required topics are available"""
        self.get_logger().info('🔍 Checking topics...')
        
        topic_names = self.get_topic_names_and_types()
        required_topics = ['/cmd_vel', '/cmd_vel_teleop', '/odom', '/camera/image_raw', '/scan']
        
        for topic in required_topics:
            if any(topic in name for name, _ in topic_names):
                self.get_logger().info(f'✅ {topic}')
            else:
                self.get_logger().warn(f'❌ {topic} - MISSING')

def main():
    rclpy.init()
    checker = RobotStatusChecker()
    
    # Wait for initial data
    time.sleep(3)
    
    # Check topics
    checker.check_topics()
    
    # Test movement
    checker.test_movement()
    
    checker.get_logger().info('🎉 Status check complete!')
    checker.get_logger().info('💡 Use the xterm window with i/j/l/k keys to control the robot')
    checker.get_logger().info('👀 Check Gazebo and RViz windows to see the robot')
    
    rclpy.shutdown()

if __name__ == '__main__':
    main()