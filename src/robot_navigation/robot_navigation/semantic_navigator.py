import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid
from robot_navigation_interfaces.action import NavigateToObject
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
import json
import math
import numpy as np
import os
from ament_index_python.packages import get_package_share_directory

class SemanticNavigator(Node):
    def __init__(self):
        super().__init__('semantic_navigator')
        
        # Load Semantic Map
        self.declare_parameter('semantic_map_path', '')
        map_path_param = self.get_parameter('semantic_map_path').get_parameter_value().string_value
        
        if not map_path_param:
            # Default to package share directory
            pkg_share = get_package_share_directory('robot_navigation')
            self.map_path = os.path.join(pkg_share, 'config', 'semantic_map.json')
        else:
            self.map_path = map_path_param

        self.load_map()

        # Costmap Subscription
        self.costmap = None
        self.create_subscription(
            OccupancyGrid,
            '/global_costmap/costmap',
            self.costmap_callback,
            10
        )

        # Action Server
        self._action_server = ActionServer(
            self,
            NavigateToObject,
            'navigate_to_object',
            self.execute_callback,
            callback_group=ReentrantCallbackGroup()
        )

        # Nav2 Navigator
        self.navigator = BasicNavigator()

        self.get_logger().info('Semantic Navigator Started')

    def load_map(self):
        try:
            with open(self.map_path, 'r') as f:
                self.semantic_map = json.load(f)
            self.get_logger().info(f'Loaded semantic map from {self.map_path}')
        except Exception as e:
            self.get_logger().error(f'Failed to load semantic map: {e}')
            self.semantic_map = {}

    def costmap_callback(self, msg):
        self.costmap = msg

    def execute_callback(self, goal_handle):
        self.get_logger().info('Executing goal...')
        object_name = goal_handle.request.object_name
        
        if object_name not in self.semantic_map:
            goal_handle.abort()
            result = NavigateToObject.Result()
            result.success = False
            result.message = f"Object '{object_name}' not found in map."
            return result

        obj_data = self.semantic_map[object_name]
        centroid = obj_data['centroid']
        radius = obj_data['radius']
        
        # Generate Candidates
        candidates = self.generate_candidates(centroid, radius)
        
        # Validate Candidates
        valid_candidates = self.validate_candidates(candidates)
        
        if not valid_candidates:
            goal_handle.abort()
            result = NavigateToObject.Result()
            result.success = False
            result.message = "No valid view points found."
            return result

        # Select Best Candidate
        best_pose = self.select_best_candidate(valid_candidates)
        
        # Navigate
        self.navigator.goToPose(best_pose)
        
        while not self.navigator.isTaskComplete():
            feedback = NavigateToObject.Feedback()
            feedback.current_status = "Navigating..."
            goal_handle.publish_feedback(feedback)
            # Check for cancel
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                self.navigator.cancelTask()
                result = NavigateToObject.Result()
                result.success = False
                result.message = "Goal canceled"
                return result

        result = self.navigator.getResult()
        
        action_result = NavigateToObject.Result()
        if result == TaskResult.SUCCEEDED:
            goal_handle.succeed()
            action_result.success = True
            action_result.message = "Arrived at best view point."
        else:
            goal_handle.abort()
            action_result.success = False
            action_result.message = "Navigation failed."
            
        return action_result

    def generate_candidates(self, centroid, radius):
        candidates = []
        target_radius = radius + 1.0
        angles = np.linspace(0, 2 * np.pi, 8, endpoint=False)
        
        for angle in angles:
            x = centroid['x'] + target_radius * np.cos(angle)
            y = centroid['y'] + target_radius * np.sin(angle)
            candidates.append((x, y, angle + np.pi)) # Face the object
            
        return candidates

    def validate_candidates(self, candidates):
        if self.costmap is None:
            self.get_logger().warn("No costmap received yet. Assuming all valid.")
            return candidates # Or return empty if strict

        valid = []
        resolution = self.costmap.info.resolution
        origin_x = self.costmap.info.origin.position.x
        origin_y = self.costmap.info.origin.position.y
        width = self.costmap.info.width
        height = self.costmap.info.height
        data = self.costmap.data

        for x, y, theta in candidates:
            # Convert world to grid
            grid_x = int((x - origin_x) / resolution)
            grid_y = int((y - origin_y) / resolution)

            if 0 <= grid_x < width and 0 <= grid_y < height:
                index = grid_y * width + grid_x
                cost = data[index]
                # Check occupancy (assuming > 90 is lethal)
                if cost < 90 and cost != -1: # -1 is unknown, usually treat as free or risky
                     valid.append((x, y, theta))
            else:
                # Out of bounds
                pass
        
        return valid

    def select_best_candidate(self, candidates):
        # Get current robot pose (mocking or getting from TF)
        # For simplicity, using (0,0) or last known pose if available via navigator?
        # BasicNavigator doesn't expose getRobotPose easily without spinning.
        # We'll assume the robot is at (0,0) for the first step or use a placeholder.
        # Ideally, we should use TF.
        
        # Let's try to get the pose from Nav2's feedback if possible, or just use 0,0 for now as a fallback
        # In a real scenario, we'd use a TF listener.
        
        current_x, current_y = 0.0, 0.0 # Placeholder
        
        # If we could get the pose:
        # trans = self.tf_buffer.lookup_transform(...)
        
        best_candidate = None
        min_dist = float('inf')
        
        for x, y, theta in candidates:
            dist = math.hypot(x - current_x, y - current_y)
            if dist < min_dist:
                min_dist = dist
                best_candidate = (x, y, theta)
                
        # Create PoseStamped
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = best_candidate[0]
        pose.pose.position.y = best_candidate[1]
        
        # Convert theta to quaternion
        q = self.euler_to_quaternion(0, 0, best_candidate[2])
        pose.pose.orientation.x = q[0]
        pose.pose.orientation.y = q[1]
        pose.pose.orientation.z = q[2]
        pose.pose.orientation.w = q[3]
        
        return pose

    def euler_to_quaternion(self, roll, pitch, yaw):
        qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
        qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
        qz = np.cos(roll/2) * np.cos(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.sin(pitch/2) * np.cos(yaw/2)
        qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
        return [qx, qy, qz, qw]

def main(args=None):
    rclpy.init(args=args)
    node = SemanticNavigator()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
