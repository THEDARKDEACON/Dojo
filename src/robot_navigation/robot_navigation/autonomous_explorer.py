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

from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy

import numpy as np
import cv2
from scipy import ndimage
from sklearn.cluster import DBSCAN
import math

from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import PoseStamped, Point, Twist
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import Header, String
from visualization_msgs.msg import Marker, MarkerArray

import tf2_ros
import tf2_geometry_msgs
from tf2_ros import TransformException


class AutonomousExplorer(Node):
    def __init__(self):
        super().__init__('autonomous_explorer')
        
        # Parameters
        self.declare_parameter('exploration_radius', 200.0)
        self.declare_parameter('min_frontier_size', 5)
        self.declare_parameter('robot_radius', 0.22)
        self.declare_parameter('goal_timeout', 15.0)
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('gaussian_splat_mode', False)
        self.declare_parameter('exploration_interval', 0.5)  # Check every 0.5 seconds
        
        self.exploration_radius = self.get_parameter('exploration_radius').value
        self.min_frontier_size = self.get_parameter('min_frontier_size').value
        self.robot_radius = self.get_parameter('robot_radius').value
        self.goal_timeout = self.get_parameter('goal_timeout').value
        self.map_frame = self.get_parameter('map_frame').value
        self.base_frame = self.get_parameter('base_frame').value
        
        # Robust boolean parsing (handle "False" string vs False boolean)
        gs_param = self.get_parameter('gaussian_splat_mode').value
        self.gaussian_splat_mode = str(gs_param).lower() == 'true'
        
        self.exploration_interval = self.get_parameter('exploration_interval').value
        
        # State variables
        self.map_data = None
        self.current_goal = None
        self.exploration_complete = False
        self.goal_start_time = None
        self.visited_frontiers = []  # Track visited locations
        self.exploration_start_time = self.get_clock().now()
        self.last_frontier_count = 0
        self.last_frontier_count = 0
        self.no_progress_count = 0
        self.failed_frontiers = []  # Track failed/unreachable frontiers
        self.initial_pose_received = False
        self.frontiers = []  # Track current frontiers
        self.last_status = "Initializing..."
        self.frontier_retries = {}  # Track retries for failed frontiers: (x_key, y_key) -> count
        
        # Callback group for concurrent operations
        self.callback_group = ReentrantCallbackGroup()
        
        # TF2 buffer and listener
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)    
    
        # QoS Profile for map subscription (Transient Local to get last map)
        map_qos = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE
        )

        # Subscribers
        self.map_subscriber = self.create_subscription(
            OccupancyGrid,
            '/map',
            self.map_callback,
            map_qos,
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

        self.cmd_vel_publisher = self.create_publisher(
            Twist,
            '/cmd_vel_nav',
            10
        )
        
        # Action client for navigation
        self.nav_action_client = ActionClient(
            self,
            NavigateToPose,
            '/navigate_to_pose',
            callback_group=self.callback_group
        )
        
        self.debug_publisher = self.create_publisher(
            String,
            '/explorer_debug',
            10
        )
        
        # Timer for exploration loop
        self.get_logger().info(f"⏱️ Exploration loop running every {self.exploration_interval} seconds")
        self.exploration_timer = self.create_timer(
            self.exploration_interval,
            self.exploration_loop,
            callback_group=self.callback_group
        )
        
        self.get_logger().info("🤖 Autonomous Explorer initialized - Starting frontier-based exploration!")
        self.get_logger().info(f"📊 Configuration: radius={self.exploration_radius}m, min_frontier_size={self.min_frontier_size}")
        self.get_logger().info(f"📸 Gaussian Splat Mode: {self.gaussian_splat_mode} (Type: {type(self.gaussian_splat_mode)})")
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
            
            self.initial_pose_received = True
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
        self.get_logger().debug(f"Map Data Values: {np.unique(grid)}")
        
        # Create binary maps
        free_space = (grid == 0).astype(np.uint8)  # Free space
        # Handle unknown space (can be -1 or 255 depending on interpretation)
        unknown_space = np.logical_or(grid == -1, grid == 255).astype(np.uint8)
        occupied_space = (grid == 100).astype(np.uint8)  # Obstacles
        
        # Apply morphological operations to clean up the map
        kernel = np.ones((3, 3), np.uint8)
        
        # Clean free space (remove noise) - ONLY use CLOSE to fill holes, avoid OPEN which erodes boundaries
        # free_space = cv2.morphologyEx(free_space, cv2.MORPH_OPEN, kernel) 
        free_space = cv2.morphologyEx(free_space, cv2.MORPH_CLOSE, kernel)
        
        self.get_logger().debug(f"Grid Stats: Free={np.sum(free_space)}, Unknown={np.sum(unknown_space)}, Occupied={np.sum(occupied_space)}")
        
        # Find frontiers using multiple methods for robustness
        
        # Method 1: Dilation-based frontier detection - Increase iterations to ensure overlap
        free_dilated = cv2.dilate(free_space, kernel, iterations=2)
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
        
        self.get_logger().debug(f"Frontier Candidates: Method1={np.sum(frontiers_method1)}, Method2={np.sum(frontiers_method2)}, Combined={np.sum(frontiers)}")
        
        # Find frontier coordinates
        frontier_coords = np.where(frontiers)
        
        if len(frontier_coords[0]) == 0:
            return []
        
        # Convert grid coordinates to world coordinates
        frontier_points = []
        for i in range(len(frontier_coords[0])):
            grid_x = frontier_coords[1][i]
            grid_y = frontier_coords[0][i]
            
            # Convert to world coordinates (Standard ROS: origin is bottom-left)
            world_x = origin.position.x + grid_x * resolution
            world_y = origin.position.y + grid_y * resolution  # Fixed Y-flip bug
            
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
        grid_y = int((frontier_y - origin.position.y) / resolution)  # Fixed Y-flip bug
        
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
        grid_y = int((frontier_y - origin.position.y) / resolution)
        
        if grid_x < 0 or grid_x >= width or grid_y < 0 or grid_y >= height:
            return False
        
        grid = np.array(self.map_data.data).reshape((height, width))
        # Increase safety margin to match Nav2 inflation radius (0.45m)
        # robot_radius (0.22) * 1.2 ~= 0.26m (Significantly reduced for "Braver" exploration)
        safety_radius = int(self.robot_radius * 1.05 / resolution)
        
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
        
        rejected_distance = 0
        rejected_safety = 0
        min_rejected_dist = float('inf')
        max_rejected_dist = float('-inf')
        
        for i, frontier in enumerate(frontiers):
            fx, fy = frontier
            
            # Calculate distance to frontier
            distance = np.sqrt((fx - robot_x)**2 + (fy - robot_y)**2)
            
            # Skip if too close or too far
            if distance < 0.5 or distance > self.exploration_radius:
                rejected_distance += 1
                min_rejected_dist = min(min_rejected_dist, distance)
                max_rejected_dist = max(max_rejected_dist, distance)
                self.get_logger().debug(f"Frontier {i} rejected: dist={distance:.2f} (valid range: 0.5-{self.exploration_radius})")
                continue
            
            # Check if frontier is safe
            if not self.is_frontier_safe(fx, fy):
                rejected_safety += 1
                min_rejected_dist = min(min_rejected_dist, distance)
                max_rejected_dist = max(max_rejected_dist, distance)
                self.get_logger().debug(f"Frontier {i} at ({fx:.2f}, {fy:.2f}) rejected: UNSAFE (Obstacle nearby)")
                continue
            
            # Calculate information gain
            info_gain = self.calculate_information_gain(fx, fy)
            
            # Multi-criteria scoring
            # User Request: Prioritize closest frontiers heavily
            # Score = -Distance * 2.0 + InfoGain * 0.5
            distance_score = -distance * 2.0
            info_score = info_gain * 0.5
            
            # Combined score
            score = distance_score + info_score

            # CONSISTENCY BIAS (Hysteresis):
            # If we have an active goal, give a massive bonus to frontiers near it.
            # This prevents the "Jumping" behavior where the robot switches targets mid-path.
            if self.current_goal:
                curr_x = self.current_goal.pose.position.x
                curr_y = self.current_goal.pose.position.y
                dist_to_current = np.sqrt((fx - curr_x)**2 + (fy - curr_y)**2)
                
                if dist_to_current < 2.0: # If within 2m of current goal
                     score += 5.0 # Large bonus to "stick" to the plan
            
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
        else:
            msg = f"No suitable frontier found. Rejected: {rejected_distance} (dist), {rejected_safety} (safety)."
            if min_rejected_dist != float('inf'):
                msg += f" Min Dist: {min_rejected_dist:.2f}m"
            self.get_logger().warn(msg)
            # Update status for Dashboard visibility
            self.last_status = f"Rejected all (Min Dist: {min_rejected_dist:.2f}m)"
        
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
        """Send navigation goal to Nav2 with callbacks"""
        if not self.nav_action_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().warn("⏳ Navigation action server not ready yet, will retry...")
            return False
        
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = goal_pose
        
        self.get_logger().info(f"Sending goal: ({goal_pose.pose.position.x:.2f}, {goal_pose.pose.position.y:.2f})")
        
        # Send goal with callbacks
        self._send_goal_future = self.nav_action_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        self._send_goal_future.add_done_callback(self.goal_response_callback)
        
        # Store current goal
        self.current_goal = goal_pose
        
        # Publish goal for visualization
        self.goal_publisher.publish(goal_pose)
        
        return True

    def goal_response_callback(self, future):
        """Handle goal acceptance/rejection"""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('Goal rejected :(')
            self.current_goal = None
            return

        self.get_logger().info('Goal accepted :)')
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        """Handle navigation result"""
        result = future.result().result
        status = future.result().status
        
        # STATUS_SUCCEEDED = 4, STATUS_ABORTED = 5, STATUS_CANCELED = 6
        if status == 4:
            self.get_logger().info('✅ Navigation succeeded!')
            if self.current_goal:
                self.add_visited_frontier(
                    self.current_goal.pose.position.x,
                    self.current_goal.pose.position.y
                )
                if self.gaussian_splat_mode:
                    self.perform_spin()
        elif status == 6:
            self.get_logger().info('⚠️ Navigation canceled (likely by user/teleop)')
            # Do NOT add to visited/failed, just reset so we can pick a new goal
        else:
            self.get_logger().warn(f'❌ Navigation failed with status: {status}')
            if self.current_goal:
                # Round coordinates to group nearby failures (10cm precision)
                gx = round(self.current_goal.pose.position.x, 1)
                gy = round(self.current_goal.pose.position.y, 1)
                key = (gx, gy)
                
                # Increment retry count
                retries = self.frontier_retries.get(key, 0) + 1
                self.frontier_retries[key] = retries
                
                if retries >= 3:
                    self.get_logger().warn(f'💀 Frontier at ({gx}, {gy}) failed 3 times. Blacklisting.')
                    # Add to failed frontiers so we don't retry immediately
                    self.failed_frontiers.append((
                        self.current_goal.pose.position.x,
                        self.current_goal.pose.position.y
                    ))
                    # Keep only recent failed frontiers
                    if len(self.failed_frontiers) > 20:
                        self.failed_frontiers.pop(0)
                else:
                    self.get_logger().info(f'🔄 Frontier failed (Attempt {retries}/3) - Will retry.')
                    # Do NOT add to failed_frontiers yet
        
        # Clear current goal to allow selecting a new one
        self.current_goal = None
        self.goal_start_time = None

    def feedback_callback(self, feedback_msg):
        """Handle navigation feedback"""
        # feedback = feedback_msg.feedback
        # self.get_logger().debug(f'Received feedback: {feedback}')
        pass    

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
            self.no_progress_count += 1
            if self.no_progress_count > 5: # Require 5 consecutive checks (2.5s) to confirm empty
                self.get_logger().info("✅ No frontiers found - exploration complete!")
                return True
            return False
        
        # If we have an active goal, we are not done (unless we are stuck, which is handled by goal timeout)
        if self.current_goal is not None:
            self.no_progress_count = 0
            return False
        
        # Check if we're making progress
        if frontier_count == self.last_frontier_count:
            self.no_progress_count += 1
        else:
            self.no_progress_count = 0
        
        self.last_frontier_count = frontier_count
        
        # If no progress for too long, consider exploration complete
        if self.no_progress_count > 60:  # Increased to 30 seconds
            self.get_logger().warn(f"⚠️ No progress in exploration ({self.no_progress_count} checks). Robot might be stuck.")
            # Do NOT return True here, just warn. 
            # We might want to trigger a recovery behavior here in the future.
            return False
        
        # Check exploration time limit (optional safety)
        exploration_duration = (current_time - self.exploration_start_time).nanoseconds / 1e9
        if exploration_duration > 3600:  # 60 minutes max
            self.get_logger().info("✅ Exploration time limit reached!")
            return True
        
        return False
    
    def calculate_map_saturation(self):
        """Calculate the saturation (completeness) of the map within the explored bounding box"""
        if self.map_data is None:
            return 1.0 # Assume complete if no map to prevent stuck loop
            
        width = self.map_data.info.width
        height = self.map_data.info.height
        resolution = self.map_data.info.resolution
        origin_x = self.map_data.info.origin.position.x
        origin_y = self.map_data.info.origin.position.y
        data = np.array(self.map_data.data).reshape((height, width))
        
        # Find bounding box of known space (Free or Occupied)
        # 0 = Free, 100 = Occupied, -1 = Unknown
        known_mask = (data != -1)
        if not np.any(known_mask):
            return 0.0
            
        rows, cols = np.where(known_mask)
        min_row, max_row = np.min(rows), np.max(rows)
        min_col, max_col = np.min(cols), np.max(cols)
        
        # Calculate saturation within this bounding box
        # Saturation = (Count of Known Cells) / (Total Cells in Bounding Box)
        # This checks if there are "holes" of unknown space inside the mapped area
        bbox_area = (max_row - min_row + 1) * (max_col - min_col + 1)
        known_count = np.sum(known_mask[min_row:max_row+1, min_col:max_col+1])
        
        saturation = known_count / bbox_area if bbox_area > 0 else 0.0
        
        self.get_logger().info(f"📊 Map Saturation: {saturation*100:.1f}% (BBox: {max_col-min_col}x{max_row-min_row})")
        return saturation

    def generate_loop_closure_goal(self):
        """Generate a random goal within known free space to force loop closure/re-visiting"""
        if self.map_data is None:
            return None
            
        width = self.map_data.info.width
        height = self.map_data.info.height
        data = np.array(self.map_data.data).reshape((height, width))
        resolution = self.map_data.info.resolution
        origin_x = self.map_data.info.origin.position.x
        origin_y = self.map_data.info.origin.position.y
        
        # Find all free cells
        free_rows, free_cols = np.where(data == 0)
        
        if len(free_rows) == 0:
            return None
            
        # Try different distance requirements (from far to near)
        min_distances = [2.0, 1.0, 0.5]
        
        for min_dist in min_distances:
            for _ in range(50): # 50 attempts per distance tier
                idx = np.random.randint(0, len(free_rows))
                r, c = free_rows[idx], free_cols[idx]
                
                # Convert to world coordinates
                wx = origin_x + (c + 0.5) * resolution
                wy = origin_y + (r + 0.5) * resolution
                
                # Check distance from current pose
                if self.current_pose:
                    robot_x = self.current_pose.position.x
                    robot_y = self.current_pose.position.y
                    dist = np.sqrt((wx - robot_x)**2 + (wy - robot_y)**2)
                    if dist < min_dist:
                        continue
                        
                # Found a valid point!
                return (wx, wy)
            
        return None

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
    
    def is_frontier_recently_visited(self, fx, fy, visited_threshold=2.0, failed_threshold=0.75):
        """Check if a frontier was recently visited or failed"""
        # Check visited (Keep large radius to avoid re-exploring known areas)
        for vx, vy in self.visited_frontiers:
            distance = np.sqrt((fx - vx)**2 + (fy - vy)**2)
            if distance < visited_threshold:
                return True
        
        # Check failed (Use smaller radius to allow retrying nearby points)
        for fax, fay in self.failed_frontiers:
            distance = np.sqrt((fx - fax)**2 + (fy - fay)**2)
            if distance < failed_threshold:
                return True
                
        return False

    def perform_spin(self):
        """Perform a 360-degree spin to capture data for Gaussian Splatting"""
        self.get_logger().info("🔄 Performing Gaussian Splat spin...")
        twist = Twist()
        twist.angular.z = 0.5  # rad/s

        # Spin for approx 12.5 seconds (2*pi / 0.5 ~= 12.56)
        # We'll do it in short bursts to allow callbacks to process
        # Ideally this should be async, but for simplicity we block slightly or use a state machine
        # For this simple implementation, we'll just publish for a duration
        
        # Note: In a real async node, blocking is bad. But here we are inside a timer callback.
        # A better approach would be to have a 'SPINNING' state.
        # However, to keep it simple and robust for this demo:
        
        import time
        start_time = time.time()
        while time.time() - start_time < 13.0:
            self.cmd_vel_publisher.publish(twist)
            time.sleep(0.1)
        
        # Stop
        twist.angular.z = 0.0
        self.cmd_vel_publisher.publish(twist)
        self.get_logger().info("✅ Spin complete")
    
    def exploration_loop(self):
        """
        Main exploration loop
        """
        # Get robot position first to update initial_pose_received
        robot_x, robot_y = self.get_robot_position()
        
        # Calculate saturation for display
        current_saturation = self.calculate_map_saturation()
        
        # Publish debug status
        status_msg = f"State: {'GOAL_ACTIVE' if self.current_goal else 'IDLE'} | " \
                     f"Pose: {'YES' if self.initial_pose_received else 'NO'} | " \
                     f"Map: {'YES' if self.map_data else 'NO'} | " \
                     f"Frontiers: {len(self.frontiers)} | " \
                     f"Saturation: {current_saturation:.2f} | " \
                     f"Status: {self.last_status}"
        self.debug_publisher.publish(String(data=status_msg))

        if not self.initial_pose_received:
            self.get_logger().warn("Waiting for initial pose...")
            return
        
        if self.exploration_complete:
            self.get_logger().info("🏁 Exploration complete (idle)... checking for new frontiers.")
            # Do not return, continue to check for new frontiers
            # return
        
        if self.map_data is None:
            self.get_logger().info("⏳ Waiting for map data from SLAM...")
            return
        
        start_time = self.get_clock().now()
        
        if robot_x is None:
            self.get_logger().info("⏳ Waiting for robot localization...")
            return
        
        self.get_logger().debug(f"🤖 Robot position: ({robot_x:.2f}, {robot_y:.2f})")
        
        # Find frontiers
        frontier_points = self.find_frontiers(self.map_data)
        self.frontiers = frontier_points
        self.get_logger().info(f"🔍 Found {len(frontier_points)} frontier points")
        
        # Check if exploration is complete
        # is_exploration_complete returns True if no frontiers found for 5 consecutive checks
        if self.is_exploration_complete(len(frontier_points)):
            
            # Additional Check: Map Saturation / Confidence
            saturation = self.calculate_map_saturation()
            confidence_threshold = 0.90 # 90% saturation
            
            if saturation < confidence_threshold and saturation > 0.1: # >0.1 to avoid empty map issues
                self.get_logger().info(f"🔄 Frontiers exhausted but Map Saturation {saturation*100:.1f}% < {confidence_threshold*100}%.")
                self.get_logger().info("   >> Generating Loop Closure Goal to improve map quality...")
                self.last_status = "Improving Map Quality"
                
                lc_goal = self.generate_loop_closure_goal()
                if lc_goal:
                    self.get_logger().info(f"📍 Loop Closure Goal: ({lc_goal[0]:.2f}, {lc_goal[1]:.2f})")
                    self.move_to_goal(lc_goal[0], lc_goal[1])
                    self.exploration_complete = False # Reset flag as we are still working
                    return
                else:
                    self.get_logger().info("⚠️ Could not generate valid loop closure goal.")
            
            if not self.exploration_complete:
                self.get_logger().info("🎉 Exploration complete! All areas have been mapped and confidence threshold met.")
                self.last_status = "Exploration Complete"
                self.exploration_complete = True
            
            # Don't return, keep checking in case new frontiers appear
        else:
            # If we found frontiers and were previously complete, resume!
            if self.exploration_complete:
                self.get_logger().info("🔍 New frontiers detected - Resuming exploration!")
                self.exploration_complete = False
        
        # Cluster frontiers
        clustered_frontiers = self.cluster_frontiers(frontier_points)
        self.get_logger().info(f"📊 Clustered into {len(clustered_frontiers)} frontier groups")
        
        # Publish frontiers for visualization
        self.publish_frontier_markers(clustered_frontiers)
        
        # Check current goal status
        if self.current_goal is not None:
            # Check if goal timed out
            if self.is_goal_timeout():
                self.get_logger().warn("Goal timed out, cancelling and selecting new target")
                # Cancel the goal explicitly (TODO: cancel action handle)
                # For now we just reset local state and blacklist
                self.failed_frontiers.append((
                    self.current_goal.pose.position.x,
                    self.current_goal.pose.position.y
                ))
                self.current_goal = None
                self.goal_start_time = None
            else:
                # We are relying on callbacks now, but we can still log progress
                self.get_logger().debug("Navigating to goal...")
                return
        
        # Filter out recently visited frontiers
        available_frontiers = []
        for frontier in clustered_frontiers:
            if not self.is_frontier_recently_visited(frontier[0], frontier[1]):
                available_frontiers.append(frontier)
        
        if not available_frontiers:
            self.last_status = "All frontiers visited/failed"
            self.get_logger().info(f"All {len(clustered_frontiers)} nearby frontiers are in blacklist (visited/failed).")
            
            # Fallback: Wandering (Same logic as when frontiers are rejected)
            saturation = self.calculate_map_saturation()
            if saturation < 0.98:
                 self.get_logger().info(f"🔄 All Frontiers Failed. Saturation {saturation*100:.1f}%. Triggering Wandering.")
                 lc_goal = self.generate_loop_closure_goal()
                 if lc_goal:
                      self.get_logger().info(f"📍 Wandering Goal: ({lc_goal[0]:.2f}, {lc_goal[1]:.2f})")
                      self.move_to_goal(lc_goal[0], lc_goal[1])
                      self.last_status = "Wandering (All Failed)"
                      # Clear blacklist AFTER setting goal so we don't immediately re-fail
                      self.failed_frontiers = [] 
                      return

            self.get_logger().info("Clearing failed frontiers list to retry...")
            self.failed_frontiers = []
            return
        
        # Select next frontier to explore
        best_frontier = self.select_best_frontier(available_frontiers, robot_x, robot_y)
        
        if best_frontier is None:
            self.last_status = "No suitable frontier (check logs)"
            self.get_logger().info("No suitable frontiers found (all rejected by safety check).")
            
            # Fallback: Check Map Saturation to trigger Loop Closure / Wandering
            # This handles the case where frontiers exist but are all "unsafe" due to map noise
            # Fallback: Check Map Saturation OR just Wander if stuck
            # If we have frontiers but cannot reach them, moving to a random open spot often changes the perspective
            saturation = self.calculate_map_saturation()
            
            # If map is not perfect (or even if it is, but we are stuck), try wandering
            if saturation < 0.98: 
                self.get_logger().info(f"🔄 Stalled with Saturation {saturation*100:.1f}%. Triggering Loop Closure Wandering.")
                lc_goal = self.generate_loop_closure_goal()
                if lc_goal:
                     self.get_logger().info(f"📍 Wandering Goal: ({lc_goal[0]:.2f}, {lc_goal[1]:.2f})")
                     self.move_to_goal(lc_goal[0], lc_goal[1])
                     self.last_status = "Wandering (Stalled)"
                     return
            
            return
        
        # Create and send navigation goal
        goal_pose = self.create_goal_pose(best_frontier[0], best_frontier[1])
        self.get_logger().info(f"🎯 Setting new exploration goal: ({best_frontier[0]:.2f}, {best_frontier[1]:.2f})")
        if self.send_navigation_goal(goal_pose):
            self.last_status = "Goal sent to Nav2"
            self.goal_start_time = self.get_clock().now()
            self.get_logger().info("🚀 Robot should start moving towards the exploration goal!")
        else:
            self.last_status = "Nav2 Action Server not ready"
        
        duration = (self.get_clock().now() - start_time).nanoseconds / 1e9
        self.get_logger().debug(f"⚡ Exploration loop took {duration:.3f} seconds")

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
