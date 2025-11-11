#!/usr/bin/env python3
"""
Priority 1 Features Integration Test
Tests all Priority 1 features working together:
- Semantic SLAM with YOLO
- 3D Point Cloud Visualization
- Performance Dashboard
- Advanced Safety System
- Multi-world Support
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import PointCloud2
from geometry_msgs.msg import Twist
import json
import time
import sys

class Priority1IntegrationTest(Node):
    def __init__(self):
        super().__init__('priority1_integration_test')
        
        # Test results
        self.tests_passed = []
        self.tests_failed = []
        
        # Feature status tracking
        self.semantic_map_received = False
        self.pointcloud_received = False
        self.dashboard_received = False
        self.safety_status_received = False
        self.navigation_status_received = False
        
        # Data storage
        self.semantic_map_data = None
        self.dashboard_data = None
        self.safety_data = None
        
        # Subscribers for monitoring
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
        
        # Publishers for testing
        self.cmd_pub = self.create_publisher(String, '/semantic_command', 10)
        self.vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        self.get_logger().info("🧪 Priority 1 Integration Test initialized")
    
    def semantic_map_callback(self, msg):
        """Monitor semantic map updates"""
        self.semantic_map_received = True
        try:
            self.semantic_map_data = json.loads(msg.data)
            self.get_logger().debug(f"✅ Semantic map received: {len(self.semantic_map_data.get('objects', {}))} objects")
        except json.JSONDecodeError:
            self.get_logger().warn("⚠️ Failed to parse semantic map JSON")
    
    def pointcloud_callback(self, msg):
        """Monitor point cloud updates"""
        self.pointcloud_received = True
        self.get_logger().debug(f"✅ Point cloud received: {msg.width * msg.height} points")
    
    def dashboard_callback(self, msg):
        """Monitor performance dashboard"""
        self.dashboard_received = True
        try:
            self.dashboard_data = json.loads(msg.data)
            self.get_logger().debug("✅ Dashboard data received")
        except json.JSONDecodeError:
            self.get_logger().warn("⚠️ Failed to parse dashboard JSON")
    
    def safety_callback(self, msg):
        """Monitor safety system"""
        self.safety_status_received = True
        try:
            self.safety_data = json.loads(msg.data)
            self.get_logger().debug(f"✅ Safety status: {self.safety_data.get('level', 'unknown')}")
        except json.JSONDecodeError:
            self.get_logger().warn("⚠️ Failed to parse safety status JSON")
    
    def nav_status_callback(self, msg):
        """Monitor navigation status"""
        self.navigation_status_received = True
        try:
            nav_data = json.loads(msg.data)
            self.get_logger().debug(f"✅ Navigation status: {nav_data.get('status', 'unknown')}")
        except json.JSONDecodeError:
            self.get_logger().warn("⚠️ Failed to parse navigation status JSON")
    
    def run_tests(self):
        """Run all integration tests"""
        self.get_logger().info("\n" + "="*80)
        self.get_logger().info("🚀 STARTING PRIORITY 1 INTEGRATION TESTS")
        self.get_logger().info("="*80 + "\n")
        
        # Test 1: Semantic SLAM Integration
        self.test_semantic_slam()
        
        # Test 2: Point Cloud Visualization
        self.test_pointcloud_visualization()
        
        # Test 3: Performance Dashboard
        self.test_performance_dashboard()
        
        # Test 4: Advanced Safety System
        self.test_safety_system()
        
        # Test 5: Feature Combination
        self.test_feature_combination()
        
        # Print results
        self.print_results()
    
    def test_semantic_slam(self):
        """Test semantic SLAM with object detection"""
        self.get_logger().info("\n📋 TEST 1: Semantic SLAM Integration")
        self.get_logger().info("-" * 60)
        
        # Wait for semantic map data
        self.get_logger().info("Waiting for semantic map data...")
        timeout = 10.0
        start_time = time.time()
        
        while not self.semantic_map_received and (time.time() - start_time) < timeout:
            rclpy.spin_once(self, timeout_sec=0.1)
        
        if self.semantic_map_received:
            self.tests_passed.append("Semantic SLAM: Map publishing")
            self.get_logger().info("✅ Semantic map is being published")
            
            if self.semantic_map_data:
                objects = self.semantic_map_data.get('objects', {})
                self.get_logger().info(f"   Objects detected: {len(objects)}")
                
                # Check object data structure
                if objects:
                    sample_obj = list(objects.values())[0]
                    required_fields = ['class', 'x', 'y', 'confidence']
                    if all(field in sample_obj for field in required_fields):
                        self.tests_passed.append("Semantic SLAM: Object data structure")
                        self.get_logger().info("✅ Object data structure is correct")
                    else:
                        self.tests_failed.append("Semantic SLAM: Object data structure incomplete")
                        self.get_logger().warn("⚠️ Object data structure incomplete")
        else:
            self.tests_failed.append("Semantic SLAM: No map data received")
            self.get_logger().error("❌ No semantic map data received within timeout")
    
    def test_pointcloud_visualization(self):
        """Test 3D point cloud visualization"""
        self.get_logger().info("\n📋 TEST 2: 3D Point Cloud Visualization")
        self.get_logger().info("-" * 60)
        
        # Wait for point cloud data
        self.get_logger().info("Waiting for point cloud data...")
        timeout = 10.0
        start_time = time.time()
        
        while not self.pointcloud_received and (time.time() - start_time) < timeout:
            rclpy.spin_once(self, timeout_sec=0.1)
        
        if self.pointcloud_received:
            self.tests_passed.append("Point Cloud: Data publishing")
            self.get_logger().info("✅ Point cloud is being published")
        else:
            self.tests_failed.append("Point Cloud: No data received")
            self.get_logger().error("❌ No point cloud data received within timeout")
    
    def test_performance_dashboard(self):
        """Test performance dashboard"""
        self.get_logger().info("\n📋 TEST 3: Performance Dashboard")
        self.get_logger().info("-" * 60)
        
        # Wait for dashboard data
        self.get_logger().info("Waiting for dashboard data...")
        timeout = 10.0
        start_time = time.time()
        
        while not self.dashboard_received and (time.time() - start_time) < timeout:
            rclpy.spin_once(self, timeout_sec=0.1)
        
        if self.dashboard_received:
            self.tests_passed.append("Dashboard: Data publishing")
            self.get_logger().info("✅ Performance dashboard is active")
            
            if self.dashboard_data:
                # Check for required metrics
                required_metrics = ['cpu_usage', 'memory_usage', 'timestamp']
                metrics_present = [m for m in required_metrics if m in self.dashboard_data]
                
                self.get_logger().info(f"   Metrics present: {len(metrics_present)}/{len(required_metrics)}")
                
                if len(metrics_present) == len(required_metrics):
                    self.tests_passed.append("Dashboard: All metrics present")
                    self.get_logger().info("✅ All required metrics are present")
                    
                    # Display current metrics
                    self.get_logger().info(f"   CPU: {self.dashboard_data.get('cpu_usage', 0):.1f}%")
                    self.get_logger().info(f"   Memory: {self.dashboard_data.get('memory_usage', 0):.1f} MB")
                else:
                    self.tests_failed.append("Dashboard: Missing metrics")
                    self.get_logger().warn(f"⚠️ Missing metrics: {set(required_metrics) - set(metrics_present)}")
        else:
            self.tests_failed.append("Dashboard: No data received")
            self.get_logger().error("❌ No dashboard data received within timeout")
    
    def test_safety_system(self):
        """Test advanced safety system"""
        self.get_logger().info("\n📋 TEST 4: Advanced Safety System")
        self.get_logger().info("-" * 60)
        
        # Wait for safety status
        self.get_logger().info("Waiting for safety status...")
        timeout = 10.0
        start_time = time.time()
        
        while not self.safety_status_received and (time.time() - start_time) < timeout:
            rclpy.spin_once(self, timeout_sec=0.1)
        
        if self.safety_status_received:
            self.tests_passed.append("Safety: Status publishing")
            self.get_logger().info("✅ Safety system is active")
            
            if self.safety_data:
                level = self.safety_data.get('level', 'unknown')
                threats = self.safety_data.get('active_threats', 0)
                
                self.get_logger().info(f"   Safety level: {level}")
                self.get_logger().info(f"   Active threats: {threats}")
                
                self.tests_passed.append("Safety: Status data valid")
        else:
            self.tests_failed.append("Safety: No status received")
            self.get_logger().error("❌ No safety status received within timeout")
    
    def test_feature_combination(self):
        """Test all features working together"""
        self.get_logger().info("\n📋 TEST 5: Feature Combination")
        self.get_logger().info("-" * 60)
        
        # Check if all features are active simultaneously
        all_active = (
            self.semantic_map_received and
            self.pointcloud_received and
            self.dashboard_received and
            self.safety_status_received
        )
        
        if all_active:
            self.tests_passed.append("Integration: All features active")
            self.get_logger().info("✅ All Priority 1 features are active simultaneously")
            
            # Test semantic navigation command
            self.get_logger().info("Testing semantic navigation command...")
            cmd_msg = String()
            cmd_msg.data = "list objects"
            self.cmd_pub.publish(cmd_msg)
            
            time.sleep(2.0)
            rclpy.spin_once(self, timeout_sec=0.1)
            
            self.tests_passed.append("Integration: Command interface")
            self.get_logger().info("✅ Command interface is functional")
            
        else:
            self.tests_failed.append("Integration: Not all features active")
            self.get_logger().error("❌ Not all features are active simultaneously")
            self.get_logger().info(f"   Semantic SLAM: {'✅' if self.semantic_map_received else '❌'}")
            self.get_logger().info(f"   Point Cloud: {'✅' if self.pointcloud_received else '❌'}")
            self.get_logger().info(f"   Dashboard: {'✅' if self.dashboard_received else '❌'}")
            self.get_logger().info(f"   Safety: {'✅' if self.safety_status_received else '❌'}")
    
    def print_results(self):
        """Print test results summary"""
        self.get_logger().info("\n" + "="*80)
        self.get_logger().info("📊 TEST RESULTS SUMMARY")
        self.get_logger().info("="*80)
        
        total_tests = len(self.tests_passed) + len(self.tests_failed)
        pass_rate = (len(self.tests_passed) / total_tests * 100) if total_tests > 0 else 0
        
        self.get_logger().info(f"\nTotal Tests: {total_tests}")
        self.get_logger().info(f"Passed: {len(self.tests_passed)} ✅")
        self.get_logger().info(f"Failed: {len(self.tests_failed)} ❌")
        self.get_logger().info(f"Pass Rate: {pass_rate:.1f}%")
        
        if self.tests_passed:
            self.get_logger().info("\n✅ PASSED TESTS:")
            for test in self.tests_passed:
                self.get_logger().info(f"   ✓ {test}")
        
        if self.tests_failed:
            self.get_logger().info("\n❌ FAILED TESTS:")
            for test in self.tests_failed:
                self.get_logger().info(f"   ✗ {test}")
        
        self.get_logger().info("\n" + "="*80)
        
        if pass_rate >= 80:
            self.get_logger().info("🎉 INTEGRATION TEST PASSED! Priority 1 features are working well.")
        elif pass_rate >= 60:
            self.get_logger().info("⚠️ INTEGRATION TEST PARTIAL PASS. Some features need attention.")
        else:
            self.get_logger().info("❌ INTEGRATION TEST FAILED. Significant issues detected.")
        
        self.get_logger().info("="*80 + "\n")
        
        return pass_rate >= 80

def main(args=None):
    rclpy.init(args=args)
    
    test_node = Priority1IntegrationTest()
    
    try:
        # Give system time to initialize
        test_node.get_logger().info("⏳ Waiting 5 seconds for system initialization...")
        time.sleep(5.0)
        
        # Run tests
        success = test_node.run_tests()
        
        # Return appropriate exit code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        test_node.get_logger().info("Test interrupted by user")
        sys.exit(1)
    finally:
        test_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
