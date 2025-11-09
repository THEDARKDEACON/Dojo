#!/usr/bin/env python3
"""
Start Autonomous Movement Script
Simple script to start autonomous movement immediately after launch.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
import time
import math
import random

class StartAutonomousMovement(Node):
    def __init__(self):
        super().__init__('start_autonomous_movement')
        
        # Publisher for autonomous movement
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel_autonomous', 10)
        
        # Subscriber for obstacle detection
        self.scan_sub = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10
        )
        
        # Movement state
        self.obstacle_detected = False
        self.movement_pattern = 0
        self.pattern_start_time = time.time()
        
        # Timer for movement commands
        self.movement_timer = self.create_timer(0.2, self.send_movement_command)
        
        self.get_logger().info("🚀 Starting autonomous movement for mapping...")
    
    def scan_callback(self, msg):
        """Simple obstacle detection"""
        if len(msg.ranges) > 0:
            # Check front 60 degrees for obstacles
            front_ranges = msg.ranges[-30:] + msg.ranges[:30]
            min_distance = min([r for r in front_ranges if r > 0.1])
            self.obstacle_detected = min_distance < 1.0
    
    def send_movement_command(self):
        """Send movement commands based on simple patterns"""
        twist = Twist()
        current_time = time.time()
        
        if self.obstacle_detected:
            # Turn when obstacle detected
            twist.linear.x = 0.0
            twist.angular.z = 0.5
            self.get_logger().info("🚧 Obstacle detected, turning...")
        else:
            # Movement patterns for exploration
            elapsed = current_time - self.pattern_start_time
            
            if self.movement_pattern == 0:  # Move forward
                twist.linear.x = 0.3
                twist.angular.z = 0.0
                if elapsed > 4.0:
                    self.movement_pattern = 1
                    self.pattern_start_time = current_time
            
            elif self.movement_pattern == 1:  # Turn
                twist.linear.x = 0.0
                twist.angular.z = 0.4
                if elapsed > 2.0:
                    self.movement_pattern = 2
                    self.pattern_start_time = current_time
            
            elif self.movement_pattern == 2:  # Move forward and turn slightly
                twist.linear.x = 0.25
                twist.angular.z = 0.1
                if elapsed > 3.0:
                    self.movement_pattern = 3
                    self.pattern_start_time = current_time
            
            elif self.movement_pattern == 3:  # Exploration turn
                twist.linear.x = 0.1
                twist.angular.z = -0.3
                if elapsed > 2.5:
                    self.movement_pattern = 0
                    self.pattern_start_time = current_time
        
        # Publish movement command
        self.cmd_pub.publish(twist)

def main():
    rclpy.init()
    
    try:
        node = StartAutonomousMovement()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()