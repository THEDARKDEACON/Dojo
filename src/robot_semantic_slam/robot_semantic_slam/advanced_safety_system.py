#!/usr/bin/env python3
"""
Advanced Safety System - Predictive obstacle avoidance and emergency behaviors
Multi-level safety overrides with intelligent decision making
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, Image, PointCloud2
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import OccupancyGrid
from std_msgs.msg import String, Bool, Int32
import numpy as np
import cv2
from cv_bridge import CvBridge
from typing import Dict, List, Tuple, Optional
import time
from enum import Enum

# Behavior tree imports
try:
    import py_trees
    from py_trees.common import Status
    from py_trees.behaviour import Behaviour
    from py_trees.composites import Selector, Sequence, Parallel
    from py_trees.decorators import FailureIsSuccess, SuccessIsFailure
    PY_TREES_AVAILABLE = True
except ImportError:
    PY_TREES_AVAILABLE = False
    print("Warning: py_trees not available. Install with: pip3 install py-trees")

class SafetyLevel(Enum):
    NORMAL = 0
    CAUTION = 1
    WARNING = 2
    EMERGENCY = 3
    CRITICAL = 4

class ThreatType(Enum):
    STATIC_OBSTACLE = "static_obstacle"
    DYNAMIC_OBSTACLE = "dynamic_obstacle"
    HUMAN_DETECTED = "human_detected"
    CLIFF_EDGE = "cliff_edge"
    NARROW_PASSAGE = "narrow_passage"
    SYSTEM_FAILURE = "system_failure"

# ============================================================================
# Behavior Tree Nodes for Emergency Response
# ============================================================================

if PY_TREES_AVAILABLE:
    
    class CheckCriticalThreat(Behaviour):
        """Check if there's a critical threat requiring immediate action"""
        
        def __init__(self, name: str, safety_system):
            super().__init__(name)
            self.safety_system = safety_system
        
        def update(self) -> Status:
            if self.safety_system.current_safety_level == SafetyLevel.CRITICAL:
                return Status.SUCCESS
            return Status.FAILURE
    
    class EmergencyStop(Behaviour):
        """Execute emergency stop - halt all motion immediately"""
        
        def __init__(self, name: str, safety_system):
            super().__init__(name)
            self.safety_system = safety_system
            self.stop_time = None
        
        def initialise(self):
            self.stop_time = time.time()
            self.safety_system.get_logger().warn("🛑 EMERGENCY STOP ACTIVATED")
        
        def update(self) -> Status:
            # Publish stop command
            stop_cmd = Twist()
            self.safety_system.cmd_vel_safe_pub.publish(stop_cmd)
            
            # Publish emergency stop flag
            emergency_msg = Bool()
            emergency_msg.data = True
            self.safety_system.emergency_stop_pub.publish(emergency_msg)
            
            # Check if we've been stopped for at least 100ms
            if time.time() - self.stop_time >= 0.1:
                return Status.SUCCESS
            return Status.RUNNING
    
    class CheckHumanThreat(Behaviour):
        """Check if human is detected within safety distance"""
        
        def __init__(self, name: str, safety_system):
            super().__init__(name)
            self.safety_system = safety_system
        
        def update(self) -> Status:
            # Check for human threats
            for threat_id, threat_data in self.safety_system.active_threats.items():
                if threat_data['type'] == ThreatType.HUMAN_DETECTED:
                    return Status.SUCCESS
            return Status.FAILURE
    
    class MaintainHumanDistance(Behaviour):
        """Maintain 1.5m distance from detected humans"""
        
        def __init__(self, name: str, safety_system):
            super().__init__(name)
            self.safety_system = safety_system
            self.min_distance = 1.5  # meters
        
        def update(self) -> Status:
            # Reduce speed significantly when human detected
            if self.safety_system.last_cmd_vel:
                safe_cmd = Twist()
                # Reduce to 20% speed
                safe_cmd.linear.x = self.safety_system.last_cmd_vel.linear.x * 0.2
                safe_cmd.angular.z = self.safety_system.last_cmd_vel.angular.z * 0.2
                self.safety_system.cmd_vel_safe_pub.publish(safe_cmd)
                
                self.safety_system.get_logger().info("👤 Human detected - maintaining safe distance")
                return Status.SUCCESS
            return Status.FAILURE
    
    class CheckDynamicObstacle(Behaviour):
        """Check for dynamic obstacles requiring evasive action"""
        
        def __init__(self, name: str, safety_system):
            super().__init__(name)
            self.safety_system = safety_system
        
        def update(self) -> Status:
            for threat_id, threat_data in self.safety_system.active_threats.items():
                if threat_data['type'] == ThreatType.DYNAMIC_OBSTACLE:
                    return Status.SUCCESS
            return Status.FAILURE
    
    class EvadeObstacle(Behaviour):
        """Execute evasive maneuver for dynamic obstacles"""
        
        def __init__(self, name: str, safety_system):
            super().__init__(name)
            self.safety_system = safety_system
        
        def update(self) -> Status:
            # Implement evasive maneuver
            if self.safety_system.current_scan:
                # Find direction with most clearance
                ranges = self.safety_system.current_scan.ranges
                mid_point = len(ranges) // 2
                
                left_clearance = np.mean([r for r in ranges[:mid_point] if 0.1 < r < 10.0])
                right_clearance = np.mean([r for r in ranges[mid_point:] if 0.1 < r < 10.0])
                
                safe_cmd = Twist()
                if left_clearance > right_clearance:
                    # Turn left
                    safe_cmd.angular.z = 0.5
                    self.safety_system.get_logger().warn("🚧 WOULD Evade LEFT (Actuation Disabled)")
                else:
                    # Turn right
                    safe_cmd.angular.z = -0.5
                    self.safety_system.get_logger().warn("🚧 WOULD Evade RIGHT (Actuation Disabled)")
                
                # safe_cmd.linear.x = 0.1  # Slow forward motion
                # self.safety_system.cmd_vel_safe_pub.publish(safe_cmd)
                return Status.SUCCESS
            return Status.FAILURE
    
    class CheckWarningLevel(Behaviour):
        """Check if at warning safety level"""
        
        def __init__(self, name: str, safety_system):
            super().__init__(name)
            self.safety_system = safety_system
        
        def update(self) -> Status:
            if self.safety_system.current_safety_level in [SafetyLevel.WARNING, SafetyLevel.EMERGENCY]:
                return Status.SUCCESS
            return Status.FAILURE
    
    class ReduceSpeed(Behaviour):
        """Reduce speed for warning level threats"""
        
        def __init__(self, name: str, safety_system):
            super().__init__(name)
            self.safety_system = safety_system
        
        def update(self) -> Status:
            if self.safety_system.last_cmd_vel:
                safe_cmd = Twist()
                # Reduce to 50% speed
                safe_cmd.linear.x = self.safety_system.last_cmd_vel.linear.x * 0.5
                safe_cmd.angular.z = self.safety_system.last_cmd_vel.angular.z * 0.5
                self.safety_system.cmd_vel_safe_pub.publish(safe_cmd)
                return Status.SUCCESS
            return Status.FAILURE
    
    class NormalOperation(Behaviour):
        """Pass through commands during normal operation"""
        
        def __init__(self, name: str, safety_system):
            super().__init__(name)
            self.safety_system = safety_system
        
        def update(self) -> Status:
            # Pass through command unchanged
            if self.safety_system.last_cmd_vel:
                self.safety_system.cmd_vel_safe_pub.publish(self.safety_system.last_cmd_vel)
                return Status.SUCCESS
            return Status.FAILURE

