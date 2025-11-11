#!/usr/bin/env python3
"""
Test script for performance monitoring and resource management integration.

This script tests the performance monitoring and resource management features
of the vision detection node.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray
from diagnostic_msgs.msg import DiagnosticArray
import cv2
import numpy as np
from cv_bridge import CvBridge
import time


class PerformanceTestNode(Node):
    """Test node for performance monitoring functionality."""
    
    def __init__(self):
        super().__init__('performance_test_node')
        
        self.bridge = CvBridge()
        
        # Publishers
        self.image_publisher = self.create_publisher(
            Image,
            '/camera/image_raw',
            10
        )
        
        # Subscribers
        self.detection_subscriber = self.create_subscription(
            Detection2DArray,
            '/detections',
            self.detection_callback,
            10
        )
        
        self.diagnostic_subscriber = self.create_subscription(
            DiagnosticArray,
            '/diagnostics',
            self.diagnostic_callback,
            10
        )
        
        # Test state
        self.detections_received = 0
        self.diagnostics_received = 0
        self.start_time = time.time()
        
        # Timer to publish test images
        self.timer = self.create_timer(0.1, self.publish_test_image)  # 10 FPS
        
        self.get_logger().info('Performance Test Node started')
    
    def publish_test_image(self):
        """Publish a test image to trigger detection processing."""
        # Create a simple test image
        height, width = 480, 640
        test_image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add some visual elements to make detection interesting
        cv2.rectangle(test_image, (100, 100), (200, 200), (0, 255, 0), -1)
        cv2.circle(test_image, (400, 300), 50, (255, 0, 0), -1)
        
        # Add frame counter
        frame_text = f'Frame {int((time.time() - self.start_time) * 10)}'
        cv2.putText(test_image, frame_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Convert to ROS message
        try:
            image_msg = self.bridge.cv2_to_imgmsg(test_image, encoding='bgr8')
            image_msg.header.stamp = self.get_clock().now().to_msg()
            image_msg.header.frame_id = 'camera_optical_frame'
            
            self.image_publisher.publish(image_msg)
            
        except Exception as e:
            self.get_logger().error(f'Error publishing test image: {e}')
    
    def detection_callback(self, msg):
        """Handle detection results."""
        self.detections_received += 1
        
        if self.detections_received % 10 == 0:
            self.get_logger().info(f'Received {self.detections_received} detection messages')
    
    def diagnostic_callback(self, msg):
        """Handle diagnostic messages."""
        self.diagnostics_received += 1
        
        # Look for vision detection performance diagnostics
        for status in msg.status:
            if status.name == 'vision_detection_performance':
                # Extract performance metrics
                metrics = {}
                for kv in status.values:
                    metrics[kv.key] = kv.value
                
                if self.diagnostics_received % 3 == 0:  # Log every 3rd diagnostic
                    self.get_logger().info(
                        f'Performance Metrics - '
                        f'FPS: {metrics.get("frame_rate_fps", "N/A")}, '
                        f'CPU: {metrics.get("cpu_usage_percent", "N/A")}%, '
                        f'Memory: {metrics.get("memory_usage_mb", "N/A")}MB, '
                        f'Status: {status.message}'
                    )


def main(args=None):
    """Main function for performance test."""
    rclpy.init(args=args)
    
    try:
        node = PerformanceTestNode()
        
        # Run for 30 seconds
        start_time = time.time()
        while rclpy.ok() and (time.time() - start_time) < 30.0:
            rclpy.spin_once(node, timeout_sec=0.1)
        
        # Print final statistics
        node.get_logger().info(
            f'Test completed - Detections received: {node.detections_received}, '
            f'Diagnostics received: {node.diagnostics_received}'
        )
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'Error in performance test: {e}')
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()