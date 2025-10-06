#!/usr/bin/env python3
"""
Test script for enhanced camera driver with dual-topic support.
This script tests the camera driver functionality without requiring actual hardware.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from std_msgs.msg import String
import time


class CameraDriverTester(Node):
    """Test node for camera driver functionality."""
    
    def __init__(self):
        super().__init__('camera_driver_tester')
        
        # Track received messages
        self.received_messages = {
            'image_raw': 0,
            'detection_input': 0,
            'camera_info': 0,
            'diagnostics': 0
        }
        
        # Subscribers for camera topics
        self.image_sub = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10
        )
        
        self.detection_input_sub = self.create_subscription(
            Image,
            '/camera/detection_input',
            self.detection_input_callback,
            10
        )
        
        self.camera_info_sub = self.create_subscription(
            CameraInfo,
            '/camera/camera_info',
            self.camera_info_callback,
            10
        )
        
        self.diagnostics_sub = self.create_subscription(
            String,
            '/camera/diagnostics',
            self.diagnostics_callback,
            10
        )
        
        # Timer to report statistics
        self.stats_timer = self.create_timer(5.0, self.report_stats)
        
        self.get_logger().info('Camera driver tester initialized')
    
    def image_callback(self, msg):
        """Handle raw image messages."""
        self.received_messages['image_raw'] += 1
        self.get_logger().debug(f'Received raw image: {msg.header.stamp}')
    
    def detection_input_callback(self, msg):
        """Handle detection input messages."""
        self.received_messages['detection_input'] += 1
        self.get_logger().debug(f'Received detection input: {msg.header.stamp}')
    
    def camera_info_callback(self, msg):
        """Handle camera info messages."""
        self.received_messages['camera_info'] += 1
        self.get_logger().debug(f'Received camera info: {msg.header.stamp}')
    
    def diagnostics_callback(self, msg):
        """Handle diagnostics messages."""
        self.received_messages['diagnostics'] += 1
        self.get_logger().info(f'Camera diagnostics: {msg.data}')
    
    def report_stats(self):
        """Report message reception statistics."""
        self.get_logger().info('=== Camera Driver Test Statistics ===')
        for topic, count in self.received_messages.items():
            self.get_logger().info(f'{topic}: {count} messages received')
        
        # Check if dual-topic publishing is working
        if (self.received_messages['image_raw'] > 0 and 
            self.received_messages['detection_input'] > 0):
            self.get_logger().info('✓ Dual-topic publishing is working!')
        else:
            self.get_logger().warning('✗ Dual-topic publishing may not be working')
        
        # Check timestamp synchronization (basic check)
        if (self.received_messages['image_raw'] > 0 and 
            self.received_messages['detection_input'] > 0 and
            abs(self.received_messages['image_raw'] - self.received_messages['detection_input']) <= 1):
            self.get_logger().info('✓ Topics appear to be synchronized')
        else:
            self.get_logger().warning('✗ Topic synchronization may have issues')


def main(args=None):
    """Main function."""
    rclpy.init(args=args)
    
    try:
        tester = CameraDriverTester()
        
        # Run for 30 seconds
        start_time = time.time()
        while rclpy.ok() and (time.time() - start_time) < 30.0:
            rclpy.spin_once(tester, timeout_sec=0.1)
        
        # Final report
        tester.get_logger().info('=== Final Test Report ===')
        tester.report_stats()
        
    except KeyboardInterrupt:
        pass
    finally:
        if 'tester' in locals():
            tester.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()