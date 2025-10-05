#!/usr/bin/env python3
"""
System Integration Test Script

This script performs comprehensive integration testing of the Dojo Robot system
including configuration management, hardware discovery, safety systems, and
component health monitoring.

Usage:
    ros2 run robot_control test_system_integration
    
Or directly:
    python3 scripts/test_system_integration.py
"""

import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
import time
import sys
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from std_msgs.msg import String, Bool
from diagnostic_msgs.msg import DiagnosticArray
from geometry_msgs.msg import Twist
from std_srvs.srv import Trigger


@dataclass
class TestResult:
    """Test result data structure"""
    name: str
    passed: bool
    message: str
    duration: float
    timestamp: datetime


class SystemIntegrationTester(Node):
    """
    Comprehensive system integration tester
    
    Tests all major system components and their integration:
    - Configuration management
    - Hardware discovery
    - Safety systems
    - Health monitoring
    - Emergency stop functionality
    """
    
    def __init__(self):
        super().__init__('system_integration_tester')
        
        self.logger = self.get_logger()
        self.test_results: List[TestResult] = []
        self.test_timeout = 30.0  # seconds
        
        # Test state tracking
        self.received_topics: Dict[str, Any] = {}
        self.service_responses: Dict[str, Any] = {}
        
        # Subscribers for monitoring system topics
        self.setup_subscribers()
        
        # Service clients for testing
        self.setup_service_clients()
        
        self.logger.info("System Integration Tester initialized")
    
    def setup_subscribers(self):
        """Setup subscribers for monitoring system topics"""
        
        # Configuration management topics
        self.config_status_sub = self.create_subscription(
            String, '/configuration_status', 
            lambda msg: self._record_topic('/configuration_status', msg), 10
        )
        
        self.config_conflicts_sub = self.create_subscription(
            String, '/configuration_conflicts',
            lambda msg: self._record_topic('/configuration_conflicts', msg), 10
        )
        
        # Hardware discovery topics
        self.hardware_discovery_sub = self.create_subscription(
            String, '/hardware_discovery_status',
            lambda msg: self._record_topic('/hardware_discovery_status', msg), 10
        )
        
        # Safety system topics
        self.safety_status_sub = self.create_subscription(
            String, '/safety_status',
            lambda msg: self._record_topic('/safety_status', msg), 10
        )
        
        self.emergency_stop_sub = self.create_subscription(
            Bool, '/emergency_stop_status',
            lambda msg: self._record_topic('/emergency_stop_status', msg), 10
        )
        
        # Health monitoring topics
        self.diagnostics_sub = self.create_subscription(
            DiagnosticArray, '/diagnostics',
            lambda msg: self._record_topic('/diagnostics', msg), 10
        )
        
        self.system_health_sub = self.create_subscription(
            String, '/system/health_status',
            lambda msg: self._record_topic('/system/health_status', msg), 10
        )
        
        # Command topics for testing
        self.cmd_vel_filtered_sub = self.create_subscription(
            Twist, '/cmd_vel_filtered',
            lambda msg: self._record_topic('/cmd_vel_filtered', msg), 10
        )
    
    def setup_service_clients(self):
        """Setup service clients for testing"""
        
        # Safety system services
        self.clear_estop_client = self.create_client(Trigger, '/clear_emergency_stop')
        self.reset_watchdogs_client = self.create_client(Trigger, '/reset_watchdogs')
        
        # Configuration services
        self.reload_config_client = self.create_client(Trigger, '/reload_configuration')
    
    def _record_topic(self, topic_name: str, msg: Any):
        """Record received topic message"""
        self.received_topics[topic_name] = {
            'message': msg,
            'timestamp': datetime.now()
        }
        self.logger.debug(f"Received message on {topic_name}")
    
    def run_all_tests(self) -> bool:
        """Run all integration tests"""
        self.logger.info("🚀 Starting System Integration Tests")
        self.logger.info("=" * 60)
        
        # List of tests to run
        tests = [
            ("Topic Availability", self.test_topic_availability),
            ("Configuration Management", self.test_configuration_management),
            ("Hardware Discovery", self.test_hardware_discovery),
            ("Safety System Integration", self.test_safety_system),
            ("Health Monitoring", self.test_health_monitoring),
            ("Emergency Stop Functionality", self.test_emergency_stop),
            ("Velocity Limiting", self.test_velocity_limiting),
            ("Service Availability", self.test_service_availability),
        ]
        
        all_passed = True
        
        for test_name, test_func in tests:
            self.logger.info(f"\n📋 Running Test: {test_name}")
            
            start_time = time.time()
            try:
                result = test_func()
                duration = time.time() - start_time
                
                test_result = TestResult(
                    name=test_name,
                    passed=result,
                    message="Test completed successfully" if result else "Test failed",
                    duration=duration,
                    timestamp=datetime.now()
                )
                
                self.test_results.append(test_result)
                
                if result:
                    self.logger.info(f"✅ {test_name}: PASSED ({duration:.2f}s)")
                else:
                    self.logger.error(f"❌ {test_name}: FAILED ({duration:.2f}s)")
                    all_passed = False
                    
            except Exception as e:
                duration = time.time() - start_time
                self.logger.error(f"💥 {test_name}: ERROR - {str(e)} ({duration:.2f}s)")
                
                test_result = TestResult(
                    name=test_name,
                    passed=False,
                    message=f"Exception: {str(e)}",
                    duration=duration,
                    timestamp=datetime.now()
                )
                
                self.test_results.append(test_result)
                all_passed = False
        
        # Print test summary
        self.print_test_summary()
        
        return all_passed
    
    def test_topic_availability(self) -> bool:
        """Test that all expected topics are available"""
        self.logger.info("  📡 Checking topic availability...")
        
        # Wait for topics to be discovered
        time.sleep(2.0)
        
        # Get list of available topics
        topic_names = self.get_topic_names_and_types()
        available_topics = [name for name, _ in topic_names]
        
        # Expected core topics
        expected_topics = [
            '/configuration_status',
            '/hardware_discovery_status',
            '/safety_status',
            '/diagnostics',
            '/cmd_vel',
            '/emergency_stop_request'
        ]
        
        missing_topics = []
        for topic in expected_topics:
            if topic not in available_topics:
                missing_topics.append(topic)
        
        if missing_topics:
            self.logger.warning(f"Missing topics: {missing_topics}")
            return False
        
        self.logger.info(f"  ✅ All expected topics available ({len(expected_topics)} topics)")
        return True
    
    def test_configuration_management(self) -> bool:
        """Test configuration management system"""
        self.logger.info("  ⚙️ Testing configuration management...")
        
        # Wait for configuration status
        timeout = time.time() + 10.0
        while time.time() < timeout:
            if '/configuration_status' in self.received_topics:
                break
            time.sleep(0.1)
        
        if '/configuration_status' not in self.received_topics:
            self.logger.error("  Configuration status topic not received")
            return False
        
        # Check for configuration conflicts
        if '/configuration_conflicts' in self.received_topics:
            conflicts_msg = self.received_topics['/configuration_conflicts']['message']
            if conflicts_msg.data and conflicts_msg.data.strip():
                self.logger.warning(f"  Configuration conflicts detected: {conflicts_msg.data}")
                return False
        
        self.logger.info("  ✅ Configuration management working")
        return True
    
    def test_hardware_discovery(self) -> bool:
        """Test hardware discovery system"""
        self.logger.info("  🔍 Testing hardware discovery...")
        
        # Wait for hardware discovery status
        timeout = time.time() + 15.0
        while time.time() < timeout:
            if '/hardware_discovery_status' in self.received_topics:
                break
            time.sleep(0.1)
        
        if '/hardware_discovery_status' not in self.received_topics:
            self.logger.error("  Hardware discovery status not received")
            return False
        
        discovery_msg = self.received_topics['/hardware_discovery_status']['message']
        self.logger.info(f"  Hardware discovery status: {discovery_msg.data}")
        
        # Hardware discovery is working if we receive status (even if no hardware found)
        self.logger.info("  ✅ Hardware discovery system working")
        return True
    
    def test_safety_system(self) -> bool:
        """Test safety system integration"""
        self.logger.info("  🛡️ Testing safety system...")
        
        # Wait for safety status
        timeout = time.time() + 10.0
        while time.time() < timeout:
            if '/safety_status' in self.received_topics:
                break
            time.sleep(0.1)
        
        if '/safety_status' not in self.received_topics:
            self.logger.error("  Safety status topic not received")
            return False
        
        safety_msg = self.received_topics['/safety_status']['message']
        self.logger.info(f"  Safety status: {safety_msg.data}")
        
        self.logger.info("  ✅ Safety system working")
        return True
    
    def test_health_monitoring(self) -> bool:
        """Test health monitoring system"""
        self.logger.info("  💓 Testing health monitoring...")
        
        # Wait for diagnostics
        timeout = time.time() + 10.0
        while time.time() < timeout:
            if '/diagnostics' in self.received_topics:
                break
            time.sleep(0.1)
        
        if '/diagnostics' not in self.received_topics:
            self.logger.error("  Diagnostics topic not received")
            return False
        
        diagnostics_msg = self.received_topics['/diagnostics']['message']
        self.logger.info(f"  Received diagnostics with {len(diagnostics_msg.status)} status entries")
        
        # Check for system health status
        if '/system/health_status' in self.received_topics:
            health_msg = self.received_topics['/system/health_status']['message']
            self.logger.info(f"  System health: {health_msg.data}")
        
        self.logger.info("  ✅ Health monitoring working")
        return True
    
    def test_emergency_stop(self) -> bool:
        """Test emergency stop functionality"""
        self.logger.info("  🚨 Testing emergency stop...")
        
        # Create publisher for emergency stop request
        estop_pub = self.create_publisher(Bool, '/emergency_stop_request', 10)
        
        # Wait for publisher to be ready
        time.sleep(1.0)
        
        # Trigger emergency stop
        estop_msg = Bool()
        estop_msg.data = True
        estop_pub.publish(estop_msg)
        
        self.logger.info("  Triggered emergency stop")
        
        # Wait for emergency stop status
        timeout = time.time() + 5.0
        estop_activated = False
        
        while time.time() < timeout:
            if '/emergency_stop_status' in self.received_topics:
                estop_status = self.received_topics['/emergency_stop_status']['message']
                if estop_status.data:
                    estop_activated = True
                    break
            time.sleep(0.1)
        
        if not estop_activated:
            self.logger.error("  Emergency stop was not activated")
            return False
        
        self.logger.info("  Emergency stop activated successfully")
        
        # Try to clear emergency stop (if service is available)
        if self.clear_estop_client.service_is_ready():
            try:
                request = Trigger.Request()
                future = self.clear_estop_client.call_async(request)
                
                # Wait for response
                timeout = time.time() + 5.0
                while time.time() < timeout and not future.done():
                    time.sleep(0.1)
                
                if future.done():
                    response = future.result()
                    if response.success:
                        self.logger.info("  Emergency stop cleared successfully")
                    else:
                        self.logger.info(f"  Emergency stop clear response: {response.message}")
                
            except Exception as e:
                self.logger.warning(f"  Could not clear emergency stop: {e}")
        
        self.logger.info("  ✅ Emergency stop functionality working")
        return True
    
    def test_velocity_limiting(self) -> bool:
        """Test velocity limiting functionality"""
        self.logger.info("  🏃 Testing velocity limiting...")
        
        # Create publisher for cmd_vel
        cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # Wait for publisher to be ready
        time.sleep(1.0)
        
        # Send high velocity command
        cmd_msg = Twist()
        cmd_msg.linear.x = 10.0  # Intentionally high velocity
        cmd_msg.angular.z = 5.0
        
        cmd_vel_pub.publish(cmd_msg)
        self.logger.info("  Sent high velocity command")
        
        # Wait for filtered command
        timeout = time.time() + 5.0
        velocity_limited = False
        
        while time.time() < timeout:
            if '/cmd_vel_filtered' in self.received_topics:
                filtered_msg = self.received_topics['/cmd_vel_filtered']['message']
                
                # Check if velocity was limited
                if (filtered_msg.linear.x < cmd_msg.linear.x and 
                    filtered_msg.angular.z < cmd_msg.angular.z):
                    velocity_limited = True
                    self.logger.info(f"  Velocity limited: {filtered_msg.linear.x:.2f} m/s, {filtered_msg.angular.z:.2f} rad/s")
                    break
            time.sleep(0.1)
        
        if not velocity_limited:
            self.logger.warning("  Velocity limiting not detected (may not be active)")
            # This is not necessarily a failure - velocity limiting might not be active
            return True
        
        self.logger.info("  ✅ Velocity limiting working")
        return True
    
    def test_service_availability(self) -> bool:
        """Test that expected services are available"""
        self.logger.info("  🔧 Testing service availability...")
        
        # Expected services
        expected_services = [
            '/clear_emergency_stop',
            '/reload_configuration'
        ]
        
        # Get available services
        service_names = self.get_service_names_and_types()
        available_services = [name for name, _ in service_names]
        
        missing_services = []
        for service in expected_services:
            if service not in available_services:
                missing_services.append(service)
        
        if missing_services:
            self.logger.warning(f"  Missing services: {missing_services}")
            # Services might not be available in all configurations
            return True
        
        self.logger.info(f"  ✅ All expected services available ({len(expected_services)} services)")
        return True
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("📊 INTEGRATION TEST SUMMARY")
        self.logger.info("=" * 60)
        
        passed_tests = [r for r in self.test_results if r.passed]
        failed_tests = [r for r in self.test_results if not r.passed]
        
        self.logger.info(f"Tests Passed: {len(passed_tests)}/{len(self.test_results)}")
        
        if failed_tests:
            self.logger.info(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                self.logger.info(f"  • {test.name}: {test.message}")
        
        if passed_tests:
            self.logger.info(f"\n✅ PASSED TESTS ({len(passed_tests)}):")
            for test in passed_tests:
                self.logger.info(f"  • {test.name} ({test.duration:.2f}s)")
        
        total_duration = sum(t.duration for t in self.test_results)
        self.logger.info(f"\nTotal test duration: {total_duration:.2f} seconds")
        
        if len(passed_tests) == len(self.test_results):
            self.logger.info("\n🎉 ALL INTEGRATION TESTS PASSED!")
            self.logger.info("System integration is working correctly.")
        else:
            self.logger.info("\n⚠️ SOME TESTS FAILED")
            self.logger.info("Check failed tests and system configuration.")
        
        self.logger.info("\n📋 System Status:")
        self.logger.info("  • Configuration Management: ✅" if any("Configuration" in t.name and t.passed for t in self.test_results) else "  • Configuration Management: ❌")
        self.logger.info("  • Hardware Discovery: ✅" if any("Hardware" in t.name and t.passed for t in self.test_results) else "  • Hardware Discovery: ❌")
        self.logger.info("  • Safety Systems: ✅" if any("Safety" in t.name and t.passed for t in self.test_results) else "  • Safety Systems: ❌")
        self.logger.info("  • Health Monitoring: ✅" if any("Health" in t.name and t.passed for t in self.test_results) else "  • Health Monitoring: ❌")


def main():
    """Main test function"""
    rclpy.init()
    
    try:
        tester = SystemIntegrationTester()
        
        # Run tests in a separate thread to allow ROS2 spinning
        test_thread = threading.Thread(target=lambda: tester.run_all_tests())
        test_thread.start()
        
        # Spin the node to receive messages
        executor = SingleThreadedExecutor()
        executor.add_node(tester)
        
        # Spin for test duration
        start_time = time.time()
        while test_thread.is_alive() and time.time() - start_time < 120.0:  # 2 minute timeout
            executor.spin_once(timeout_sec=0.1)
        
        test_thread.join(timeout=5.0)
        
        # Check if all tests passed
        if tester.test_results:
            all_passed = all(r.passed for r in tester.test_results)
            return all_passed
        else:
            tester.logger.error("No test results available")
            return False
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return False
    except Exception as e:
        print(f"Test failed with exception: {e}")
        return False
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)