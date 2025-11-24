#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
import json
import math
import os

class SemanticNavigator(Node):
    def __init__(self):
        super().__init__('semantic_navigator')
        
        self.navigator = BasicNavigator()
        
        # Parameters
        self.declare_parameter('semantic_map_path', 'semantic_map.json')
        self.map_path = self.get_parameter('semantic_map_path').value
        
        self.semantic_map = self.load_map()
        
        self.get_logger().info("Semantic Navigator Initialized")

    def load_map(self):
        if not os.path.exists(self.map_path):
            self.get_logger().error(f"Map file not found: {self.map_path}")
            return {}
        with open(self.map_path, 'r') as f:
            return json.load(f)

    def generate_candidate_points(self, centroid, radius, num_points=12):
        """Generates points on a circle around the object."""
        cx, cy = centroid
        points = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            px = cx + (radius + 1.0) * math.cos(angle) # Radius + 1.0m buffer
            py = cy + (radius + 1.0) * math.sin(angle)
            points.append((px, py))
        return points

    def filter_candidates(self, points):
        """
        Filters points based on costmap.
        TODO: Subscribe to /global_costmap/costmap and check values.
        For now, we assume all are valid.
        """
        valid_points = points # Placeholder
        return valid_points

    def select_best_candidate(self, points):
        """Selects the candidate closest to the robot (placeholder logic)."""
        if not points:
            return None
        # TODO: Get robot pose and compare distances
        return points[0] # Return first for now

    def go_to_object(self, object_name):
        if object_name not in self.semantic_map:
            self.get_logger().error(f"Object {object_name} not found in map")
            return

        obj_data = self.semantic_map[object_name]
        centroid = obj_data['centroid']
        radius = obj_data['radius']
        
        candidates = self.generate_candidate_points(centroid, radius)
        valid_candidates = self.filter_candidates(candidates)
        target = self.select_best_candidate(valid_candidates)
        
        if target:
            self.get_logger().info(f"Navigating to {object_name} at {target}")
            self.send_goal(target)
        else:
            self.get_logger().warn("No valid approach points found")

    def send_goal(self, point):
        goal_pose = PoseStamped()
        goal_pose.header.frame_id = 'map'
        goal_pose.header.stamp = self.navigator.get_clock().now().to_msg()
        goal_pose.pose.position.x = point[0]
        goal_pose.pose.position.y = point[1]
        goal_pose.pose.orientation.w = 1.0 # TODO: Face the object
        
        self.navigator.goToPose(goal_pose)
        
        while not self.navigator.isTaskComplete():
            pass
            
        result = self.navigator.getResult()
        if result == TaskResult.SUCCEEDED:
            self.get_logger().info('Goal succeeded!')
        else:
            self.get_logger().info('Goal failed!')

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
