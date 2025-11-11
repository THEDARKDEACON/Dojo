#!/usr/bin/env python3
"""
Comprehensive test script for RL Navigation system.

This script tests and validates the RL navigation implementation:
- Tests in multiple environments
- Measures success rate
- Measures collision rate
- Compares performance vs Nav2 baseline
"""

import os
import sys
import time
import math
import json
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from geometry_msgs.msg import PoseStamped, Twist
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from std_msgs.msg import String, Float32


@dataclass
class TestResult:
    """Results from a single navigation test."""
    environment: str
    start_position: Tuple[float, float]
    goal_position: Tuple[float, float]
    success: bool
    collision: bool
    time_taken: float
    path_length: float
    avg_velocity: float
    min_obstacle_distance: float
    confidence_scores: List[float]
    using_rl: bool  # True if RL was used, False if Nav2 fallback


@dataclass
class TestSummary:
    """Summary statistics for all tests."""
    total_tests: int
    success_rate: float
    collision_rate: float
    avg_time: float
    avg_path_length: float
    avg_confidence: float
    rl_usage_rate: float
    nav2_fallback_rate: float


class RLNavigationTester(Node):
    """
    Test node for RL navigation system.
    
    Runs comprehensive tests and collects metrics.
    """
    
    def __init__(self):
        super().__init__('rl_navigation_tester')
        
        # Test configuration
        self.test_environments = [
            'mapping_world',
            'house',
            'office_small',
            'warehouse'
        ]
        
        self.test_goals = [
            # (x, y) positions for each environment
            [(5.0, 0.0), (0.0, 5.0), (-5.0, 0.0), (0.0, -5.0)],  # mapping_world
            [(3.0, 3.0), (-3.0, 3.0), (-3.0, -3.0), (3.0, -3.0)],  # house
            [(4.0, 2.0), (2.0, 4.0), (-2.0, 2.0), (2.0, -2.0)],  # office_small
            [(8.0, 0.0), (0.0, 8.0), (-8.0, 0.0), (0.0, -8.0)]   # warehouse
        ]
        
        # Test state
        self.current_test = None
        self.test_results: List[TestResult] = []
        self.robot_pose = None
        self.robot_velocity = None
        self.lidar_data = None
        self.rl_confidence = 0.0
        self.rl_status = ""
        
        # Test tracking
        self.test_start_time = 0.0
        self.test_start_position = None
        self.path_positions = []
        self.min_obstacle_distances = []
        self.confidence_history = []
        
        # QoS profiles
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Subscribers
        self.odom_sub = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10
        )
        
        self.lidar_sub = self.create_subscription(
            LaserScan,
            '/scan',
            self.lidar_callback,
            sensor_qos
        )
        
        self.confidence_sub = self.create_subscription(
            Float32,
            '/rl_confidence',
            self.confidence_callback,
            10
        )
        
        self.status_sub = self.create_subscription(
            String,
            '/rl_status',
            self.status_callback,
            10
        )
        
        # Publishers
        self.goal_pub = self.create_publisher(
            PoseStamped,
            '/rl_goal',
            10
        )
        
        self.get_logger().info('RLNavigationTester initialized')
    
    def odom_callback(self, msg: Odometry):
        """Process odometry data."""
        self.robot_pose = msg.pose.pose
        self.robot_velocity = msg.twist.twist
        
        # Track path during test
        if self.current_test is not None:
            self.path_positions.append((
                self.robot_pose.position.x,
                self.robot_pose.position.y
            ))
    
    def lidar_callback(self, msg: LaserScan):
        """Process LiDAR data."""
        ranges = np.array(msg.ranges)
        ranges = np.nan_to_num(ranges, nan=msg.range_max, posinf=msg.range_max)
        self.lidar_data = ranges
        
        # Track minimum obstacle distance during test
        if self.current_test is not None:
            min_dist = np.min(ranges)
            self.min_obstacle_distances.append(min_dist)
    
    def confidence_callback(self, msg: Float32):
        """Process RL confidence score."""
        self.rl_confidence = msg.data
        
        if self.current_test is not None:
            self.confidence_history.append(self.rl_confidence)
    
    def status_callback(self, msg: String):
        """Process RL status."""
        self.rl_status = msg.data
    
    def send_goal(self, x: float, y: float):
        """Send navigation goal."""
        goal_msg = PoseStamped()
        goal_msg.header.frame_id = 'map'
        goal_msg.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.position.x = x
        goal_msg.pose.position.y = y
        goal_msg.pose.orientation.w = 1.0
        
        self.goal_pub.publish(goal_msg)
        self.get_logger().info(f'Sent goal: ({x:.2f}, {y:.2f})')
    
    def calculate_distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two positions."""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def calculate_path_length(self, positions: List[Tuple[float, float]]) -> float:
        """Calculate total path length."""
        if len(positions) < 2:
            return 0.0
        
        length = 0.0
        for i in range(1, len(positions)):
            length += self.calculate_distance(positions[i-1], positions[i])
        
        return length
    
    def check_collision(self) -> bool:
        """Check if robot has collided (very close to obstacle)."""
        if self.lidar_data is None:
            return False
        
        min_dist = np.min(self.lidar_data)
        return min_dist < 0.2  # Collision threshold: 20cm
    
    def check_goal_reached(self, goal: Tuple[float, float], threshold: float = 0.5) -> bool:
        """Check if robot has reached the goal."""
        if self.robot_pose is None:
            return False
        
        current_pos = (self.robot_pose.position.x, self.robot_pose.position.y)
        distance = self.calculate_distance(current_pos, goal)
        
        return distance < threshold
    
    def run_single_test(self, environment: str, goal: Tuple[float, float], timeout: float = 120.0) -> TestResult:
        """
        Run a single navigation test.
        
        Args:
            environment: Name of the test environment
            goal: Goal position (x, y)
            timeout: Maximum time for test (seconds)
            
        Returns:
            TestResult with metrics
        """
        self.get_logger().info(f'Starting test in {environment} to goal {goal}')
        
        # Initialize test tracking
        self.current_test = True
        self.test_start_time = time.time()
        self.test_start_position = (
            self.robot_pose.position.x,
            self.robot_pose.position.y
        ) if self.robot_pose else (0.0, 0.0)
        self.path_positions = [self.test_start_position]
        self.min_obstacle_distances = []
        self.confidence_history = []
        
        # Send goal
        self.send_goal(goal[0], goal[1])
        
        # Wait for robot to reach goal or timeout
        success = False
        collision = False
        
        rate = self.create_rate(10)  # 10 Hz
        while time.time() - self.test_start_time < timeout:
            rclpy.spin_once(self, timeout_sec=0.1)
            
            # Check for collision
            if self.check_collision():
                collision = True
                self.get_logger().warn('Collision detected!')
                break
            
            # Check if goal reached
            if self.check_goal_reached(goal):
                success = True
                self.get_logger().info('Goal reached!')
                break
            
            rate.sleep()
        
        # Calculate metrics
        time_taken = time.time() - self.test_start_time
        path_length = self.calculate_path_length(self.path_positions)
        avg_velocity = path_length / time_taken if time_taken > 0 else 0.0
        min_obstacle_distance = min(self.min_obstacle_distances) if self.min_obstacle_distances else 0.0
        avg_confidence = np.mean(self.confidence_history) if self.confidence_history else 0.0
        using_rl = 'RL' in self.rl_status
        
        # Create result
        result = TestResult(
            environment=environment,
            start_position=self.test_start_position,
            goal_position=goal,
            success=success,
            collision=collision,
            time_taken=time_taken,
            path_length=path_length,
            avg_velocity=avg_velocity,
            min_obstacle_distance=min_obstacle_distance,
            confidence_scores=self.confidence_history.copy(),
            using_rl=using_rl
        )
        
        # Reset test state
        self.current_test = None
        
        return result
    
    def run_all_tests(self) -> List[TestResult]:
        """Run all navigation tests."""
        self.get_logger().info('Starting comprehensive RL navigation tests')
        
        results = []
        
        for env_idx, environment in enumerate(self.test_environments):
            self.get_logger().info(f'\n=== Testing in {environment} ===')
            
            goals = self.test_goals[env_idx]
            
            for goal in goals:
                # Wait for robot to be ready
                time.sleep(2.0)
                
                # Run test
                result = self.run_single_test(environment, goal)
                results.append(result)
                
                # Log result
                self.get_logger().info(
                    f'Test result: Success={result.success}, '
                    f'Collision={result.collision}, '
                    f'Time={result.time_taken:.1f}s, '
                    f'Path={result.path_length:.1f}m'
                )
                
                # Wait between tests
                time.sleep(3.0)
        
        self.test_results = results
        return results
    
    def calculate_summary(self, results: List[TestResult]) -> TestSummary:
        """Calculate summary statistics from test results."""
        if not results:
            return TestSummary(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        
        total_tests = len(results)
        success_count = sum(1 for r in results if r.success)
        collision_count = sum(1 for r in results if r.collision)
        rl_usage_count = sum(1 for r in results if r.using_rl)
        
        success_rate = success_count / total_tests
        collision_rate = collision_count / total_tests
        avg_time = np.mean([r.time_taken for r in results])
        avg_path_length = np.mean([r.path_length for r in results])
        
        # Calculate average confidence across all tests
        all_confidences = []
        for r in results:
            all_confidences.extend(r.confidence_scores)
        avg_confidence = np.mean(all_confidences) if all_confidences else 0.0
        
        rl_usage_rate = rl_usage_count / total_tests
        nav2_fallback_rate = 1.0 - rl_usage_rate
        
        return TestSummary(
            total_tests=total_tests,
            success_rate=success_rate,
            collision_rate=collision_rate,
            avg_time=avg_time,
            avg_path_length=avg_path_length,
            avg_confidence=avg_confidence,
            rl_usage_rate=rl_usage_rate,
            nav2_fallback_rate=nav2_fallback_rate
        )
    
    def save_results(self, results: List[TestResult], summary: TestSummary, filename: str = 'rl_navigation_test_results.json'):
        """Save test results to JSON file."""
        data = {
            'summary': asdict(summary),
            'results': [asdict(r) for r in results]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.get_logger().info(f'Results saved to {filename}')
    
    def print_summary(self, summary: TestSummary):
        """Print test summary to console."""
        print('\n' + '='*60)
        print('RL NAVIGATION TEST SUMMARY')
        print('='*60)
        print(f'Total Tests:          {summary.total_tests}')
        print(f'Success Rate:         {summary.success_rate*100:.1f}% (target: 90%+)')
        print(f'Collision Rate:       {summary.collision_rate*100:.1f}% (target: <5%)')
        print(f'Average Time:         {summary.avg_time:.1f}s')
        print(f'Average Path Length:  {summary.avg_path_length:.1f}m')
        print(f'Average Confidence:   {summary.avg_confidence:.2f}')
        print(f'RL Usage Rate:        {summary.rl_usage_rate*100:.1f}%')
        print(f'Nav2 Fallback Rate:   {summary.nav2_fallback_rate*100:.1f}%')
        print('='*60)
        
        # Check if targets met
        if summary.success_rate >= 0.90:
            print('✓ SUCCESS RATE TARGET MET')
        else:
            print('✗ SUCCESS RATE TARGET NOT MET')
        
        if summary.collision_rate < 0.05:
            print('✓ COLLISION RATE TARGET MET')
        else:
            print('✗ COLLISION RATE TARGET NOT MET')
        
        print('='*60 + '\n')


def main(args=None):
    """Main function."""
    rclpy.init(args=args)
    
    try:
        tester = RLNavigationTester()
        
        # Wait for robot to be ready
        print('Waiting for robot to be ready...')
        time.sleep(5.0)
        
        # Run all tests
        results = tester.run_all_tests()
        
        # Calculate summary
        summary = tester.calculate_summary(results)
        
        # Print summary
        tester.print_summary(summary)
        
        # Save results
        tester.save_results(results, summary)
        
        print('Testing complete!')
        
    except KeyboardInterrupt:
        print('\nTesting interrupted by user')
    finally:
        if 'tester' in locals():
            tester.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
