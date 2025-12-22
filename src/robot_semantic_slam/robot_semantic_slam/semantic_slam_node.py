#!/usr/bin/env python3
"""
Semantic SLAM Node - Cutting-edge object-aware mapping and navigation
Integrates YOLO object detection with SLAM for intelligent spatial understanding
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from sensor_msgs.msg import Image, LaserScan, PointCloud2, PointField
from geometry_msgs.msg import PoseStamped, Twist
from vision_msgs.msg import Detection2DArray, Detection2D
from nav_msgs.msg import OccupancyGrid, Path
from std_msgs.msg import String, Float32
from visualization_msgs.msg import Marker, MarkerArray
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatus
import cv2
from cv_bridge import CvBridge
import numpy as np
import math
import json
import os
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from scipy.spatial import KDTree
import tf2_ros
import tf2_geometry_msgs
import sys
import struct
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError as e:
    print(f"DEBUG: Failed to import ultralytics: {e}", file=sys.stderr)
    print(f"DEBUG: sys.executable: {sys.executable}", file=sys.stderr)
    print(f"DEBUG: sys.path: {sys.path}", file=sys.stderr)
    YOLO_AVAILABLE = False
    YOLO = None

class SemanticSLAMNode(Node):
    """Advanced Semantic SLAM with object-aware navigation"""
    
    def __init__(self):
        super().__init__('semantic_slam_node')
        
        # Initialize YOLO model with optimization
        if YOLO_AVAILABLE:
            try:
                self.yolo_model = YOLO('yolov8n.pt')  # Lightweight model for real-time
                self.yolo_model.fuse()  # Fuse model layers for faster inference
            except Exception as e:
                self.get_logger().warn(f"Failed to load YOLO model: {e}. YOLO detection disabled.")
                self.yolo_model = None
        else:
            self.get_logger().warn("YOLO not available. Object detection will be disabled.")
            self.yolo_model = None
        self.bridge = CvBridge()
        
        # Frame skipping for performance optimization
        self.declare_parameter('detection_frequency', 5.0)  # Hz (reduced from 10Hz)
        self.declare_parameter('skip_frames', 2)  # Process every Nth frame
        self.detection_frequency = self.get_parameter('detection_frequency').value
        self.skip_frames = self.get_parameter('skip_frames').value
        self.frame_counter = 0
        
        # Semantic map storage with persistence
        self.semantic_map = {}  # {object_id: {class, position, confidence, timestamp, last_seen, detections}}
        self.object_counter = 0
        
        # Persistence parameters
        self.declare_parameter('persistence_file', 'semantic_map_persistent.pkl')
        self.declare_parameter('object_timeout_seconds', 300.0)  # 5 minutes
        self.declare_parameter('confidence_decay_rate', 0.95)  # 5% decay per minute
        self.declare_parameter('min_confidence_threshold', 0.3)  # Remove objects below this
        self.declare_parameter('merge_distance_threshold', 1.0)  # meters
        
        self.persistence_file = self.get_parameter('persistence_file').value
        self.object_timeout = self.get_parameter('object_timeout_seconds').value
        self.confidence_decay_rate = self.get_parameter('confidence_decay_rate').value
        self.min_confidence = self.get_parameter('min_confidence_threshold').value
        self.merge_distance = self.get_parameter('merge_distance_threshold').value
        
        # Spatial indexing for fast nearest-neighbor queries
        self.spatial_index = None  # KDTree for efficient spatial queries
        self.spatial_index_dirty = True  # Flag to rebuild index when map changes
        
        # Load persistent semantic map from disk
        self.load_semantic_map()
        
        # Build initial spatial index
        self.rebuild_spatial_index()
        
        # Publishers
        self.semantic_map_pub = self.create_publisher(String, '/semantic_map', 10)
        self.annotated_image_pub = self.create_publisher(Image, '/semantic_image', 10)
        self.navigation_goal_pub = self.create_publisher(PoseStamped, '/navigate_to_object', 10)
        self.navigation_status_pub = self.create_publisher(String, '/navigation_status', 10)
        self.navigation_progress_pub = self.create_publisher(Float32, '/navigation_progress', 10)
        self.marker_pub = self.create_publisher(MarkerArray, '/semantic_markers', 10)
        
        # Nav2 Action Client for goal-based navigation
        self.nav2_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        
        # Navigation state
        self.current_navigation_goal = None
        self.navigation_in_progress = False
        self.multi_step_goals = []  # Queue for multi-step navigation
        
        # Subscribers
        self.image_sub = self.create_subscription(Image, '/camera/color/image_raw', self.image_callback, 10)
        self.scan_sub = self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        self.map_sub = self.create_subscription(OccupancyGrid, '/map', self.map_callback, 10)
        self.pose_sub = self.create_subscription(PoseStamped, '/robot_pose', self.pose_callback, 10)
        
        # Command interface
        self.command_sub = self.create_subscription(String, '/semantic_command', self.command_callback, 10)
        
        # TF2 for coordinate transformations
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        
        # Current robot state
        self.current_pose = None
        self.current_map = None
        self.current_scan = None
        
        # Timers for periodic operations (optimized frequencies)
        self.publish_timer = self.create_timer(0.2, self.publish_semantic_map)  # 5Hz for real-time updates
        self.cleanup_timer = self.create_timer(120.0, self.cleanup_old_objects)  # Every 2 minutes (reduced frequency)
        self.persistence_timer = self.create_timer(60.0, self.save_semantic_map)  # Every 60 seconds (reduced frequency)
        
        self.get_logger().info("🚀 Semantic SLAM Node initialized with persistence - Ready for object-aware navigation!")
        self.get_logger().info(f"📁 Persistence file: {self.persistence_file}")
        self.get_logger().info(f"⏱️  Object timeout: {self.object_timeout}s ({self.object_timeout/60:.1f} minutes)")
        self.get_logger().info(f"📉 Confidence decay: {self.confidence_decay_rate} per minute")
        self.get_logger().info(f"🗑️  Min confidence threshold: {self.min_confidence}")

        # Semantic Obstacle Publisher (PointCloud2)
        self.obstacle_pub = self.create_publisher(PointCloud2, '/semantic_obstacles', 10)
        
        # New Publisher strictly for Text Labels
        self.label_pub = self.create_publisher(MarkerArray, '/semantic_labels', 10)
        
        # Object Physical Dimensions (Radius in meters)
        self.object_dimensions = {
            'chair': 0.35,
            'person': 0.30,
            'table': 0.60,
            'desk': 0.60,
            'potted plant': 0.30,
            'couch': 0.80,
            'sofa': 0.80,
            'bed': 1.00,
            'tv': 0.20,
            'monitor': 0.20
        }
        self.default_object_radius = 0.30
        
    def publish_semantic_obstacles(self):
        """Generate and publish a PointCloud2 representing semantic barriers"""
        if not self.semantic_map:
            return

        points = []
        current_time = self.get_clock().now()
        
        # Generate points for each active object
        for obj_id, obj_data in self.semantic_map.items():
            # Get physical radius
            radius = self.object_dimensions.get(obj_data['class'], self.default_object_radius)
            x_center = obj_data['x']
            y_center = obj_data['y']
            
            # Generate a dense cylinder of points
            # Vertical layers
            for z in np.linspace(0.1, 1.5, 10): # 0.1m to 1.5m height
                # Angular steps for circle
                for angle in np.linspace(0, 2*np.pi, 16):
                    # Fill structure (hollow cylinder is enough for costmap)
                    px = x_center + radius * np.cos(angle)
                    py = y_center + radius * np.sin(angle)
                    points.append([px, py, z])
                    
                    # Add internal cross to ensure marking if radius is large
                    if radius > 0.4:
                         points.append([x_center, y_center, z])
        
        if not points:
            return

        # Create PointCloud2 message
        msg = PointCloud2()
        msg.header.stamp = current_time.to_msg()
        msg.header.frame_id = "map"
        
        msg.height = 1
        msg.width = len(points)
        
        # Define fields (x, y, z)
        msg.fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1)
        ]
        
        msg.is_bigendian = False
        msg.point_step = 12 # 3 * 4 bytes
        msg.row_step = msg.point_step * len(points)
        msg.is_dense = True
        
        # Pack data
        buffer = []
        for p in points:
            buffer.append(struct.pack('fff', p[0], p[1], p[2]))
        
        msg.data = b''.join(buffer)
        
        self.obstacle_pub.publish(msg)
    
    def image_callback(self, msg: Image):
        """Process camera images with YOLO detection (optimized with frame skipping)"""
        # Frame skipping optimization
        self.frame_counter += 1
        if self.frame_counter % self.skip_frames != 0:
            return
        
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            
            # Run YOLO detection with optimizations
            if self.yolo_model is None:
                return  # Skip detection if YOLO not available
            results = self.yolo_model(cv_image, verbose=False)  # Explicit device selection
            
            # Process detections
            annotated_image = cv_image.copy()
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Extract detection info
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        class_id = int(box.cls[0].cpu().numpy())
                        class_name = self.yolo_model.names[class_id]
                        
                        if confidence > 0.5:  # Confidence threshold
                            # Add to semantic map
                            self.add_object_to_map(class_name, (x1, y1, x2, y2), confidence, msg.header.stamp)
                            
                            # Annotate image
                            cv2.rectangle(annotated_image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                            cv2.putText(annotated_image, f"{class_name}: {confidence:.2f}", 
                                      (int(x1), int(y1-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Publish annotated image
            annotated_msg = self.bridge.cv2_to_imgmsg(annotated_image, "bgr8")
            annotated_msg.header = msg.header
            self.annotated_image_pub.publish(annotated_msg)
            
        except Exception as e:
            self.get_logger().error(f"Error in image processing: {e}")
    
    def add_object_to_map(self, class_name: str, bbox: Tuple, confidence: float, timestamp):
        """Add detected object to semantic map with world coordinates using LiDAR fusion"""
        if self.current_pose is None:
            return
        
        # Calculate object position in world coordinates using LiDAR-camera fusion
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        
        # Get accurate distance using LiDAR fusion
        distance = self.estimate_object_distance_with_lidar(center_x, center_y, bbox)
        
        # Calculate angle offset from camera center (assuming 640x480 resolution, 60° FOV)
        image_width = 640
        horizontal_fov = np.deg2rad(60)  # 60 degrees horizontal FOV
        angle_offset = ((center_x - image_width / 2) / (image_width / 2)) * (horizontal_fov / 2)
        
        # Transform to robot frame (camera is forward-facing)
        robot_frame_x = distance * np.cos(angle_offset)
        robot_frame_y = distance * np.sin(angle_offset)
        
        # Transform to world frame using robot pose
        robot_yaw = self.get_yaw_from_quaternion(self.current_pose.pose.orientation)
        world_x = self.current_pose.pose.position.x + robot_frame_x * np.cos(robot_yaw) - robot_frame_y * np.sin(robot_yaw)
        world_y = self.current_pose.pose.position.y + robot_frame_x * np.sin(robot_yaw) + robot_frame_y * np.cos(robot_yaw)
        
        # Check if object already exists nearby
        object_id = self.find_or_create_object(class_name, world_x, world_y, confidence, timestamp)
        
        self.get_logger().info(f"🎯 Detected {class_name} at ({world_x:.2f}, {world_y:.2f}) distance: {distance:.2f}m - ID: {object_id}")
    
    def estimate_object_distance_with_lidar(self, center_x: float, center_y: float, bbox: Tuple) -> float:
        """Estimate object distance using LiDAR-camera fusion"""
        if self.current_scan is None:
            # Fallback to simplified estimate if no LiDAR data
            self.get_logger().warn("No LiDAR data available, using fallback distance estimate")
            return 2.0
        
        # Camera parameters (assuming 640x480 resolution, 60° horizontal FOV)
        image_width = 640
        horizontal_fov = np.deg2rad(60)
        
        # Calculate angle corresponding to bounding box center
        angle_offset = ((center_x - image_width / 2) / (image_width / 2)) * (horizontal_fov / 2)
        
        # LiDAR scan parameters
        angle_min = self.current_scan.angle_min
        angle_max = self.current_scan.angle_max
        angle_increment = self.current_scan.angle_increment
        
        # Convert camera angle to LiDAR scan index
        # Assuming LiDAR is forward-facing and aligned with camera
        lidar_angle = angle_offset
        
        # Find corresponding LiDAR ray index
        if lidar_angle < angle_min or lidar_angle > angle_max:
            # Angle outside LiDAR range, use fallback
            return 2.0
        
        ray_index = int((lidar_angle - angle_min) / angle_increment)
        ray_index = max(0, min(ray_index, len(self.current_scan.ranges) - 1))
        
        # Get distance from LiDAR
        distance = self.current_scan.ranges[ray_index]
        
        # Validate distance
        if distance < self.current_scan.range_min or distance > self.current_scan.range_max:
            # Invalid reading, try averaging nearby rays
            distance = self.average_nearby_lidar_rays(ray_index, bbox)
        
        # Additional validation: check if distance makes sense for bounding box size
        if distance < 0.3 or distance > 10.0:
            # Unrealistic distance, use fallback
            self.get_logger().warn(f"Unrealistic distance {distance:.2f}m, using fallback")
            return 2.0
        
        return distance
    
    def average_nearby_lidar_rays(self, center_index: int, bbox: Tuple) -> float:
        """Average LiDAR rays corresponding to bounding box width"""
        if self.current_scan is None:
            return 2.0
        
        # Calculate bounding box width in pixels
        bbox_width = bbox[2] - bbox[0]
        
        # Estimate number of rays to average based on bbox width
        # Wider bbox = more rays to average
        image_width = 640
        horizontal_fov = np.deg2rad(60)
        bbox_angle_width = (bbox_width / image_width) * horizontal_fov
        rays_to_average = max(3, int(bbox_angle_width / self.current_scan.angle_increment))
        
        # Get rays around center
        start_index = max(0, center_index - rays_to_average // 2)
        end_index = min(len(self.current_scan.ranges), center_index + rays_to_average // 2)
        
        # Collect valid ranges
        valid_ranges = []
        for i in range(start_index, end_index):
            r = self.current_scan.ranges[i]
            if self.current_scan.range_min < r < self.current_scan.range_max:
                valid_ranges.append(r)
        
        if valid_ranges:
            # Use median to be robust against outliers
            return float(np.median(valid_ranges))
        else:
            return 2.0
    
    def get_yaw_from_quaternion(self, orientation) -> float:
        """Extract yaw angle from quaternion"""
        # Convert quaternion to yaw angle
        siny_cosp = 2 * (orientation.w * orientation.z + orientation.x * orientation.y)
        cosy_cosp = 1 - 2 * (orientation.y * orientation.y + orientation.z * orientation.z)
        return np.arctan2(siny_cosp, cosy_cosp)
    
    def find_or_create_object(self, class_name: str, x: float, y: float, confidence: float, timestamp) -> str:
        """Find existing object or create new one with improved merging logic"""
        current_time = self.get_clock().now()
        
        # Find best matching object (closest with same class)
        best_match = None
        best_distance = float('inf')
        
        for obj_id, obj_data in self.semantic_map.items():
            if obj_data['class'] == class_name:
                distance = np.sqrt((obj_data['x'] - x)**2 + (obj_data['y'] - y)**2)
                
                # Check if within merge distance threshold
                if distance < self.merge_distance and distance < best_distance:
                    best_match = obj_id
                    best_distance = distance
        
        if best_match:
            # Update existing object with weighted average for position
            obj_data = self.semantic_map[best_match]
            old_weight = obj_data['detections']
            new_weight = 1
            total_weight = old_weight + new_weight
            
            # Weighted average for position (gives more weight to frequently seen objects)
            obj_data['x'] = (obj_data['x'] * old_weight + x * new_weight) / total_weight
            obj_data['y'] = (obj_data['y'] * old_weight + y * new_weight) / total_weight
            
            # Update confidence (take maximum, as higher confidence is more reliable)
            obj_data['confidence'] = max(obj_data['confidence'], confidence)
            
            # Update timestamps
            obj_data['last_seen'] = current_time.nanoseconds / 1e9  # Convert to seconds
            obj_data['timestamp'] = timestamp
            obj_data['detections'] += 1
            
            self.get_logger().debug(f"Updated {class_name} (ID: {best_match}), detections: {obj_data['detections']}")
            return best_match
        
        # Create new object
        self.object_counter += 1
        object_id = f"{class_name}_{self.object_counter}"
        
        self.semantic_map[object_id] = {
            'class': class_name,
            'x': x,
            'y': y,
            'confidence': confidence,
            'timestamp': timestamp,
            'last_seen': current_time.nanoseconds / 1e9,
            'detections': 1,
            'created_at': current_time.nanoseconds / 1e9
        }
        
        # Mark spatial index as dirty
        self.spatial_index_dirty = True
        
        self.get_logger().info(f"Created new object: {object_id} at ({x:.2f}, {y:.2f})")
        return object_id
    
    def cleanup_old_objects(self):
        """Remove objects that haven't been seen for timeout period and apply confidence decay"""
        current_time = self.get_clock().now().nanoseconds / 1e9
        objects_to_remove = []
        
        for obj_id, obj_data in self.semantic_map.items():
            last_seen = obj_data.get('last_seen', obj_data.get('timestamp', 0))
            
            # Convert timestamp to seconds if it's a ROS Time object
            if hasattr(last_seen, 'sec'):
                last_seen = last_seen.sec + last_seen.nanosec / 1e9
            
            time_since_seen = current_time - last_seen
            
            # Apply confidence decay based on time since last seen
            if time_since_seen > 60:  # After 1 minute, start decaying
                minutes_unseen = time_since_seen / 60.0
                decay_factor = self.confidence_decay_rate ** minutes_unseen
                obj_data['confidence'] *= decay_factor
            
            # Mark for removal if timeout exceeded or confidence too low
            if time_since_seen > self.object_timeout:
                objects_to_remove.append(obj_id)
                self.get_logger().info(f"🗑️  Removing {obj_id} - not seen for {time_since_seen/60:.1f} minutes")
            elif obj_data['confidence'] < self.min_confidence:
                objects_to_remove.append(obj_id)
                self.get_logger().info(f"🗑️  Removing {obj_id} - confidence too low ({obj_data['confidence']:.2f})")
        
        # Remove old objects
        for obj_id in objects_to_remove:
            del self.semantic_map[obj_id]
        
        if objects_to_remove:
            # Mark spatial index as dirty
            self.spatial_index_dirty = True
            self.get_logger().info(f"Cleaned up {len(objects_to_remove)} old objects. Active objects: {len(self.semantic_map)}")
    
    def save_semantic_map(self):
        """Save semantic map to disk for persistence"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(self.persistence_file)), exist_ok=True)
            
            # Prepare data for serialization
            save_data = {
                'semantic_map': self.semantic_map,
                'object_counter': self.object_counter,
                'saved_at': self.get_clock().now().nanoseconds / 1e9
            }
            
            # Save to file
            with open(self.persistence_file, 'wb') as f:
                pickle.dump(save_data, f)
            
            self.get_logger().debug(f"💾 Saved {len(self.semantic_map)} objects to {self.persistence_file}")
            
        except Exception as e:
            self.get_logger().error(f"Failed to save semantic map: {e}")
    
    def load_semantic_map(self):
        """Load semantic map from disk"""
        try:
            if os.path.exists(self.persistence_file):
                with open(self.persistence_file, 'rb') as f:
                    save_data = pickle.load(f)
                
                self.semantic_map = save_data.get('semantic_map', {})
                self.object_counter = save_data.get('object_counter', 0)
                saved_at = save_data.get('saved_at', 0)
                
                self.get_logger().info(f"📂 Loaded {len(self.semantic_map)} objects from {self.persistence_file}")
                
                # Log age of loaded data
                current_time = self.get_clock().now().nanoseconds / 1e9
                age_minutes = (current_time - saved_at) / 60.0
                self.get_logger().info(f"   Data age: {age_minutes:.1f} minutes")
                
                # Clean up old objects from loaded data
                self.cleanup_old_objects()
            else:
                self.get_logger().info(f"No existing semantic map found at {self.persistence_file}")
                
        except Exception as e:
            self.get_logger().warn(f"Failed to load semantic map: {e}. Starting with empty map.")
    
    def command_callback(self, msg: String):
        """Handle semantic navigation commands"""
        command = msg.data.lower()
        
        if command.startswith("go to"):
            object_name = command.replace("go to", "").strip()
            
            # Check for multi-step navigation (e.g., "go to chair then table then door")
            if " then " in object_name:
                objects = [obj.strip() for obj in object_name.split(" then ")]
                self.navigate_multi_step(objects)
            else:
                self.navigate_to_object(object_name)
        elif command.startswith("find"):
            object_name = command.replace("find", "").strip()
            self.find_object(object_name)
        elif command == "list objects":
            self.list_detected_objects()
        elif command == "cancel navigation" or command == "stop":
            self.cancel_navigation()
        elif command.startswith("find nearby"):
            # Find objects near robot
            if self.current_pose:
                radius = 5.0  # 5 meter radius
                objects = self.find_all_objects_in_radius(
                    self.current_pose.pose.position.x,
                    self.current_pose.pose.position.y,
                    radius
                )
                self.get_logger().info(f"🔍 Found {len(objects)} objects within {radius}m:")
                for obj_id, obj_data in objects:
                    self.get_logger().info(f"  - {obj_data['class']} at ({obj_data['x']:.2f}, {obj_data['y']:.2f})")
    
    def navigate_to_object(self, object_name: str, use_nav2: bool = True):
        """Navigate to a specific object type using Nav2"""
        if self.current_pose is None:
            self.get_logger().warn("Cannot navigate - robot pose unknown")
            self.publish_navigation_status("failed", "Robot pose unknown")
            return
        
        # Find closest object using spatial indexing
        closest_object_id, closest_object = self.find_nearest_object(object_name)
        
        if closest_object:
            robot_x = self.current_pose.pose.position.x
            robot_y = self.current_pose.pose.position.y
            distance = np.sqrt((closest_object['x'] - robot_x)**2 + (closest_object['y'] - robot_y)**2)
            
            self.get_logger().info(f"🎯 Navigating to {object_name} at ({closest_object['x']:.2f}, {closest_object['y']:.2f}), distance: {distance:.2f}m")
            
            if use_nav2:
                # Use Nav2 action client for navigation
                self.send_nav2_goal(closest_object['x'], closest_object['y'], object_name)
            else:
                # Fallback: publish goal for other navigation systems
                goal = PoseStamped()
                goal.header.frame_id = "map"
                goal.header.stamp = self.get_clock().now().to_msg()
                goal.pose.position.x = closest_object['x']
                goal.pose.position.y = closest_object['y']
                goal.pose.orientation.w = 1.0
                self.navigation_goal_pub.publish(goal)
                self.publish_navigation_status("started", f"Goal published for {object_name}")
        else:
            self.get_logger().warn(f"❌ Object '{object_name}' not found in semantic map")
            self.publish_navigation_status("failed", f"Object '{object_name}' not found")
    
    def send_nav2_goal(self, x: float, y: float, object_name: str = "target"):
        """Send navigation goal to Nav2"""
        # Wait for Nav2 action server
        if not self.nav2_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().warn("Nav2 action server not available, using fallback")
            # Publish goal for other systems
            goal = PoseStamped()
            goal.header.frame_id = "map"
            goal.header.stamp = self.get_clock().now().to_msg()
            goal.pose.position.x = x
            goal.pose.position.y = y
            goal.pose.orientation.w = 1.0
            self.navigation_goal_pub.publish(goal)
            self.publish_navigation_status("started", f"Goal published (Nav2 unavailable)")
            return
        
        # Create Nav2 goal
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = "map"
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.position.z = 0.0
        goal_msg.pose.pose.orientation.w = 1.0
        
        # Send goal
        self.get_logger().info(f"📤 Sending Nav2 goal to ({x:.2f}, {y:.2f})")
        self.current_navigation_goal = object_name
        self.navigation_in_progress = True
        
        send_goal_future = self.nav2_client.send_goal_async(
            goal_msg,
            feedback_callback=self.navigation_feedback_callback
        )
        send_goal_future.add_done_callback(self.navigation_goal_response_callback)
        
        self.publish_navigation_status("started", f"Navigating to {object_name}")
    
    def navigation_goal_response_callback(self, future):
        """Handle Nav2 goal response"""
        goal_handle = future.result()
        
        if not goal_handle.accepted:
            self.get_logger().warn("❌ Nav2 goal rejected")
            self.navigation_in_progress = False
            self.publish_navigation_status("rejected", "Goal rejected by Nav2")
            return
        
        self.get_logger().info("✅ Nav2 goal accepted")
        
        # Get result
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.navigation_result_callback)
    
    def navigation_feedback_callback(self, feedback_msg):
        """Handle Nav2 navigation feedback"""
        feedback = feedback_msg.feedback
        
        # Calculate progress (distance remaining)
        if self.current_pose and hasattr(feedback, 'distance_remaining'):
            distance_remaining = feedback.distance_remaining
            self.get_logger().debug(f"📍 Distance remaining: {distance_remaining:.2f}m")
            
            # Publish progress (0-100%)
            # Estimate total distance and calculate progress
            progress = Float32()
            progress.data = max(0.0, min(100.0, (1.0 - distance_remaining / 10.0) * 100.0))
            self.navigation_progress_pub.publish(progress)
    
    def navigation_result_callback(self, future):
        """Handle Nav2 navigation result"""
        result = future.result().result
        status = future.result().status
        
        self.navigation_in_progress = False
        
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f"🎉 Navigation succeeded! Reached {self.current_navigation_goal}")
            self.publish_navigation_status("succeeded", f"Reached {self.current_navigation_goal}")
            
            # Check if there are more goals in multi-step navigation
            if self.multi_step_goals:
                next_goal = self.multi_step_goals.pop(0)
                self.get_logger().info(f"🔄 Continuing to next goal: {next_goal}")
                self.navigate_to_object(next_goal)
        elif status == GoalStatus.STATUS_ABORTED:
            self.get_logger().warn(f"⚠️ Navigation aborted for {self.current_navigation_goal}")
            self.publish_navigation_status("aborted", f"Navigation to {self.current_navigation_goal} aborted")
        elif status == GoalStatus.STATUS_CANCELED:
            self.get_logger().info(f"🛑 Navigation canceled for {self.current_navigation_goal}")
            self.publish_navigation_status("canceled", f"Navigation to {self.current_navigation_goal} canceled")
        else:
            self.get_logger().warn(f"❌ Navigation failed for {self.current_navigation_goal}")
            self.publish_navigation_status("failed", f"Navigation to {self.current_navigation_goal} failed")
        
        self.current_navigation_goal = None
    
    def publish_navigation_status(self, status: str, message: str):
        """Publish navigation status"""
        status_msg = String()
        status_data = {
            'status': status,
            'message': message,
            'timestamp': self.get_clock().now().nanoseconds / 1e9,
            'current_goal': self.current_navigation_goal,
            'in_progress': self.navigation_in_progress,
            'queued_goals': len(self.multi_step_goals)
        }
        status_msg.data = json.dumps(status_data)
        self.navigation_status_pub.publish(status_msg)
    
    def rebuild_spatial_index(self):
        """Rebuild spatial index (KDTree) for fast nearest-neighbor queries"""
        if not self.semantic_map:
            self.spatial_index = None
            self.spatial_index_dirty = False
            return
        
        # Extract positions and object IDs
        positions = []
        object_ids = []
        
        for obj_id, obj_data in self.semantic_map.items():
            positions.append([obj_data['x'], obj_data['y']])
            object_ids.append(obj_id)
        
        # Build KDTree
        if positions:
            self.spatial_index = KDTree(np.array(positions))
            self.spatial_index_object_ids = object_ids
            self.spatial_index_dirty = False
            self.get_logger().debug(f"🗺️  Rebuilt spatial index with {len(positions)} objects")
        else:
            self.spatial_index = None
    
    def find_nearest_object(self, object_class: str, max_distance: float = float('inf')) -> Tuple[Optional[str], Optional[Dict]]:
        """Find nearest object of given class using spatial indexing"""
        if self.current_pose is None:
            return None, None
        
        robot_pos = np.array([self.current_pose.pose.position.x, self.current_pose.pose.position.y])
        
        # Rebuild index if dirty
        if self.spatial_index_dirty or self.spatial_index is None:
            self.rebuild_spatial_index()
        
        if self.spatial_index is None:
            return None, None
        
        # Find all objects of the requested class
        matching_objects = []
        for obj_id, obj_data in self.semantic_map.items():
            if object_class.lower() in obj_data['class'].lower():
                distance = np.sqrt((obj_data['x'] - robot_pos[0])**2 + (obj_data['y'] - robot_pos[1])**2)
                if distance <= max_distance:
                    matching_objects.append((obj_id, obj_data, distance))
        
        if not matching_objects:
            return None, None
        
        # Sort by distance and return closest
        matching_objects.sort(key=lambda x: x[2])
        closest_id, closest_obj, _ = matching_objects[0]
        
        return closest_id, closest_obj
    
    def find_all_objects_in_radius(self, center_x: float, center_y: float, radius: float) -> List[Tuple[str, Dict]]:
        """Find all objects within radius of a point using spatial indexing"""
        if self.spatial_index_dirty or self.spatial_index is None:
            self.rebuild_spatial_index()
        
        if self.spatial_index is None:
            return []
        
        # Query KDTree
        center = np.array([center_x, center_y])
        indices = self.spatial_index.query_ball_point(center, radius)
        
        # Return matching objects
        results = []
        for idx in indices:
            obj_id = self.spatial_index_object_ids[idx]
            obj_data = self.semantic_map[obj_id]
            results.append((obj_id, obj_data))
        
        return results
    
    def navigate_multi_step(self, object_names: List[str]):
        """Navigate to multiple objects in sequence"""
        if not object_names:
            self.get_logger().warn("No objects specified for multi-step navigation")
            return
        
        self.get_logger().info(f"🗺️  Starting multi-step navigation: {' → '.join(object_names)}")
        
        # Set up multi-step goals
        self.multi_step_goals = object_names[1:]  # Queue remaining goals
        
        # Start with first goal
        self.navigate_to_object(object_names[0])
    
    def cancel_navigation(self):
        """Cancel current navigation"""
        if self.navigation_in_progress and self.nav2_client:
            self.get_logger().info("🛑 Canceling navigation...")
            # Cancel the goal (would need to store goal_handle for this)
            self.navigation_in_progress = False
            self.multi_step_goals.clear()
            self.publish_navigation_status("canceled", "Navigation canceled by user")
    
    def find_object(self, object_name: str):
        """Find and report object locations"""
        found_objects = []
        for obj_id, obj_data in self.semantic_map.items():
            if object_name in obj_data['class'].lower():
                distance = 0.0
                if self.current_pose:
                    robot_x = self.current_pose.pose.position.x
                    robot_y = self.current_pose.pose.position.y
                    distance = np.sqrt((obj_data['x'] - robot_x)**2 + (obj_data['y'] - robot_y)**2)
                found_objects.append((obj_data, distance))
        
        if found_objects:
            # Sort by distance
            found_objects.sort(key=lambda x: x[1])
            
            self.get_logger().info(f"🔍 Found {len(found_objects)} {object_name}(s):")
            for obj, dist in found_objects:
                self.get_logger().info(f"  - {obj['class']} at ({obj['x']:.2f}, {obj['y']:.2f}) - Distance: {dist:.2f}m, Confidence: {obj['confidence']:.2f}")
        else:
            self.get_logger().info(f"❌ No {object_name} found in semantic map")
    
    def list_detected_objects(self):
        """List all detected objects"""
        if not self.semantic_map:
            self.get_logger().info("📋 No objects detected yet")
            return
        
        self.get_logger().info(f"📋 Detected Objects ({len(self.semantic_map)} total):")
        for obj_id, obj_data in self.semantic_map.items():
            self.get_logger().info(f"  - {obj_data['class']} at ({obj_data['x']:.2f}, {obj_data['y']:.2f}) - {obj_data['detections']} detections")
    
    def scan_callback(self, msg: LaserScan):
        """Process laser scan data"""
        self.current_scan = msg
    
    def map_callback(self, msg: OccupancyGrid):
        """Process SLAM map updates"""
        self.current_map = msg
    
    def pose_callback(self, msg: PoseStamped):
        """Update current robot pose"""
        self.current_pose = msg
    
    def publish_semantic_map(self):
        """Publish semantic map as JSON"""
        if self.semantic_map:
            semantic_data = {
                'timestamp': self.get_clock().now().to_msg().sec,
                'objects': self.semantic_map
            }
            
            msg = String()
            msg.data = json.dumps(semantic_data, default=str)
            self.semantic_map_pub.publish(msg)
            
            # Publish semantic map visualization
            self.publish_markers()
            
            # Publish physical obstacles for costmap
            self.publish_semantic_obstacles()

    def publish_markers(self):
        """Publish visualization markers for RViz"""
        marker_array = MarkerArray()
        label_array = MarkerArray()
        
        for i, (obj_id, obj_data) in enumerate(self.semantic_map.items()):
            x = obj_data.get('x')
            y = obj_data.get('y')
            
            if x is None or y is None or math.isnan(x) or math.isnan(y):
                continue
                
            # Text Marker (Add to Label Array)
            text_marker = Marker()
            text_marker.header.frame_id = "map"
            text_marker.header.stamp = self.get_clock().now().to_msg()
            text_marker.ns = "semantic_labels"
            text_marker.id = i
            text_marker.type = Marker.TEXT_VIEW_FACING
            text_marker.action = Marker.ADD
            text_marker.pose.position.x = obj_data['x']
            text_marker.pose.position.y = obj_data['y']
            text_marker.pose.position.z = 1.0  # Nice height above object
            text_marker.scale.z = 0.4  # Readable size
            text_marker.color.r = 1.0
            text_marker.color.g = 1.0
            text_marker.color.b = 1.0
            text_marker.color.a = 1.0
            text_marker.text = f"{obj_data['class']} ({obj_data['confidence']:.2f})"
            label_array.markers.append(text_marker)
            
            # Sphere Marker (Add to Main Marker Array)
            sphere_marker = Marker()
            sphere_marker.header.frame_id = "map"
            sphere_marker.header.stamp = self.get_clock().now().to_msg()
            sphere_marker.ns = "semantic_objects"
            sphere_marker.id = i + 1000
            sphere_marker.type = Marker.SPHERE
            sphere_marker.action = Marker.ADD
            sphere_marker.pose.position.x = obj_data['x']
            sphere_marker.pose.position.y = obj_data['y']
            sphere_marker.pose.position.z = 0.2
            sphere_marker.scale.x = 0.3
            sphere_marker.scale.y = 0.3
            sphere_marker.scale.z = 0.3
            sphere_marker.color.r = 0.0
            sphere_marker.color.g = 1.0
            sphere_marker.color.b = 0.0
            sphere_marker.color.a = 0.8
            marker_array.markers.append(sphere_marker)
            
        self.marker_pub.publish(marker_array)
        self.label_pub.publish(label_array)

def main(args=None):
    rclpy.init(args=args)
    node = SemanticSLAMNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down - saving semantic map...")
        node.save_semantic_map()
    except Exception as e:
        node.get_logger().error(f'Error in semantic SLAM node: {e}')
    finally:
        # Final save before shutdown
        if 'node' in locals():
            node.save_semantic_map()
            node.get_logger().info(f"💾 Final save complete. {len(node.semantic_map)} objects persisted.")
            node.destroy_node()
        # Don't call rclpy.shutdown() - let launch system handle it

if __name__ == '__main__':
    main()