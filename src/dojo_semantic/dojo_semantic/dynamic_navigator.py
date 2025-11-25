#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from tf2_ros import TransformListener, Buffer
import json
import math
import os
import numpy as np

class SemanticNavigator(Node):
    def __init__(self):
        super().__init__('semantic_navigator')
        
        self.navigator = BasicNavigator()
        
        # Parameters
        self.declare_parameter('semantic_map_path', 'semantic_map.json')
        self.declare_parameter('costmap_threshold', 90)  # Cost above this is considered occupied
        self.declare_parameter('num_candidates', 12)  # Number of approach points
        self.declare_parameter('approach_buffer', 1.0)  # Distance from object center
        
        self.map_path = self.get_parameter('semantic_map_path').value
        self.costmap_threshold = self.get_parameter('costmap_threshold').value
        self.num_candidates = self.get_parameter('num_candidates').value
        self.approach_buffer = self.get_parameter('approach_buffer').value
        
        # TF2 for robot pose
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        # Costmap subscriber
        self.costmap = None
        self.costmap_sub = self.create_subscription(
            OccupancyGrid,
            '/global_costmap/costmap',
            self.costmap_callback,
            10
        )
        
        # Load semantic map
        self.semantic_map = self.load_map()
        
        # Current robot pose
        self.robot_x = 0.0
        self.robot_y = 0.0
        
        self.get_logger().info("Semantic Navigator Initialized")

    def load_map(self):
        """Load semantic map from JSON file."""
        if not os.path.exists(self.map_path):
            self.get_logger().warn(f"Map file not found: {self.map_path}, creating empty map")
            return {}
        try:
            with open(self.map_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.get_logger().error(f"Failed to load semantic map: {e}")
            return {}

    def costmap_callback(self, msg):
        """Store the latest costmap."""
        self.costmap = msg

    def get_robot_pose(self):
        """Get current robot pose from TF."""
        try:
            transform = self.tf_buffer.lookup_transform(
                'map',
                'base_link',
                rclpy.time.Time(),
                timeout=rclpy.duration.Duration(seconds=0.5)
            )
            
            self.robot_x = transform.transform.translation.x
            self.robot_y = transform.transform.translation.y
            return True
        except Exception as e:
            self.get_logger().warn(f"TF lookup failed: {e}", throttle_duration_sec=5.0)
            return False

    def generate_candidate_points(self, centroid, radius):
        """Generate candidate approach points in a circle around the object."""
        cx, cy = centroid
        points = []
        for i in range(self.num_candidates):
            angle = 2 * math.pi * i / self.num_candidates
            px = cx + (radius + self.approach_buffer) * math.cos(angle)
            py = cy + (radius + self.approach_buffer) * math.sin(angle)
            points.append((px, py, angle))  # Include angle to face the object
        return points

    def world_to_grid(self, world_x, world_y, costmap):
        """Convert world coordinates to grid coordinates."""
        origin_x = costmap.info.origin.position.x
        origin_y = costmap.info.origin.position.y
        resolution = costmap.info.resolution
        
        grid_x = int((world_x - origin_x) / resolution)
        grid_y = int((world_y - origin_y) / resolution)
        
        return grid_x, grid_y

    def get_cost_at_point(self, world_x, world_y):
        """Get costmap value at a world coordinate."""
        if self.costmap is None:
            return 0  # No costmap, assume free
        
        grid_x, grid_y = self.world_to_grid(world_x, world_y, self.costmap)
        
        # Check bounds
        if (grid_x < 0 or grid_x >= self.costmap.info.width or
            grid_y < 0 or grid_y >= self.costmap.info.height):
            return 100  # Out of bounds, treat as occupied
        
        # Get cost from data array
        index = grid_y * self.costmap.info.width + grid_x
        if index < len(self.costmap.data):
            return self.costmap.data[index]
        return 100  # Invalid index

    def filter_candidates(self, candidates):
        """Filter candidate points based on costmap - remove occupied points."""
        valid_candidates = []
        
        for px, py, angle in candidates:
            cost = self.get_cost_at_point(px, py)
            
            if cost < self.costmap_threshold:
                valid_candidates.append((px, py, angle))
                self.get_logger().debug(f"Candidate ({px:.2f}, {py:.2f}) cost={cost} - VALID")
            else:
                self.get_logger().debug(f"Candidate ({px:.2f}, {py:.2f}) cost={cost} - BLOCKED")
        
        self.get_logger().info(f"Filtered {len(valid_candidates)}/{len(candidates)} valid candidates")
        return valid_candidates

    def select_best_candidate(self, candidates, object_centroid):
        """Select the candidate closest to the robot that also faces the object."""
        if not candidates:
            return None
        
        # Get current robot pose
        if not self.get_robot_pose():
            # If no TF, return first valid candidate
            return candidates[0] if candidates else None
        
        best_candidate = None
        min_distance = float('inf')
        
        for px, py, angle in candidates:
            # Calculate distance from robot to candidate
            distance = math.sqrt((px - self.robot_x)**2 + (py - self.robot_y)**2)
            
            if distance < min_distance:
                min_distance = distance
                best_candidate = (px, py, angle)
        
        if best_candidate:
            self.get_logger().info(
                f"Selected candidate at ({best_candidate[0]:.2f}, {best_candidate[1]:.2f}) "
                f"distance={min_distance:.2f}m"
            )
        
        return best_candidate

    def calculate_orientation_to_object(self, px, py, object_centroid):
        """Calculate quaternion to face the object from the approach point."""
        cx, cy = object_centroid
        dx = cx - px
        dy = cy - py
        yaw = math.atan2(dy, dx)
        
        # Convert yaw to quaternion
        qw = math.cos(yaw / 2)
        qz = math.sin(yaw / 2)
        
        return qw, qz

    def go_to_object(self, object_name):
        """Navigate to approach a specific semantic object."""
        if object_name not in self.semantic_map:
            self.get_logger().error(f"Object '{object_name}' not found in semantic map")
            return False

        obj_data = self.semantic_map[object_name]
        centroid = obj_data['centroid']
        radius = obj_data.get('radius', 0.5)  # Default radius if not specified
        
        self.get_logger().info(f"Planning approach to '{object_name}' at {centroid}")
        
        # Generate candidate approach points
        candidates = self.generate_candidate_points(centroid, radius)
        
        # Filter based on costmap
        valid_candidates = self.filter_candidates(candidates)
        
        if not valid_candidates:
            self.get_logger().error("No valid approach points found - all blocked!")
            return False
        
        # Select best candidate
        target = self.select_best_candidate(valid_candidates, centroid)
        
        if target:
            px, py, angle = target
            self.get_logger().info(f"Navigating to {object_name} at ({px:.2f}, {py:.2f})")
            return self.send_goal(px, py, centroid)
        else:
            self.get_logger().error("Failed to select approach point")
            return False

    def send_goal(self, px, py, object_centroid):
        """Send navigation goal to Nav2."""
        goal_pose = PoseStamped()
        goal_pose.header.frame_id = 'map'
        goal_pose.header.stamp = self.navigator.get_clock().now().to_msg()
        goal_pose.pose.position.x = px
        goal_pose.pose.position.y = py
        goal_pose.pose.position.z = 0.0
        
        # Face the object
        qw, qz = self.calculate_orientation_to_object(px, py, object_centroid)
        goal_pose.pose.orientation.w = qw
        goal_pose.pose.orientation.z = qz
        
        self.get_logger().info(f"Sending goal: ({px:.2f}, {py:.2f})")
        
        self.navigator.goToPose(goal_pose)
        
        # Wait for completion
        while not self.navigator.isTaskComplete():
            rclpy.spin_once(self, timeout_sec=0.1)
            
        result = self.navigator.getResult()
        if result == TaskResult.SUCCEEDED:
            self.get_logger().info('Navigation succeeded!')
            return True
        else:
            self.get_logger().warn(f'Navigation failed with result: {result}')
            return False

def main(args=None):
    rclpy.init(args=args)
    node = SemanticNavigator()
    
    # Example usage
    # node.go_to_object("chair_1")
    
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
