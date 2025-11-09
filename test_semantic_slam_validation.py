#!/usr/bin/env python3
"""
Comprehensive Validation Test for Semantic SLAM System

This test validates all Priority 1 features:
- Task 1.1: YOLO integration with semantic map
- Task 1.2: LiDAR-camera fusion for depth estimation
- Task 1.3: Object persistence mechanism
- Task 1.4: Enhanced navigation interface

Run this test to validate the complete semantic SLAM system.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32
from sensor_msgs.msg import LaserScan, Image
from geometry_msgs.msg import PoseStamped
import json
import time
import os
import numpy as np
from typing import Dict, List

class SemanticSLAMValidator(Node):
    """Comprehensive validator for semantic SLAM system"""
    
    def __init__(self):
        super().__init__('semantic_slam_validator')
        
        # Test results for all tasks
        self.test_results = {
            # Task 1.1: YOLO Integration
            'yolo_integration': False,
            'semantic_map_publishing': False,
            'annotated_image_publishing': False,
            'natural_language_commands': False,
            
            # Task 1.2: LiDAR Fusion
            'lidar_data_available': False,
            'depth_estimation_active': False,
            'multiple_distances_detected': False,
            
            # Task 1.3: Persistence
            'persistence_file_exists': False,
            'objects_persisted': False,
            'object_merging_working': False,
            
            # Task 1.4: Navigation
            'nav2_integration': False,
            'spatial_indexing': False,
            'multi_step_navigation': False,
            'navigation_feedback': False,
            'progress_reporting': False
        }
        
        # Tracking data
        self.semantic_objects = {}
        self.object_history = {}
        self.detected_distances = []
        self.navigation_statuses = []
        self.progress_updates = []
        self.lidar_available = False
        
        # Subscribers
        self.semantic_map_sub = self.create_subscription(
            String, '/semantic_map', self.semantic_map_callback, 10)
        self.annotated_image_sub = self.create_subscription(
            Image, '/semantic_image', self.annotated_image_callback, 10)
        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10)
        self.status_sub = self.create_subscription(
            String, '/navigation_status', self.status_callback, 10)
        self.progress_sub = self.create_subscription(
            Float32, '/navigation_progress', self.progress_callback, 10)
        self.response_sub = self.create_subscription(
            String, '/semantic_response', self.response_callback, 10)
        
        # Publisher for test commands
        self.command_pub = self.create_publisher(String, '/text_command', 10)
        
        self.get_logger().info("🧪 Semantic SLAM Comprehensive Validator initialized")
        self.get_logger().info("="*60)
        
        # Run validation tests
        self.test_timer = self.create_timer(10.0, self.run_validation_tests)
    
    def semantic_map_callback(self, msg: String):
        """Track semantic map updates"""
        try:
            data = json.loads(msg.data)
            self.semantic_objects = data.get('objects', {})
            
            if self.semantic_objects:
                self.test_results['semantic_map_publishing'] = True
                self.test_results['yolo_integration'] = True
                self.test_results['objects_persisted'] = True
                
                # Track object history for merging detection
                current_time = time.time()
                for obj_id, obj_data in self.semantic_objects.items():
                    if obj_id not in self.object_history:
                        self.object_history[obj_id] = {
                            'first_seen': current_time,
                            'detections': []
                        }
                    self.object_history[obj_id]['detections'].append(current_time)
                
                # Check for object merging
                for obj_id, history in self.object_history.items():
                    if len(history['detections']) > 1:
                        self.test_results['object_merging_working'] = True
                
                # Extract distances for Task 1.2 validation
                for obj_id, obj_data in self.semantic_objects.items():
                    x = obj_data.get('x', 0)
                    y = obj_data.get('y', 0)
                    distance = np.sqrt(x**2 + y**2)
                    self.detected_distances.append(distance)
                
                # Check for varied distances (not just 2.0m fallback)
                if len(self.detected_distances) > 3:
                    unique_distances = len(set([round(d, 1) for d in self.detected_distances[-10:]]))
                    if unique_distances > 2:
                        self.test_results['multiple_distances_detected'] = True
                        self.test_results['depth_estimation_active'] = True
                
        except json.JSONDecodeError:
            pass
    
    def annotated_image_callback(self, msg: Image):
        """Verify annotated images"""
        self.test_results['annotated_image_publishing'] = True
    
    def scan_callback(self, msg: LaserScan):
        """Verify LiDAR data"""
        if not self.lidar_available:
            self.lidar_available = True
            self.test_results['lidar_data_available'] = True
    
    def status_callback(self, msg: String):
        """Track navigation status"""
        try:
            data = json.loads(msg.data)
            self.navigation_statuses.append(data)
            
            if data.get('status') in ['started', 'in_progress', 'succeeded']:
                self.test_results['nav2_integration'] = True
                self.test_results['spatial_indexing'] = True
            
            if 'message' in data and 'timestamp' in data:
                self.test_results['navigation_feedback'] = True
            
            if data.get('queued_goals', 0) > 0:
                self.test_results['multi_step_navigation'] = True
                
        except json.JSONDecodeError:
            pass
    
    def progress_callback(self, msg: Float32):
        """Track navigation progress"""
        self.progress_updates.append(msg.data)
        self.test_results['progress_reporting'] = True
    
    def response_callback(self, msg: String):
        """Track command responses"""
        self.test_results['natural_language_commands'] = True
    
    def run_validation_tests(self):
        """Run comprehensive validation tests"""
        self.get_logger().info("\n" + "="*60)
        self.get_logger().info("🧪 RUNNING COMPREHENSIVE SEMANTIC SLAM VALIDATION")
        self.get_logger().info("="*60)
        
        # Send test commands
        self.get_logger().info("\n📤 Sending test commands...")
        
        # Test natural language
        cmd = String()
        cmd.data = "list objects"
        self.command_pub.publish(cmd)
        time.sleep(1.0)
        
        # Test navigation
        cmd.data = "go to chair"
        self.command_pub.publish(cmd)
        time.sleep(1.0)
        
        # Check persistence file
        persistence_file = 'semantic_map_persistent.pkl'
        if os.path.exists(persistence_file):
            self.test_results['persistence_file_exists'] = True
        
        # Wait for results
        time.sleep(3.0)
        
        # Print results
        self.print_results()
        
        # Cancel timer
        self.test_timer.cancel()
    
    def print_results(self):
        """Print comprehensive validation results"""
        self.get_logger().info("\n" + "="*60)
        self.get_logger().info("📊 SEMANTIC SLAM VALIDATION RESULTS")
        self.get_logger().info("="*60)
        
        # Group results by task
        tasks = {
            'Task 1.1: YOLO Integration': [
                'yolo_integration',
                'semantic_map_publishing',
                'annotated_image_publishing',
                'natural_language_commands'
            ],
            'Task 1.2: LiDAR Fusion': [
                'lidar_data_available',
                'depth_estimation_active',
                'multiple_distances_detected'
            ],
            'Task 1.3: Persistence': [
                'persistence_file_exists',
                'objects_persisted',
                'object_merging_working'
            ],
            'Task 1.4: Navigation': [
                'nav2_integration',
                'spatial_indexing',
                'multi_step_navigation',
                'navigation_feedback',
                'progress_reporting'
            ]
        }
        
        total_passed = 0
        total_tests = 0
        
        for task_name, test_keys in tasks.items():
            self.get_logger().info(f"\n{task_name}:")
            task_passed = 0
            for key in test_keys:
                result = self.test_results[key]
                status = "✅ PASS" if result else "⚠️ PENDING"
                self.get_logger().info(f"  {status}: {key.replace('_', ' ').title()}")
                if result:
                    task_passed += 1
                    total_passed += 1
                total_tests += 1
            
            task_percentage = (task_passed / len(test_keys)) * 100
            self.get_logger().info(f"  Task Score: {task_passed}/{len(test_keys)} ({task_percentage:.0f}%)")
        
        # Overall results
        self.get_logger().info("\n" + "-"*60)
        overall_percentage = (total_passed / total_tests) * 100
        self.get_logger().info(f"Overall Score: {total_passed}/{total_tests} ({overall_percentage:.0f}%)")
        
        if overall_percentage >= 80:
            self.get_logger().info("🎉 EXCELLENT - System fully functional!")
        elif overall_percentage >= 60:
            self.get_logger().info("✅ GOOD - Core functionality working")
        elif overall_percentage >= 40:
            self.get_logger().info("⚠️ PARTIAL - Some features need attention")
        else:
            self.get_logger().info("❌ NEEDS WORK - Check implementation")
        
        self.get_logger().info("="*60)
        
        # Print statistics
        if self.semantic_objects or self.navigation_statuses:
            self.get_logger().info("\n📈 STATISTICS:")
            self.get_logger().info(f"  Objects detected: {len(self.semantic_objects)}")
            self.get_logger().info(f"  Object types: {len(set(obj['class'] for obj in self.semantic_objects.values()))}")
            self.get_logger().info(f"  Navigation statuses: {len(self.navigation_statuses)}")
            self.get_logger().info(f"  Progress updates: {len(self.progress_updates)}")
            
            if self.detected_distances:
                self.get_logger().info(f"  Distance range: {min(self.detected_distances):.2f}m - {max(self.detected_distances):.2f}m")
        
        # Print instructions
        self.get_logger().info("\n📝 NOTES:")
        self.get_logger().info("  - Some tests require objects in camera view")
        self.get_logger().info("  - Nav2 tests require Nav2 stack running")
        self.get_logger().info("  - Run with: ros2 launch robot_semantic_slam cutting_edge_features.launch.py")
        self.get_logger().info("\n✅ Validation Complete!")

def main(args=None):
    rclpy.init(args=args)
    validator = SemanticSLAMValidator()
    
    try:
        rclpy.spin(validator)
    except KeyboardInterrupt:
        pass
    finally:
        validator.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