class AdvancedSafetySystem(Node):
    """Intelligent multi-layer safety system with predictive capabilities"""
    
    def __init__(self):
        super().__init__('advanced_safety_system')
        
        # Safety state
        self.current_safety_level = SafetyLevel.NORMAL
        self.active_threats = {}
        self.safety_override_active = False
        
        # Predictive tracking
        self.obstacle_history = {}  # Track moving obstacles
        self.prediction_horizon = 3.0  # seconds
        
        # Safety zones (distances in meters)
        self.safety_zones = {
            'critical': 0.3,    # Emergency stop
            'warning': 0.8,     # Slow down significantly
            'caution': 1.5,     # Reduce speed (human safety distance)
            'normal': 3.0       # Normal operation
        }
        
        # Human detection parameters
        self.human_safety_distance = 1.5  # meters - minimum distance from humans
        self.detected_humans = {}  # Track detected humans with positions
        
        # Publishers
        self.cmd_vel_safe_pub = self.create_publisher(Twist, '/cmd_vel_safe', 10)
        self.safety_status_pub = self.create_publisher(String, '/safety_status', 10)
        self.emergency_stop_pub = self.create_publisher(Bool, '/emergency_stop', 10)
        self.safety_level_pub = self.create_publisher(Int32, '/safety_level', 10)
        
        # RViz visualization publishers
        from visualization_msgs.msg import Marker, MarkerArray
        self.human_marker_pub = self.create_publisher(MarkerArray, '/human_safety_markers', 10)
        self.threat_marker_pub = self.create_publisher(MarkerArray, '/threat_markers', 10)
        
        # Subscribers
        self.cmd_vel_sub = self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.scan_sub = self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        self.image_sub = self.create_subscription(Image, '/camera/image_raw', self.image_callback, 10)
        self.pose_sub = self.create_subscription(PoseStamped, '/robot_pose', self.pose_callback, 10)
        self.map_sub = self.create_subscription(OccupancyGrid, '/map', self.map_callback, 10)
        
        # Safety override subscriber
        self.override_sub = self.create_subscription(Bool, '/safety_override', self.override_callback, 10)
        
        # Current state
        self.current_scan = None
        self.current_pose = None
        self.current_map = None
        self.last_cmd_vel = Twist()
        
        # CV bridge for image processing
        self.bridge = CvBridge()
        
        # Initialize YOLO for human detection
        try:
            from ultralytics import YOLO
            self.yolo_model = YOLO('yolov8n.pt')  # Lightweight model
            self.yolo_available = True
            self.get_logger().info("✅ YOLO model loaded for human detection")
        except Exception as e:
            self.yolo_available = False
            self.get_logger().warn(f"⚠️ YOLO not available: {e}. Using fallback detection.")
        
        # Behavior Tree for emergency response
        self.behavior_tree = None
        if PY_TREES_AVAILABLE:
            self.behavior_tree = self.create_emergency_behavior_tree()
            self.get_logger().info("🌳 Behavior tree initialized for emergency response")
        else:
            self.get_logger().warn("⚠️ py_trees not available - using fallback safety logic")
        
        # Timers
        self.safety_timer = self.create_timer(0.1, self.safety_check)  # 10 Hz
        self.prediction_timer = self.create_timer(0.2, self.update_predictions)  # 5 Hz
        self.behavior_tree_timer = self.create_timer(0.05, self.tick_behavior_tree)  # 20 Hz
        self.visualization_timer = self.create_timer(0.2, self.publish_human_markers)  # 5 Hz
        self.threat_viz_timer = self.create_timer(0.2, self.publish_human_markers)  # 5 Hz
        
        self.get_logger().info("🛡️ Advanced Safety System initialized - Multi-layer protection active!")
        self.get_logger().info(f"👤 Human safety distance: {self.human_safety_distance}m")
    
    def create_emergency_behavior_tree(self):
        """Create behavior tree for emergency response handling"""
        if not PY_TREES_AVAILABLE:
            return None
        
        # Root selector - tries behaviors in priority order
        root = Selector(name="Emergency Response Root")
        
        # Priority 1: Critical threats - Emergency stop
        critical_sequence = Sequence(name="Critical Threat Response")
        critical_sequence.add_children([
            CheckCriticalThreat("Check Critical", self),
            EmergencyStop("Emergency Stop", self)
        ])
        
        # Priority 2: Human detection - Maintain distance
        human_sequence = Sequence(name="Human Safety Response")
        human_sequence.add_children([
            CheckHumanThreat("Check Human", self),
            MaintainHumanDistance("Maintain Distance", self)
        ])
        
        # Priority 3: Dynamic obstacles - Evasive maneuvers
        dynamic_sequence = Sequence(name="Dynamic Obstacle Response")
        dynamic_sequence.add_children([
            CheckDynamicObstacle("Check Dynamic", self),
            EvadeObstacle("Evade", self)
        ])
        
        # Priority 4: Warning level - Reduce speed
        warning_sequence = Sequence(name="Warning Level Response")
        warning_sequence.add_children([
            CheckWarningLevel("Check Warning", self),
            ReduceSpeed("Reduce Speed", self)
        ])
        
        # Priority 5: Normal operation - Pass through
        normal_operation = NormalOperation("Normal Operation", self)
        
        # Add all behaviors to root selector in priority order
        root.add_children([
            critical_sequence,
            human_sequence,
            dynamic_sequence,
            warning_sequence,
            normal_operation
        ])
        
        return root
    
    def tick_behavior_tree(self):
        """Tick the behavior tree to execute emergency responses"""
        if self.behavior_tree and PY_TREES_AVAILABLE:
            try:
                self.behavior_tree.tick_once()
            except Exception as e:
                self.get_logger().error(f"Behavior tree error: {e}")
                # Fallback to emergency stop on error
                stop_cmd = Twist()
                self.cmd_vel_safe_pub.publish(stop_cmd)
    
    def cmd_vel_callback(self, msg: Twist):
        """Intercept and validate velocity commands"""
        self.last_cmd_vel = msg
        
        # If behavior tree not available, use fallback safety filtering
        if not PY_TREES_AVAILABLE or not self.behavior_tree:
            safe_cmd = self.apply_safety_filter(msg)
            self.cmd_vel_safe_pub.publish(safe_cmd)
    
    def scan_callback(self, msg: LaserScan):
        """Process laser scan for obstacle detection"""
        self.current_scan = msg
        
        # Detect immediate threats
        self.detect_scan_threats(msg)
    
    def image_callback(self, msg: Image):
        """Process camera for visual safety checks"""
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            
            # Detect humans and other safety-critical objects
            self.detect_visual_threats(cv_image)
            
        except Exception as e:
            self.get_logger().error(f"Error in visual safety processing: {e}")
    
    def pose_callback(self, msg: PoseStamped):
        """Update robot pose for spatial safety analysis"""
        self.current_pose = msg
    
    def map_callback(self, msg: OccupancyGrid):
        """Process map for global safety analysis"""
        self.current_map = msg
    
    def override_callback(self, msg: Bool):
        """Handle safety override commands"""
        self.safety_override_active = msg.data
        if msg.data:
            self.get_logger().warn("⚠️ SAFETY OVERRIDE ACTIVATED - Use with extreme caution!")
        else:
            self.get_logger().info("🛡️ Safety override deactivated - Normal safety protocols resumed")
    
    def detect_scan_threats(self, scan: LaserScan):
        """Analyze laser scan for threats"""
        if not scan.ranges:
            return
        
        min_distance = min([r for r in scan.ranges if r > scan.range_min and r < scan.range_max])
        
        # Check safety zones with enhanced threat information
        if min_distance < self.safety_zones['critical']:
            self.add_threat(ThreatType.STATIC_OBSTACLE, SafetyLevel.CRITICAL, 
                          f"Critical obstacle at {min_distance:.2f}m",
                          distance=min_distance, velocity=0.0)
        elif min_distance < self.safety_zones['warning']:
            self.add_threat(ThreatType.STATIC_OBSTACLE, SafetyLevel.WARNING,
                          f"Warning obstacle at {min_distance:.2f}m",
                          distance=min_distance, velocity=0.0)
        elif min_distance < self.safety_zones['caution']:
            self.add_threat(ThreatType.STATIC_OBSTACLE, SafetyLevel.CAUTION,
                          f"Caution obstacle at {min_distance:.2f}m",
                          distance=min_distance, velocity=0.0)
        
        # Detect dynamic obstacles by comparing with history
        self.detect_dynamic_obstacles(scan)
    
    def detect_dynamic_obstacles(self, scan: LaserScan):
        """Detect moving obstacles by comparing scan history"""
        current_time = time.time()
        scan_key = f"scan_{current_time}"
        
        # Store current scan
        self.obstacle_history[scan_key] = {
            'ranges': list(scan.ranges),
            'timestamp': current_time
        }
        
        # Clean old history (keep last 2 seconds)
        cutoff_time = current_time - 2.0
        self.obstacle_history = {k: v for k, v in self.obstacle_history.items() 
                               if v['timestamp'] > cutoff_time}
        
        # Compare with previous scans to detect movement
        if len(self.obstacle_history) > 5:  # Need some history
            self.analyze_obstacle_movement()
    
    def analyze_obstacle_movement(self):
        """Analyze obstacle movement patterns"""
        # Simplified dynamic obstacle detection
        # In practice, you'd use more sophisticated tracking algorithms
        
        recent_scans = sorted(self.obstacle_history.items(), 
                            key=lambda x: x[1]['timestamp'])[-5:]
        
        if len(recent_scans) < 2:
            return
        
        # Compare consecutive scans for significant changes
        for i in range(1, len(recent_scans)):
            prev_ranges = recent_scans[i-1][1]['ranges']
            curr_ranges = recent_scans[i][1]['ranges']
            
            # Find significant range changes (potential moving obstacles)
            for j, (prev_r, curr_r) in enumerate(zip(prev_ranges, curr_ranges)):
                if (abs(prev_r - curr_r) > 0.5 and 
                    prev_r < 5.0 and curr_r < 5.0):  # Significant change in close range
                    
                    # Predict future position
                    velocity = (curr_r - prev_r) / 0.2  # Rough velocity estimate
                    predicted_distance = curr_r + velocity * self.prediction_horizon
                    
                    if predicted_distance < self.safety_zones['warning']:
                        self.add_threat(ThreatType.DYNAMIC_OBSTACLE, SafetyLevel.WARNING,
                                      f"Predicted dynamic obstacle collision in {self.prediction_horizon}s",
                                      distance=curr_r, velocity=velocity)
    
    def detect_visual_threats(self, image: np.ndarray):
        """Detect visual safety threats using YOLO"""
        # Clear old human detections
        current_time = time.time()
        self.detected_humans = {k: v for k, v in self.detected_humans.items() 
                               if current_time - v['timestamp'] < 1.0}
        
        if self.yolo_available:
            # Use YOLO for accurate human detection
            self.detect_humans_with_yolo(image)
        else:
            # Fallback to color-based detection
            self.detect_humans_fallback(image)
        
        # Detect cliff edges (simplified - look for large dark areas at bottom)
        bottom_region = image[int(image.shape[0] * 0.8):, :]
        gray_bottom = cv2.cvtColor(bottom_region, cv2.COLOR_BGR2GRAY)
        dark_pixels = np.sum(gray_bottom < 50)
        total_pixels = gray_bottom.size
        
        if dark_pixels / total_pixels > 0.7:  # 70% dark pixels
            self.add_threat(ThreatType.CLIFF_EDGE, SafetyLevel.CRITICAL,
                          "Potential cliff edge detected",
                          distance=0.5, velocity=0.0)  # Assume cliff is very close
    
    def detect_humans_with_yolo(self, image: np.ndarray):
        """Detect humans using YOLO person class (class_id=0)"""
        try:
            # Run YOLO detection
            results = self.yolo_model(image, verbose=False)
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        class_id = int(box.cls[0].cpu().numpy())
                        confidence = float(box.conf[0].cpu().numpy())
                        
                        # Check if it's a person (class_id=0 in COCO dataset)
                        if class_id == 0 and confidence > 0.5:
                            # Extract bounding box
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            bbox = (float(x1), float(y1), float(x2), float(y2))
                            
                            # Calculate accurate distance using LiDAR fusion
                            distance = self.estimate_human_distance_with_lidar(bbox, image.shape)
                            
                            # Store human detection
                            human_id = f"human_{int(time.time() * 1000)}"
                            self.detected_humans[human_id] = {
                                'bbox': bbox,
                                'confidence': confidence,
                                'distance': distance,
                                'timestamp': time.time()
                            }
                            
                            # Determine threat level based on distance
                            if distance < self.human_safety_distance:
                                threat_level = SafetyLevel.WARNING
                                self.add_threat(ThreatType.HUMAN_DETECTED, threat_level,
                                              f"Human at {distance:.2f}m (min: {self.human_safety_distance}m)",
                                              distance=distance, velocity=0.0)  # Assume stationary for now
                                self.get_logger().warn(f"👤 Human detected at {distance:.2f}m - enforcing safety distance!")
                            else:
                                self.get_logger().info(f"👤 Human detected at {distance:.2f}m - safe distance")
                            
        except Exception as e:
            self.get_logger().error(f"Error in YOLO human detection: {e}")
            # Fall back to color-based detection
            self.detect_humans_fallback(image)
    
    def detect_humans_fallback(self, image: np.ndarray):
        """Fallback human detection using color-based approach"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Detect skin color (simplified human detection)
        lower_skin = np.array([0, 20, 70])
        upper_skin = np.array([20, 255, 255])
        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # Find contours
        contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Check for significant skin-colored regions (potential humans)
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 1000:  # Significant area
                # Get bounding box
                x, y, w, h = cv2.boundingRect(contour)
                bbox = (float(x), float(y), float(x + w), float(y + h))
                
                # Estimate distance
                distance = self.estimate_human_distance_with_lidar(bbox, image.shape)
                
                if distance < self.human_safety_distance:
                    self.add_threat(ThreatType.HUMAN_DETECTED, SafetyLevel.WARNING,
                                  f"Human detected at {distance:.2f}m (fallback detection)",
                                  distance=distance, velocity=0.0)
    
    def estimate_human_distance_with_lidar(self, bbox: Tuple, image_shape: Tuple) -> float:
        """Estimate human distance using LiDAR-camera fusion"""
        if self.current_scan is None:
            self.get_logger().warn("No LiDAR data - using fallback distance")
            return 2.0
        
        # Extract bounding box center
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        bbox_width = x2 - x1
        
        # Camera parameters (assuming standard camera)
        image_height, image_width = image_shape[:2]
        horizontal_fov = np.deg2rad(60)  # 60 degrees horizontal FOV
        
        # Calculate angle corresponding to bounding box center
        angle_offset = ((center_x - image_width / 2) / (image_width / 2)) * (horizontal_fov / 2)
        
        # LiDAR scan parameters
        angle_min = self.current_scan.angle_min
        angle_max = self.current_scan.angle_max
        angle_increment = self.current_scan.angle_increment
        
        # Convert camera angle to LiDAR scan index
        lidar_angle = angle_offset
        
        # Check if angle is within LiDAR range
        if lidar_angle < angle_min or lidar_angle > angle_max:
            self.get_logger().warn(f"Human angle {np.rad2deg(lidar_angle):.1f}° outside LiDAR range")
            return 2.0
        
        # Find corresponding LiDAR ray index
        ray_index = int((lidar_angle - angle_min) / angle_increment)
        ray_index = max(0, min(ray_index, len(self.current_scan.ranges) - 1))
        
        # Calculate number of rays to average based on bbox width
        bbox_angle_width = (bbox_width / image_width) * horizontal_fov
        rays_to_average = max(5, int(bbox_angle_width / angle_increment))
        
        # Get rays around center
        start_index = max(0, ray_index - rays_to_average // 2)
        end_index = min(len(self.current_scan.ranges), ray_index + rays_to_average // 2)
        
        # Collect valid ranges
        valid_ranges = []
        for i in range(start_index, end_index):
            r = self.current_scan.ranges[i]
            if self.current_scan.range_min < r < self.current_scan.range_max:
                valid_ranges.append(r)
        
        if valid_ranges:
            # Use median for robustness
            distance = float(np.median(valid_ranges))
            
            # Validate distance
            if 0.3 < distance < 10.0:
                return distance
            else:
                self.get_logger().warn(f"Unrealistic human distance {distance:.2f}m")
                return 2.0
        else:
            self.get_logger().warn("No valid LiDAR readings for human")
            return 2.0
    
    def add_threat(self, threat_type: ThreatType, level: SafetyLevel, description: str, 
                   distance: float = None, velocity: float = None, position: Tuple = None):
        """Add or update a safety threat with enhanced metadata"""
        threat_id = f"{threat_type.value}_{int(time.time() * 10)}"
        
        self.active_threats[threat_id] = {
            'type': threat_type,
            'level': level,
            'description': description,
            'timestamp': time.time(),
            'distance': distance,
            'velocity': velocity,
            'position': position,
            'severity_score': self.calculate_threat_severity(threat_type, level, distance, velocity)
        }
        
        # Update overall safety level with prioritization
        self.update_safety_level_with_prioritization()
    
    def calculate_threat_severity(self, threat_type: ThreatType, level: SafetyLevel, 
                                  distance: float = None, velocity: float = None) -> float:
        """
        Calculate threat severity score for prioritization
        Score range: 0.0 (no threat) to 100.0 (critical threat)
        
        Factors:
        - Base severity from safety level (0-40 points)
        - Threat type priority (0-20 points)
        - Proximity factor (0-30 points)
        - Velocity factor (0-10 points)
        """
        score = 0.0
        
        # Base severity from safety level (0-40 points)
        level_scores = {
            SafetyLevel.NORMAL: 0,
            SafetyLevel.CAUTION: 10,
            SafetyLevel.WARNING: 20,
            SafetyLevel.EMERGENCY: 30,
            SafetyLevel.CRITICAL: 40
        }
        score += level_scores.get(level, 0)
        
        # Threat type priority (0-20 points)
        type_priorities = {
            ThreatType.CLIFF_EDGE: 20,          # Highest priority
            ThreatType.HUMAN_DETECTED: 18,      # Very high priority
            ThreatType.SYSTEM_FAILURE: 16,      # High priority
            ThreatType.DYNAMIC_OBSTACLE: 12,    # Medium-high priority
            ThreatType.STATIC_OBSTACLE: 8,      # Medium priority
            ThreatType.NARROW_PASSAGE: 4        # Lower priority
        }
        score += type_priorities.get(threat_type, 0)
        
        # Proximity factor (0-30 points) - closer is more severe
        if distance is not None:
            if distance < 0.3:
                score += 30  # Critical proximity
            elif distance < 0.8:
                score += 25  # Very close
            elif distance < 1.5:
                score += 20  # Close
            elif distance < 3.0:
                score += 10  # Moderate distance
            elif distance < 5.0:
                score += 5   # Far but monitored
            # else: 0 points for very far
        
        # Velocity factor (0-10 points) - approaching threats are more severe
        if velocity is not None:
            if velocity < -1.0:  # Approaching fast
                score += 10
            elif velocity < -0.5:  # Approaching moderate
                score += 7
            elif velocity < 0:  # Approaching slow
                score += 4
            # else: 0 points for stationary or receding
        
        return min(score, 100.0)  # Cap at 100
    
    def prioritize_threats(self) -> List[Tuple[str, Dict]]:
        """
        Prioritize active threats by severity score
        Returns list of (threat_id, threat_data) tuples sorted by priority (highest first)
        """
        if not self.active_threats:
            return []
        
        # Sort threats by severity score (descending)
        prioritized = sorted(
            self.active_threats.items(),
            key=lambda x: x[1]['severity_score'],
            reverse=True
        )
        
        return prioritized
    
    def get_highest_priority_threat(self) -> Optional[Tuple[str, Dict]]:
        """Get the highest priority threat"""
        prioritized = self.prioritize_threats()
        return prioritized[0] if prioritized else None
    
    def update_safety_level_with_prioritization(self):
        """Update overall safety level based on prioritized threats"""
        if not self.active_threats:
            self.current_safety_level = SafetyLevel.NORMAL
            level_msg = Int32()
            level_msg.data = self.current_safety_level.value
            self.safety_level_pub.publish(level_msg)
            return
        
        # Get highest priority threat
        highest_threat = self.get_highest_priority_threat()
        
        if highest_threat:
            threat_id, threat_data = highest_threat
            self.current_safety_level = threat_data['level']
            
            # Log priority information
            self.get_logger().debug(
                f"Highest priority threat: {threat_data['type'].value} "
                f"(severity: {threat_data['severity_score']:.1f}, level: {threat_data['level'].name})"
            )
        else:
            self.current_safety_level = SafetyLevel.NORMAL
        
        # Publish safety level
        level_msg = Int32()
        level_msg.data = self.current_safety_level.value
        self.safety_level_pub.publish(level_msg)
    
    def update_safety_level(self):
        """Legacy method - redirects to prioritization version"""
        self.update_safety_level_with_prioritization()
    
    def apply_safety_filter(self, cmd_vel: Twist) -> Twist:
        """Apply safety filtering to velocity commands"""
        if self.safety_override_active:
            return cmd_vel  # Pass through if override active
        
        safe_cmd = Twist()
        
        # Apply safety scaling based on current level
        safety_factors = {
            SafetyLevel.NORMAL: 1.0,
            SafetyLevel.CAUTION: 0.7,
            SafetyLevel.WARNING: 0.3,
            SafetyLevel.EMERGENCY: 0.1,
            SafetyLevel.CRITICAL: 0.0
        }
        
        factor = safety_factors.get(self.current_safety_level, 0.0)
        
        # Scale velocities
        safe_cmd.linear.x = cmd_vel.linear.x * factor
        safe_cmd.linear.y = cmd_vel.linear.y * factor
        safe_cmd.angular.z = cmd_vel.angular.z * factor
        
        # Emergency stop for critical threats
        if self.current_safety_level == SafetyLevel.CRITICAL:
            safe_cmd = Twist()  # Full stop
            emergency_msg = Bool()
            emergency_msg.data = True
            self.emergency_stop_pub.publish(emergency_msg)
        
        return safe_cmd
    
    def safety_check(self):
        """Periodic safety system check"""
        current_time = time.time()
        
        # Clean old threats (remove threats older than 2 seconds)
        cutoff_time = current_time - 2.0
        self.active_threats = {k: v for k, v in self.active_threats.items() 
                             if v['timestamp'] > cutoff_time}
        
        # Update safety level
        self.update_safety_level()
        
        # Publish safety status
        status_data = {
            'safety_level': self.current_safety_level.name,
            'active_threats': len(self.active_threats),
            'override_active': self.safety_override_active,
            'threats': [
                {
                    'type': threat['type'].value,
                    'level': threat['level'].name,
                    'description': threat['description']
                }
                for threat in self.active_threats.values()
            ]
        }
        
        status_msg = String()
        status_msg.data = str(status_data)
        self.safety_status_pub.publish(status_msg)
    
    def update_predictions(self):
        """Update predictive safety analysis"""
        if not self.current_scan or not self.current_pose:
            return
        
        # Predict robot trajectory based on current velocity
        if self.last_cmd_vel.linear.x != 0 or self.last_cmd_vel.angular.z != 0:
            self.predict_collision_risk()
    
    def predict_collision_risk(self):
        """Predict potential collisions based on current trajectory"""
        # Simplified trajectory prediction
        # In practice, use more sophisticated motion models
        
        linear_vel = self.last_cmd_vel.linear.x
        angular_vel = self.last_cmd_vel.angular.z
        
        # Predict position after prediction_horizon seconds
        if abs(angular_vel) < 0.01:  # Straight line motion
            predicted_x = linear_vel * self.prediction_horizon
            predicted_y = 0.0
        else:  # Curved motion
            radius = linear_vel / angular_vel
            angle = angular_vel * self.prediction_horizon
            predicted_x = radius * np.sin(angle)
            predicted_y = radius * (1 - np.cos(angle))
        
        # Check if predicted path intersects with obstacles
        if self.current_scan:
            self.check_trajectory_safety(predicted_x, predicted_y)
    
    def check_trajectory_safety(self, pred_x: float, pred_y: float):
        """Check if predicted trajectory is safe"""
        # Convert predicted position to scan coordinates
        predicted_distance = np.sqrt(pred_x**2 + pred_y**2)
        predicted_angle = np.arctan2(pred_y, pred_x)
        
        # Find corresponding scan ray
        if self.current_scan:
            angle_min = self.current_scan.angle_min
            angle_increment = self.current_scan.angle_increment
            
            ray_index = int((predicted_angle - angle_min) / angle_increment)
            
            if 0 <= ray_index < len(self.current_scan.ranges):
                obstacle_distance = self.current_scan.ranges[ray_index]
                
                if (obstacle_distance < self.current_scan.range_max and 
                    predicted_distance >= obstacle_distance * 0.8):  # 80% safety margin
                    
                    self.add_threat(ThreatType.STATIC_OBSTACLE, SafetyLevel.WARNING,
                                  f"Predicted trajectory collision in {self.prediction_horizon}s")
    
    def publish_human_markers(self):
        """Publish RViz markers for detected humans"""
        from visualization_msgs.msg import Marker, MarkerArray
        from std_msgs.msg import ColorRGBA
        
        if not self.current_pose:
            return
        
        marker_array = MarkerArray()
        
        # Delete old markers
        delete_marker = Marker()
        delete_marker.action = Marker.DELETEALL
        marker_array.markers.append(delete_marker)
        
        # Create markers for each detected human
        marker_id = 0
        for human_id, human_data in self.detected_humans.items():
            distance = human_data['distance']
            
            # Calculate human position in world frame
            # Assuming camera is forward-facing
            bbox = human_data['bbox']
            center_x = (bbox[0] + bbox[2]) / 2
            
            # Calculate angle offset
            image_width = 640  # Assumed
            horizontal_fov = np.deg2rad(60)
            angle_offset = ((center_x - image_width / 2) / (image_width / 2)) * (horizontal_fov / 2)
            
            # Robot frame position
            robot_frame_x = distance * np.cos(angle_offset)
            robot_frame_y = distance * np.sin(angle_offset)
            
            # Transform to world frame
            robot_yaw = self.get_yaw_from_quaternion(self.current_pose.pose.orientation)
            world_x = self.current_pose.pose.position.x + robot_frame_x * np.cos(robot_yaw) - robot_frame_y * np.sin(robot_yaw)
            world_y = self.current_pose.pose.position.y + robot_frame_x * np.sin(robot_yaw) + robot_frame_y * np.cos(robot_yaw)
            
            # Create cylinder marker for human
            marker = Marker()
            marker.header.frame_id = "map"
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = "humans"
            marker.id = marker_id
            marker.type = Marker.CYLINDER
            marker.action = Marker.ADD
            
            marker.pose.position.x = world_x
            marker.pose.position.y = world_y
            marker.pose.position.z = 0.9  # Human height center
            marker.pose.orientation.w = 1.0
            
            marker.scale.x = 0.5  # Diameter
            marker.scale.y = 0.5
            marker.scale.z = 1.8  # Human height
            
            # Color based on distance (red if too close, yellow if caution, green if safe)
            if distance < self.human_safety_distance:
                marker.color = ColorRGBA(r=1.0, g=0.0, b=0.0, a=0.7)  # Red
            elif distance < self.human_safety_distance * 1.5:
                marker.color = ColorRGBA(r=1.0, g=1.0, b=0.0, a=0.7)  # Yellow
            else:
                marker.color = ColorRGBA(r=0.0, g=1.0, b=0.0, a=0.7)  # Green
            
            marker.lifetime.sec = 1  # 1 second lifetime
            marker_array.markers.append(marker)
            marker_id += 1
            
            # Create text marker with distance
            text_marker = Marker()
            text_marker.header.frame_id = "map"
            text_marker.header.stamp = self.get_clock().now().to_msg()
            text_marker.ns = "human_labels"
            text_marker.id = marker_id
            text_marker.type = Marker.TEXT_VIEW_FACING
            text_marker.action = Marker.ADD
            
            text_marker.pose.position.x = world_x
            text_marker.pose.position.y = world_y
            text_marker.pose.position.z = 2.0  # Above human
            text_marker.pose.orientation.w = 1.0
            
            text_marker.scale.z = 0.3  # Text size
            text_marker.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)  # White
            text_marker.text = f"Human\n{distance:.2f}m"
            
            text_marker.lifetime.sec = 1
            marker_array.markers.append(text_marker)
            marker_id += 1
            
            # Create safety zone circle
            zone_marker = Marker()
            zone_marker.header.frame_id = "map"
            zone_marker.header.stamp = self.get_clock().now().to_msg()
            zone_marker.ns = "safety_zones"
            zone_marker.id = marker_id
            zone_marker.type = Marker.CYLINDER
            zone_marker.action = Marker.ADD
            
            zone_marker.pose.position.x = world_x
            zone_marker.pose.position.y = world_y
            zone_marker.pose.position.z = 0.01  # Ground level
            zone_marker.pose.orientation.w = 1.0
            
            zone_marker.scale.x = self.human_safety_distance * 2  # Diameter
            zone_marker.scale.y = self.human_safety_distance * 2
            zone_marker.scale.z = 0.02  # Thin disk
            
            zone_marker.color = ColorRGBA(r=1.0, g=0.0, b=0.0, a=0.2)  # Transparent red
            zone_marker.lifetime.sec = 1
            marker_array.markers.append(zone_marker)
            marker_id += 1
        
        # Publish markers
        self.human_marker_pub.publish(marker_array)
    
    def get_yaw_from_quaternion(self, orientation) -> float:
        """Extract yaw angle from quaternion"""
        siny_cosp = 2 * (orientation.w * orientation.z + orientation.x * orientation.y)
        cosy_cosp = 1 - 2 * (orientation.y * orientation.y + orientation.z * orientation.z)
        return np.arctan2(siny_cosp, cosy_cosp)

    def publish_threat_markers(self):
        """Publish RViz markers for all active threats with prioritization visualization"""
        from visualization_msgs.msg import Marker, MarkerArray
        from std_msgs.msg import ColorRGBA
        
        if not self.current_pose:
            return
        
        marker_array = MarkerArray()
        
        # Delete old markers
        delete_marker = Marker()
        delete_marker.action = Marker.DELETEALL
        marker_array.markers.append(delete_marker)
        
        # Get prioritized threats
        prioritized_threats = self.prioritize_threats()
        
        if not prioritized_threats:
            self.threat_marker_pub.publish(marker_array)
            return
        
        marker_id = 0
        
        # Visualize each threat
        for threat_id, threat_data in prioritized_threats:
            threat_type = threat_data['type']
            severity_score = threat_data['severity_score']
            distance = threat_data.get('distance')
            level = threat_data['level']
            
            # Skip human threats (they have their own visualization)
            if threat_type == ThreatType.HUMAN_DETECTED:
                continue
            
            # Determine position for visualization
            if distance is not None and self.current_scan:
                # Use LiDAR data to estimate threat position
                position = self.estimate_threat_position(distance)
            else:
                # Default position in front of robot
                position = (self.current_pose.pose.position.x + 1.0,
                           self.current_pose.pose.position.y,
                           0.5)
            
            # Create threat marker
            marker = Marker()
            marker.header.frame_id = "map"
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = "threats"
            marker.id = marker_id
            marker.type = Marker.CUBE if threat_type == ThreatType.STATIC_OBSTACLE else Marker.SPHERE
            marker.action = Marker.ADD
            
            marker.pose.position.x = position[0]
            marker.pose.position.y = position[1]
            marker.pose.position.z = position[2]
            marker.pose.orientation.w = 1.0
            
            # Size based on threat type
            if threat_type == ThreatType.CLIFF_EDGE:
                marker.scale.x = 2.0
                marker.scale.y = 0.5
                marker.scale.z = 0.1
            elif threat_type == ThreatType.DYNAMIC_OBSTACLE:
                marker.scale.x = 0.6
                marker.scale.y = 0.6
                marker.scale.z = 0.6
            else:
                marker.scale.x = 0.4
                marker.scale.y = 0.4
                marker.scale.z = 0.4
            
            # Color based on severity score and level
            marker.color = self.get_threat_color(level, severity_score)
            marker.lifetime.sec = 1
            marker_array.markers.append(marker)
            marker_id += 1
            
            # Add text label with severity score and priority rank
            text_marker = Marker()
            text_marker.header.frame_id = "map"
            text_marker.header.stamp = self.get_clock().now().to_msg()
            text_marker.ns = "threat_labels"
            text_marker.id = marker_id
            text_marker.type = Marker.TEXT_VIEW_FACING
            text_marker.action = Marker.ADD
            
            text_marker.pose.position.x = position[0]
            text_marker.pose.position.y = position[1]
            text_marker.pose.position.z = position[2] + 0.5
            text_marker.pose.orientation.w = 1.0
            
            text_marker.scale.z = 0.2
            text_marker.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)
            
            # Priority rank (1 = highest priority)
            priority_rank = prioritized_threats.index((threat_id, threat_data)) + 1
            text_marker.text = f"{threat_type.value}\nPriority: #{priority_rank}\nSeverity: {severity_score:.1f}"
            if distance:
                text_marker.text += f"\nDist: {distance:.2f}m"
            
            text_marker.lifetime.sec = 1
            marker_array.markers.append(text_marker)
            marker_id += 1
            
            # Add arrow pointing from robot to threat
            arrow_marker = Marker()
            arrow_marker.header.frame_id = "map"
            arrow_marker.header.stamp = self.get_clock().now().to_msg()
            arrow_marker.ns = "threat_arrows"
            arrow_marker.id = marker_id
            arrow_marker.type = Marker.ARROW
            arrow_marker.action = Marker.ADD
            
            # Arrow from robot to threat
            from geometry_msgs.msg import Point
            start_point = Point()
            start_point.x = self.current_pose.pose.position.x
            start_point.y = self.current_pose.pose.position.y
            start_point.z = 0.3
            
            end_point = Point()
            end_point.x = position[0]
            end_point.y = position[1]
            end_point.z = position[2]
            
            arrow_marker.points = [start_point, end_point]
            arrow_marker.scale.x = 0.05  # Shaft diameter
            arrow_marker.scale.y = 0.1   # Head diameter
            arrow_marker.scale.z = 0.15  # Head length
            
            # Color based on priority (highest priority = brightest)
            alpha = 1.0 - (priority_rank - 1) * 0.15  # Fade lower priority threats
            arrow_color = self.get_threat_color(level, severity_score)
            arrow_color.a = max(0.3, alpha)
            arrow_marker.color = arrow_color
            
            arrow_marker.lifetime.sec = 1
            marker_array.markers.append(arrow_marker)
            marker_id += 1
        
        # Publish all markers
        self.threat_marker_pub.publish(marker_array)
    
    def get_threat_color(self, level: SafetyLevel, severity_score: float) -> 'ColorRGBA':
        """Get color for threat visualization based on level and severity"""
        from std_msgs.msg import ColorRGBA
        
        # Base color on safety level
        if level == SafetyLevel.CRITICAL:
            return ColorRGBA(r=1.0, g=0.0, b=0.0, a=0.8)  # Red
        elif level == SafetyLevel.EMERGENCY:
            return ColorRGBA(r=1.0, g=0.3, b=0.0, a=0.7)  # Orange-red
        elif level == SafetyLevel.WARNING:
            return ColorRGBA(r=1.0, g=0.6, b=0.0, a=0.6)  # Orange
        elif level == SafetyLevel.CAUTION:
            return ColorRGBA(r=1.0, g=1.0, b=0.0, a=0.5)  # Yellow
        else:
            return ColorRGBA(r=0.0, g=1.0, b=0.0, a=0.4)  # Green
    
    def estimate_threat_position(self, distance: float) -> Tuple[float, float, float]:
        """Estimate threat position in world frame based on distance"""
        if not self.current_pose:
            return (0.0, 0.0, 0.5)
        
        # Get robot orientation
        robot_yaw = self.get_yaw_from_quaternion_helper(self.current_pose.pose.orientation)
        
        # Assume threat is in front of robot (could be enhanced with angle information)
        world_x = self.current_pose.pose.position.x + distance * np.cos(robot_yaw)
        world_y = self.current_pose.pose.position.y + distance * np.sin(robot_yaw)
        world_z = 0.5  # Default height
        
        return (world_x, world_y, world_z)
    
    def get_yaw_from_quaternion_helper(self, orientation) -> float:
        """Extract yaw angle from quaternion"""
        siny_cosp = 2 * (orientation.w * orientation.z + orientation.x * orientation.y)
        cosy_cosp = 1 - 2 * (orientation.y * orientation.y + orientation.z * orientation.z)
        return np.arctan2(siny_cosp, cosy_cosp)

def main(args=None):
    rclpy.init(args=args)
    node = AdvancedSafetySystem()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down advanced safety system...')
    except Exception as e:
        node.get_logger().error(f'Error in advanced safety system: {e}')
    finally:
        node.destroy_node()
        # Don't call rclpy.shutdown() - let launch system handle it

if __name__ == '__main__':
    main()
