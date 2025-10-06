#!/usr/bin/env python3
"""
Test script for map display functionality
Verifies that map visualization components are working correctly
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
from diagnostic_msgs.msg import DiagnosticArray
import time

class MapDisplayTester(Node):
    def __init__(self):
        super().__init__('map_display_tester')
        
        # Subscribers to monitor system status
        self.map_subscriber = self.create_subscription(
            OccupancyGrid,
            '/map',
            self.map_callback,
            10
        )
        
        self.diagnostic_subscriber = self.create_subscription(
            DiagnosticArray,
            '/diagnostics',
            self.diagnostic_callback,
            10
        )
        
        # Test state
        self.map_received = False
        self.diagnostics_received = False
        self.test_start_time = time.time()
        
        # Timer for test completion
        self.test_timer = self.create_timer(10.0, self.complete_test)
        
        self.get_logger().info('Map display test started - monitoring for 10 seconds...')
    
    def map_callback(self, msg):
        """Handle map messages."""
        if not self.map_received:
            self.get_logger().info(
                f'✓ Map received: {msg.info.width}x{msg.info.height} '
                f'at {msg.info.resolution:.3f}m/cell, frame: {msg.header.frame_id}'
            )
            self.map_received = True
    
    def diagnostic_callback(self, msg):
        """Handle diagnostic messages."""
        if not self.diagnostics_received:
            self.get_logger().info(f'✓ Diagnostics received: {len(msg.status)} status messages')
            
            for status in msg.status:
                if 'Map' in status.name or 'Frame' in status.name:
                    level_str = ['OK', 'WARN', 'ERROR'][status.level]
                    self.get_logger().info(f'  - {status.name}: {level_str} - {status.message}')
            
            self.diagnostics_received = True
    
    def complete_test(self):
        """Complete the test and report results."""
        elapsed_time = time.time() - self.test_start_time
        
        self.get_logger().info(f'\n=== Map Display Test Results (after {elapsed_time:.1f}s) ===')
        
        if self.map_received:
            self.get_logger().info('✓ Map topic is working correctly')
        else:
            self.get_logger().warn('✗ No map data received - check SLAM configuration')
        
        if self.diagnostics_received:
            self.get_logger().info('✓ Diagnostic system is working correctly')
        else:
            self.get_logger().warn('✗ No diagnostics received - check diagnostic nodes')
        
        # Overall test result
        if self.map_received and self.diagnostics_received:
            self.get_logger().info('🎉 Map display system test PASSED')
        else:
            self.get_logger().warn('⚠️  Map display system test INCOMPLETE - some components not responding')
        
        self.get_logger().info('Test completed. You can now check RViz for proper map visualization.')
        
        # Shutdown
        rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    tester = MapDisplayTester()
    
    try:
        rclpy.spin(tester)
    except KeyboardInterrupt:
        pass
    finally:
        tester.destroy_node()

if __name__ == '__main__':
    main()