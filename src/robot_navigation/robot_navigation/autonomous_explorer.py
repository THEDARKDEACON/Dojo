#!/usr/bin/env python3
"""
Autonomous Explorer Node for SLAM-based mapping

This node implements frontier-based exploration to autonomously map
unknown environments using SLAM and Nav2.
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup

import numpy as np
import cv2
from scipy import ndimage
from sklearn.cluster import DBSCAN
import math

from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import PoseStamped, Point
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import Header
from visualization_msgs.msg import Marker, MarkerArray

import tf2_ros
import tf2_geometry_msgs
from tf2_ros import TransformException


class AutonomousExplorer(Node):
    def __init__(self):
        super().__init__('autonomous_explorer')
        
        # Parameters
        self.declare_parameter('exploration_radius', 2.0)
        self.declare_parameter('min_frontier_size', 10)
        self.declare_parameter('robot_radius', 0.22)
        self.declare_parameter('goal_timeout', 30.0)
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('base_frame', 'base_link')
        
        self.exploration_radius = self.get_parameter('exploration_radius').value
        self.min_frontier_size = self.get_parameter('min_frontier_size').value
        self.robot_radius = self.get_parameter('robot_radius').value
        self.goal_timeout = self.get_parameter('goal_timeout').value
        self.map_frame = self.get_parameter('map_frame').value
        self.base_frame = self.get_parameter('base_frame').value
        
        # State variables
        self.map_data = None
        self.current_goal = None
        self.exploration_complete = False
        self.goal_start_time = None
        self.visited_frontiers = []  # Track visited locations
        self.exploration_start_time = self.get_clock().now()
        self.last_frontier_count = 0
        self.no_progress_count = 0
        
        # Callback group for concurrent operations
        self.callback_group = ReentrantCallbackGroup()
        
        # TF2 buffer and listener
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)    
    
        # Subscribers
        self.map_subscriber = self.create_subscription(
            OccupancyGrid,
            '/map',
            self.map_callback,
            10,
            callback_group=self.callback_group
        )
        
        # Publishers
        self.frontier_publisher = self.create_publisher(
            MarkerArray,
            '/exploration_frontiers',
            10
        )
        
        self.goal_publisher = self.create_publisher(
            PoseStamped,
            '/exploration_goal',
            10
        )
        
        # Action client for navigation
        self.nav_action_client = ActionClient(
            self,
            NavigateToPose,
            '/navigate_to_pose',
            callback_group=self.callback_group
        )
        
        # Timer for exploration loop
        self.exploration_timer = self.create_timer(
            3.0,  # Check every 3 seconds
            self.exploration_loop,
            callback_group=self.callback_group
        )
        
        self.get_logger().info("🤖 Autonomous Explorer initialized - Starting frontier-based exploration!")
        self.get_logger().info(f"📊 Configuration: radius={self.exploration_radius}m, min_frontier_size={self.min_frontier_size}")
        self.get_logger().info("⏳ Waiting for map data and navigation system to be ready...")
    
    def map_callback(self, msg):
        """Process incoming map data"""
        self.map_data = msg
    
    def get_robot_position(self):
        """Get current robot position in map frame"""
        try:
            transform = self.tf_buffer.lookup_transform(
                self.map_frame,
                self.base_frame,
                rclpy.time.Time()
            )
            
            robot_x = transform.transform.translation.x
            robot_y = transform.transform.translation.y
            
            return robot_x, robot_y
            
        except TransformException as e:
            self.get_logger().warn(f"Could not get robot position: {e}")
            return None, None    

    def find_frontiers(self, occupancy_grid):
        """Find frontier points in the occupancy grid using advanced edge detection"""
        if occupancy_grid is None:
            return []
        
        # Convert occupancy grid to numpy array
        width = occupancy_grid.info.width
        height = occupancy_grid.info.height
        resolution = occupancy_grid.info.resolution
        origin = occupancy_grid.info.origin
        
        # Reshape data to 2D array
        grid = np.array(occupancy_grid.data).reshape((height, width))
        
        # Create binary maps
        free_space = (grid == 0).astype(np.uint8)  # Free space
        unknown_space = (grid == -1).astype(np.uint8)  # Unknown space
        occupied_space = (grid == 100).astype(np.uint8)  # Obstacles
        
        # Apply morphological operations to clean up the map
        kernel = np.ones((3, 3), np.uint8)
        
        # Clean free space (remove noise)
        free_space = cv2.morphologyEx(free_space, cv2.MORPH_OPEN, kernel)
        free_space = cv2.morphologyEx(free_space, cv2.MORPH_CLOSE, kernel)
        
        # Find frontiers using multiple methods for robustness
        
        # Method 1: Dilation-based frontier detection
        free_dilated = cv2.dilate(free_space, kernel, iterations=1)
        frontiers_method1 = np.logical_and(free_dilated, unknown_space)
        
        # Method 2: Edge detection on free space boundaries
        free_edges = cv2.Canny(free_space * 255, 50, 150)
        free_edges = free_edges > 0
        frontiers_method2 = np.logical_and(free_edges, unknown_space)
        
        # Combine both methods
        frontiers = np.logical_or(frontiers_method1, frontiers_method2)
        
        # Remove frontiers too close to obstacles
        occupied_dilated = cv2.dilate(occupied_space, kernel, iterations=2)
        frontiers = np.logical_and(frontiers, ~occupied_dilated)
        
        # Apply additional filtering
        frontiers = cv2.morphologyEx(frontiers.astype(np.uint8), cv2.MORPH_OPEN, kernel)
        
        # Find frontier coordinates
        frontier_coords = np.where(frontiers)
        
        if len(frontier_coords[0]) == 0:
            return []
        
        # Convert grid coordinates to world coordinates
        frontier_points = []
        for i in range(len(frontier_coords[0])):
            grid_x = frontier_coords[1][i]
            grid_y = frontier_coords[0][i]
            
            # Convert to world coordinates
            world_x = origin.position.x + grid_x * resolution
            world_y = origin.position.y + (height - grid_y - 1) * resolution
            
            frontier_points.append((world_x, world_y))
        
        self.get_logger().info(f"Found {len(frontier_points)} frontier points")
        return frontier_points
    
    def cluster_frontiers(self, frontier_points):
        """Cluster frontier points using adaptive clustering and return weighted centers"""
        if len(frontier_points) < self.min_frontier_size:
            return []
        
        # Convert to numpy array
        points = np.array(frontier_points)
        
        # Adaptive clustering parameters based on map resolution
        if self.map_data:
            resolution = self.map_data.info.resolution
            eps = max(0.5, resolution * 10)  # Adaptive epsilon based on resolution
        else:
            eps = 0.5
        
        # Cluster frontiers using DBSCAN with adaptive parameters
        min_samples = max(3, self.min_frontier_size // 3)
        clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(points)
        
        cluster_centers = []
        cluster_info = []
        
        for cluster_id in set(clustering.labels_):
            if cluster_id == -1:  # Noise points
                continue
                
            cluster_points = points[clustering.labels_ == cluster_id]
            cluster_size = len(cluster_points)
            
            if cluster_size >= self.min_frontier_size:
                # Calculate weighted center (prefer points with more neighbors)
                center = np.mean(cluster_points, axis=0)
                
                # Calculate cluster quality metrics
                distances = np.linalg.norm(cluster_points - center, axis=1)
                compactness = np.std(distances)  # Lower is better
                
                cluster_centers.append((center[0], center[1]))
                cluster_info.append({
                    'center': (center[0], center[1]),
                    'size': cluster_size,
                    'compactness': compactness,
                    'points': cluster_points
                })
        
        # Sort clusters by size (larger clusters are potentially more valuable)
        cluster_info.sort(key=lambda x: x['size'], reverse=True)
        
        self.get_logger().info(f"Found {len(cluster_centers)} frontier clusters")
        for i, info in enumerate(cluster_info[:5]):  # Log top 5 clusters
            self.get_logger().debug(
                f"Cluster {i}: size={info['size']}, "
                f"center=({info['center'][0]:.2f}, {info['center'][1]:.2f}), "
                f"compactness={info['compactness']:.3f}"
            )
        
        return cluster_centers    
 
    def calculate_information_gain(self, frontier_x, frontier_y):
        """Calculate expected information gain for a frontier"""
        if self.map_data is None:
            return 0.0
        
        # Convert world coordinates to grid coordinates
        resolution = self.map_data.info.resolution
        origin = self.map_data.info.origin
        width = self.map_data.info.width
        height = self.map_data.info.height
        
        grid_x = int((frontier_x - origin.position.x) / resolution)
        grid_y = int((height - (frontier_y - origin.position.y) / resolution - 1))
        
        # Check bounds
        if grid_x < 0 or grid_x >= width or grid_y < 0 or grid_y >= height:
            return 0.0
        
        # Count unknown cells in a radius around the frontier
        grid = np.array(self.map_data.data).reshape((height, width))
        search_radius = int(2.0 / resolution)  # 2 meter radius
        
        unknown_count = 0
        total_count = 0
        
        for dy in range(-search_radius, search_radius + 1):
            for dx in range(-search_radius, search_radius + 1):
                check_x = grid_x + dx
                check_y = grid_y + dy
                
                if (0 <= check_x < width and 0 <= check_y < height and
                    dx*dx + dy*dy <= search_radius*search_radius):
                    total_count += 1
                    if grid[check_y, check_x] == -1:  # Unknown cell
                        unknown_count += 1
        
        return unknown_count / max(total_count, 1)
    
    def is_frontier_safe(self, frontier_x, frontier_y):
        """Check if frontier is in a safe location (not too close to obstacles)"""
        if self.map_data is None:
            return True
        
        # Convert to grid coordinates
        resolution = self.map_data.info.resolution
        origin = self.map_data.info.origin
        width = self.map_data.info.width
        height = self.map_data.info.height
        
        grid_x = int((frontier_x - origin.position.x) / resolution)
        grid_y = int((height - (frontier_y - origin.position.y) / resolution - 1))
        
        if grid_x < 0 or grid_x >= width or grid_y < 0 or grid_y >= height:
            return False
        
        grid = np.array(self.map_data.data).reshape((height, width))
        safety_radius = int(self.robot_radius * 1.5 / resolution)  # Safety margin
        
        # Check for obstacles in safety radius
        for dy in range(-safety_radius, safety_radius + 1):
            for dx in range(-safety_radius, safety_radius + 1):
                check_x = grid_x + dx
                check_y = grid_y + dy
                
                if (0 <= check_x < width and 0 <= check_y < height and
                    dx*dx + dy*dy <= safety_radius*safety_radius):
                    if grid[check_y, check_x] == 100:  # Obstacle
                        return False
        
        return True
    
    def select_best_frontier(self, frontiers, robot_x, robot_y):
        """Select the best frontier to explore based on distance, information gain, and safety"""
        if not frontiers:
            return None
        
        best_frontier = None
        best_score = float('-inf')
        
        self.get_logger().info(f"Evaluating {len(frontiers)} frontier clusters...")
        
        for i, frontier in enumerate(frontiers):
            fx, fy = frontier
            
            # Calculate distance to frontier
            distance = np.sqrt((fx - robot_x)**2 + (fy - robot_y)**2)
            
            # Skip if too close or too far
            if distance < 1.0 or distance > self.exploration_radius:
                continue
            
            # Check if frontier is safe
            if not self.is_frontier_safe(fx, fy):
                self.get_logger().debug(f"Frontier {i} at ({fx:.2f}, {fy:.2f}) is not safe")
                continue
            
            # Calculate information gain
            info_gain = self.calculate_information_gain(fx, fy)
            
            # Multi-criteria scoring
            distance_score = 1.0 / (distance + 0.1)  # Prefer closer frontiers
            info_score = info_gain * 10.0  # Weight information gain highly
            
            # Combined score
            score = distance_score + info_score
            
            self.get_logger().debug(
                f"Frontier {i}: dist={distance:.2f}, info_gain={info_gain:.3f}, score={score:.3f}"
            )
            
            if score > best_score:
                best_score = score
                best_frontier = frontier
        
        if best_frontier:
            self.get_logger().info(
                f"Selected frontier at ({best_frontier[0]:.2f}, {best_frontier[1]:.2f}) "
                f"with score {best_score:.3f}"
            )
        
        return best_frontier
    
    def create_goal_pose(self, x, y):
        """Create a PoseStamped message for navigation goal"""
        goal_pose = PoseStamped()
        goal_pose.header.frame_id = self.map_frame
        goal_pose.header.stamp = self.get_clock().now().to_msg()
        
        goal_pose.pose.position.x = x
        goal_pose.pose.position.y = y
        goal_pose.pose.position.z = 0.0
        
        # Face towards the frontier (simple orientation)
        goal_pose.pose.orientation.x = 0.0
        goal_pose.pose.orientation.y = 0.0
        goal_pose.pose.orientation.z = 0.0
        goal_pose.pose.orientation.w = 1.0
        
        return goal_pose
    
    def send_navigation_goal(self, goal_pose):
        """Send navigation goal to Nav2"""
        if not self.nav_action_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().warn("⏳ Navigation action server not ready yet, will retry...")
            return False
        
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = goal_pose
        
        self.get_logger().info(f"Sending goal: ({goal_pose.pose.position.x:.2f}, {goal_pose.pose.position.y:.2f})")
        
        # Send goal
        future = self.nav_action_client.send_goal_async(goal_msg)
        
        # Store current goal
        self.current_goal = goal_pose
        
        # Publish goal for visualization
        self.goal_publisher.publish(goal_pose)
        
        return True    

    def publish_frontier_markers(self, frontiers):
        """Publish frontier markers for visualization in RViz"""
        marker_array = MarkerArray()
        
        for i, (fx, fy) in enumerate(frontiers):
            marker = Marker()
            marker.header.frame_id = self.map_frame
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = "frontiers"
            marker.id = i
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            
            marker.pose.position.x = fx
            marker.pose.position.y = fy
            marker.pose.position.z = 0.1
            
            marker.pose.orientation.w = 1.0
            
            marker.scale.x = 0.2
            marker.scale.y = 0.2
            marker.scale.z = 0.2
            
            marker.color.r = 1.0
            marker.color.g = 0.0
            marker.color.b = 0.0
            marker.color.a = 0.8
            
            marker_array.markers.append(marker)
        
        self.frontier_publisher.publish(marker_array)
    
    def is_exploration_complete(self, frontier_count):
        """Determine if exploration is complete based on multiple criteria"""
        current_time = self.get_clock().now()
        
        # Check if no frontiers found
        if frontier_count == 0:
            self.get_logger().info("✅ No frontiers found - exploration complete!")
            return True
        
        # Check if we're making progress
        if frontier_count == self.last_frontier_count:
            self.no_progress_count += 1
        else:
            self.no_progress_count = 0
        
        self.last_frontier_count = frontier_count
        
        # If no progress for too long, consider exploration complete
        if self.no_progress_count > 10:  # 20 seconds of no progress
            self.get_logger().info("✅ No progress in exploration - considering complete!")
            return True
        
        # Check exploration time limit (optional safety)
        exploration_duration = (current_time - self.exploration_start_time).nanoseconds / 1e9
        if exploration_duration > 1800:  # 30 minutes max
            self.get_logger().info("✅ Exploration time limit reached!")
            return True
        
        return False
    
    def is_goal_timeout(self):
        """Check if current goal has timed out"""
        if self.goal_start_time is None:
            return False
        
        current_time = self.get_clock().now()
        goal_duration = (current_time - self.goal_start_time).nanoseconds / 1e9
        
        return goal_duration > self.goal_timeout
    
    def add_visited_frontier(self, x, y):
        """Add a frontier to the visited list"""
        self.visited_frontiers.append((x, y))
        # Keep only recent visited frontiers (last 20)
        if len(self.visited_frontiers) > 20:
            self.visited_frontiers.pop(0)
    
    def is_frontier_recently_visited(self, fx, fy, threshold=2.0):
        """Check if a frontier was recently visited"""
        for vx, vy in self.visited_frontiers:
            distance = np.sqrt((fx - vx)**2 + (fy - vy)**2)
            if distance < threshold:
                return True
        return False
    
    def exploration_loop(self):
        """Enhanced exploration loop with better state management"""
        if self.exploration_complete:
            self.get_logger().info("🏁 Exploration already complete, stopping.")
            return
        
        if self.map_data is None:
            self.get_logger().info("⏳ Waiting for map data from SLAM...")
            return
        
        # Get robot position
        robot_x, robot_y = self.get_robot_position()
        if robot_x is None:
            self.get_logger().info("⏳ Waiting for robot localization...")
            return
        
        self.get_logger().debug(f"🤖 Robot position: ({robot_x:.2f}, {robot_y:.2f})")
        
        # Find frontiers
        frontier_points = self.find_frontiers(self.map_data)
        self.get_logger().info(f"🔍 Found {len(frontier_points)} frontier points")
        
        # Check if exploration is complete
        if self.is_exploration_complete(len(frontier_points)):
            self.exploration_complete = True
            self.get_logger().info("🎉 Exploration complete! All areas have been mapped.")
            return
        
        # Cluster frontiers
        clustered_frontiers = self.cluster_frontiers(frontier_points)
        self.get_logger().info(f"📊 Clustered into {len(clustered_frontiers)} frontier groups")
        
        # Publish frontiers for visualization
        self.publish_frontier_markers(clustered_frontiers)
        
        # Check current goal status
        if self.current_goal is not None:
            # Check if goal timed out
            if self.is_goal_timeout():
                self.get_logger().warn("Goal timed out, selecting new target")
                self.current_goal = None
                self.goal_start_time = None
            else:
                # Check if we're close to the current goal
                goal_x = self.current_goal.pose.position.x
                goal_y = self.current_goal.pose.position.y
                distance_to_goal = np.sqrt((robot_x - goal_x)**2 + (robot_y - goal_y)**2)
                
                if distance_to_goal < 1.0:  # Close enough to goal
                    self.add_visited_frontier(goal_x, goal_y)
                    self.current_goal = None
                    self.goal_start_time = None
                    self.get_logger().info("✅ Reached exploration goal")
                else:
                    # Still navigating to current goal
                    self.get_logger().debug(f"Navigating to goal, distance: {distance_to_goal:.2f}m")
                    return
        
        # Filter out recently visited frontiers
        available_frontiers = []
        for frontier in clustered_frontiers:
            if not self.is_frontier_recently_visited(frontier[0], frontier[1]):
                available_frontiers.append(frontier)
        
        if not available_frontiers:
            self.get_logger().info("All nearby frontiers recently visited, waiting...")
            return
        
        # Select next frontier to explore
        best_frontier = self.select_best_frontier(available_frontiers, robot_x, robot_y)
        
        if best_frontier is None:
            self.get_logger().info("No suitable frontiers found")
            return
        
        # Create and send navigation goal
        goal_pose = self.create_goal_pose(best_frontier[0], best_frontier[1])
        self.get_logger().info(f"🎯 Setting new exploration goal: ({best_frontier[0]:.2f}, {best_frontier[1]:.2f})")
        if self.send_navigation_goal(goal_pose):
            self.goal_start_time = self.get_clock().now()
            self.get_logger().info("🚀 Robot should start moving towards the exploration goal!")

def main(args=None):
    rclpy.init(args=args)
    
    explorer = AutonomousExplorer()
    
    # Use MultiThreadedExecutor for concurrent operations
    executor = MultiThreadedExecutor()
    executor.add_node(explorer)
    
    try:
        explorer.get_logger().info("Starting autonomous exploration...")
        executor.spin()
    except KeyboardInterrupt:
        explorer.get_logger().info("Exploration interrupted by user")
    finally:
        explorer.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()