#!/usr/bin/env python3
"""
System Monitor - Tracks Priority 1 feature integration status
Monitors all features and reports system health
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import PointCloud2
import json
import time
from datetime import datetime

class SystemMonitor(Node):
    def __init__(self):
        super().__init__('system_monitor')
        
        # Feature status tracking
        self.features = {
            'semantic_slam': {'active': False, 'last_update': None, 'message_count': 0},
            'pointcloud': {'active': False, 'last_update': None, 'message_count': 0},
            'dashboard': {'active': False, 'last_update': None, 'message_count': 0},
            'safety': {'active': False, 'last_update': None, 'message_count': 0},
            'navigation': {'active': False, 'last_update': None, 'message_count': 0},
        }
        
        # Subscribers to monitor features
        self.semantic_map_sub = self.create_subscription(
            String, '/semantic_map', self.semantic_map_callback, 10)
        
        self.pointcloud_sub = self.create_subscription(
            PointCloud2, '/pointcloud', self.pointcloud_callback, 10)
        
        self.dashboard_sub = self.create_subscription(
            String, '/performance_metrics', self.dashboard_callback, 10)
        
        self.safety_sub = self.create_subscription(
            String, '/safety_status', self.safety_callback, 10)
        
        self.nav_status_sub = self.create_subscription(
            String, '/navigation_status', self.nav_status_callback, 10)
        
        # Publisher for system status
        self.status_pub = self.create_publisher(String, '/system_status', 10)
        
        # Timer for periodic status reports
        self.report_timer = self.create_timer(10.0, self.publish_status_report)
        
        # Startup time
        self.startup_time = time.time()
        
        self.get_logger().info("🔍 System Monitor initialized - tracking Priority 1 features")
    
    def semantic_map_callback(self, msg):
        """Track semantic SLAM activity"""
        self.features['semantic_slam']['active'] = True
        self.features['semantic_slam']['last_update'] = time.time()
        self.features['semantic_slam']['message_count'] += 1
    
    def pointcloud_callback(self, msg):
        """Track point cloud visualization activity"""
        self.features['pointcloud']['active'] = True
        self.features['pointcloud']['last_update'] = time.time()
        self.features['pointcloud']['message_count'] += 1
    
    def dashboard_callback(self, msg):
        """Track performance dashboard activity"""
        self.features['dashboard']['active'] = True
        self.features['dashboard']['last_update'] = time.time()
        self.features['dashboard']['message_count'] += 1
    
    def safety_callback(self, msg):
        """Track safety system activity"""
        self.features['safety']['active'] = True
        self.features['safety']['last_update'] = time.time()
        self.features['safety']['message_count'] += 1
    
    def nav_status_callback(self, msg):
        """Track navigation activity"""
        self.features['navigation']['active'] = True
        self.features['navigation']['last_update'] = time.time()
        self.features['navigation']['message_count'] += 1
    
    def publish_status_report(self):
        """Publish periodic status report"""
        current_time = time.time()
        uptime = current_time - self.startup_time
        
        # Check feature health (consider inactive if no update in last 5 seconds)
        timeout = 5.0
        for feature_name, feature_data in self.features.items():
            if feature_data['last_update']:
                time_since_update = current_time - feature_data['last_update']
                if time_since_update > timeout:
                    feature_data['active'] = False
        
        # Count active features
        active_count = sum(1 for f in self.features.values() if f['active'])
        total_features = len(self.features)
        
        # Create status report
        status_report = {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': uptime,
            'features': {
                name: {
                    'active': data['active'],
                    'message_count': data['message_count'],
                    'last_update': data['last_update']
                }
                for name, data in self.features.items()
            },
            'summary': {
                'active_features': active_count,
                'total_features': total_features,
                'health_percentage': (active_count / total_features) * 100 if total_features > 0 else 0
            }
        }
        
        # Publish status
        status_msg = String()
        status_msg.data = json.dumps(status_report)
        self.status_pub.publish(status_msg)
        
        # Log summary
        health = status_report['summary']['health_percentage']
        if health >= 80:
            status_icon = "✅"
            status_text = "HEALTHY"
        elif health >= 60:
            status_icon = "⚠️"
            status_text = "DEGRADED"
        else:
            status_icon = "❌"
            status_text = "CRITICAL"
        
        self.get_logger().info(
            f"{status_icon} System Status: {status_text} "
            f"({active_count}/{total_features} features active, {health:.0f}% health)"
        )
        
        # Log individual feature status
        for feature_name, feature_data in self.features.items():
            icon = "✅" if feature_data['active'] else "❌"
            count = feature_data['message_count']
            self.get_logger().debug(f"  {icon} {feature_name}: {count} messages")

def main(args=None):
    rclpy.init(args=args)
    
    monitor = SystemMonitor()
    
    try:
        rclpy.spin(monitor)
    except KeyboardInterrupt:
        monitor.get_logger().info("System Monitor shutting down")
    finally:
        monitor.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
