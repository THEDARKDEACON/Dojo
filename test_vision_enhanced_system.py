#!/usr/bin/env python3
"""
Test script for the vision enhanced system launch configuration.
Validates that all components can be launched and basic functionality works.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
from std_msgs.msg import String, Bool
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray
from nav_msgs.msg import OccupancyGrid
from diagnostic_msgs.msg import DiagnosticArray
import time
import threading
from typing import Dict, Set


class SystemTester(Node):
    """Test node for validating the vision enhanced system."""
    
    def __init__(self):
        super().__init__('system_tester')
        
        # Track received topics
        self.received_topics: Set[str] = set()
        self.topic_lock = threading.Lock()
        
        # Expected topics based on system configuration
        self.expected_topics = {
            '/camera/image_raw',
            '/camera/detection_image', 
            '/detections',
            '/map',
            '/system/status',
            '/system/health',
            '/system/startup_complete'
        }
        
        # Create subscribers for all expected topics
        qos_profile = QoSProfile(depth=1, reliability=QoSReliabilityPolicy.BEST_EFFORT)
        
        self.subscribers = [
            self.create_subscription(Image, '/camera/image_raw', 
                                   lambda msg: self._topic_received('/camera/image_raw'), qos_profile),
            self.create_subscription(Image, '/camera/detection_image',
                                   lambda msg: self._topic_received('/camera/detection_image'), qos_profile),
            self.create_subscription(Detection2DArray, '/detections',
                                   lambda msg: self._topic_received('/detections'), qos_profile),
            self.create_subscription(OccupancyGrid, '/map',
                                   lambda msg: self._topic_received('/map'), qos_profile),
            self.create_subscription(String, '/system/status',
                                   lambda msg: self._topic_received('/system/status'), qos_profile),
            self.create_subscription(DiagnosticArray, '/system/health',
                                   lambda msg: self._topic_received('/system/health'), qos_profile),
            self.create_subscription(Bool, '/system/startup_complete',
                                   lambda msg: self._startup_complete_callback(msg), qos_profile),
        ]
        
        # Test state
        self.test_start_time = time.time()
        self.startup_complete = False
        self.test_timeout = 60.0  # 60 seconds timeout
        
        # Test timer
        self.test_timer = self.create_timer(5.0, self._test_progress_callback)
        
        self.get_logger().info('System tester started - waiting for system components...')
    
    def _topic_received(self, topic_name: str) -> None:
        """Callback when a topic message is received."""
        with self.topic_lock:
            if topic_name not in self.received_topics:
                self.received_topics.add(topic_name)
                self.get_logger().info(f'Received first message on topic: {topic_name}')
    
    def _startup_complete_callback(self, msg: Bool) -> None:
        """Callback for startup complete signal."""
        if msg.data and not self.startup_complete:
            self.startup_complete = True
            elapsed_time = time.time() - self.test_start_time
            self.get_logger().info(f'System startup completed in {elapsed_time:.1f}s')
            
            # Schedule final test evaluation
            self.create_timer(10.0, self._final_evaluation)
    
    def _test_progress_callback(self) -> None:
        """Periodic test progress callback."""
        elapsed_time = time.time() - self.test_start_time
        
        with self.topic_lock:
            received_count = len(self.received_topics)
            expected_count = len(self.expected_topics)
            
            self.get_logger().info(
                f'Test progress ({elapsed_time:.1f}s): {received_count}/{expected_count} topics active, '
                f'Startup complete: {self.startup_complete}'
            )
            
            # List missing topics
            missing_topics = self.expected_topics - self.received_topics
            if missing_topics:
                self.get_logger().info(f'Missing topics: {list(missing_topics)}')
        
        # Check for timeout
        if elapsed_time > self.test_timeout:
            self.get_logger().error(f'Test timeout after {self.test_timeout}s')
            self._final_evaluation()
    
    def _final_evaluation(self) -> None:
        """Perform final test evaluation."""
        self.test_timer.cancel()
        
        with self.topic_lock:
            received_count = len(self.received_topics)
            expected_count = len(self.expected_topics)
            missing_topics = self.expected_topics - self.received_topics
        
        elapsed_time = time.time() - self.test_start_time
        
        # Generate test report
        self.get_logger().info('=== SYSTEM TEST REPORT ===')
        self.get_logger().info(f'Test duration: {elapsed_time:.1f}s')
        self.get_logger().info(f'Startup completed: {self.startup_complete}')
        self.get_logger().info(f'Topics active: {received_count}/{expected_count}')
        
        if missing_topics:
            self.get_logger().warn(f'Missing topics: {list(missing_topics)}')
        
        # Determine test result
        if self.startup_complete and received_count >= expected_count * 0.8:  # 80% success threshold
            self.get_logger().info('✓ SYSTEM TEST PASSED')
            test_result = 'PASSED'
        else:
            self.get_logger().error('✗ SYSTEM TEST FAILED')
            test_result = 'FAILED'
        
        self.get_logger().info(f'Test result: {test_result}')
        self.get_logger().info('=== END TEST REPORT ===')
        
        # Shutdown after reporting
        self.create_timer(2.0, lambda: rclpy.shutdown())


def main(args=None):
    """Main entry point for system tester."""
    rclpy.init(args=args)
    
    tester = SystemTester()
    
    try:
        rclpy.spin(tester)
    except KeyboardInterrupt:
        tester.get_logger().info('System tester interrupted by user')
    finally:
        tester.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()