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
from typing import Dict, List, Tuple
import time
from enum import Enum

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
            'caution': 1.5,     # Reduce speed
            'normal': 3.0       # Normal operation
        }
        
        # Publishers
        self.cmd_vel_safe_pub = self.create_publisher(Twist, '/cmd_vel_safe', 10)
        self.safety_status_pub = self.create_publisher(String, '/safety_status', 10)
        self.emergency_stop_pub = self.create_publisher(Bool, '/emergency_stop', 10)
        self.safety_level_pub = self.create_publisher(Int32, '/safety_level', 10)
        
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
        
        # Timers
        self.safety_timer = self.create_timer(0.1, self.safety_check)  # 10 Hz
        self.prediction_timer = self.create_timer(0.2, self.update_predictions)  # 5 Hz
        
        self.get_logger().info("🛡️ Advanced Safety System initialized - Multi-layer protection active!")
    
    def cmd_vel_callback(self, msg: Twist):
        """Intercept and validate velocity commands"""
        self.last_cmd_vel = msg
        
        # Apply safety filtering
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
        
        # Check safety zones
        if min_distance < self.safety_zones['critical']:
            self.add_threat(ThreatType.STATIC_OBSTACLE, SafetyLevel.CRITICAL, 
                          f"Critical obstacle at {min_distance:.2f}m")
        elif min_distance < self.safety_zones['warning']:
            self.add_threat(ThreatType.STATIC_OBSTACLE, SafetyLevel.WARNING,
                          f"Warning obstacle at {min_distance:.2f}m")
        elif min_distance < self.safety_zones['caution']:
            self.add_threat(ThreatType.STATIC_OBSTACLE, SafetyLevel.CAUTION,
                          f"Caution obstacle at {min_distance:.2f}m")
        
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
                                      f"Predicted dynamic obstacle collision in {self.prediction_horizon}s")
    
    def detect_visual_threats(self, image: np.ndarray):
        """Detect visual safety threats"""
        # Simplified human detection using color-based approach
        # In practice, use YOLO or other object detection
        
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
                self.add_threat(ThreatType.HUMAN_DETECTED, SafetyLevel.WARNING,
                              f"Human detected in camera view (area: {area})")
        
        # Detect cliff edges (simplified - look for large dark areas at bottom)
        bottom_region = image[int(image.shape[0] * 0.8):, :]
        gray_bottom = cv2.cvtColor(bottom_region, cv2.COLOR_BGR2GRAY)
        dark_pixels = np.sum(gray_bottom < 50)
        total_pixels = gray_bottom.size
        
        if dark_pixels / total_pixels > 0.7:  # 70% dark pixels
            self.add_threat(ThreatType.CLIFF_EDGE, SafetyLevel.CRITICAL,
                          "Potential cliff edge detected")
    
    def add_threat(self, threat_type: ThreatType, level: SafetyLevel, description: str):
        """Add or update a safety threat"""
        threat_id = f"{threat_type.value}_{int(time.time() * 10)}"
        
        self.active_threats[threat_id] = {
            'type': threat_type,
            'level': level,
            'description': description,
            'timestamp': time.time()
        }
        
        # Update overall safety level
        self.update_safety_level()
    
    def update_safety_level(self):
        """Update overall safety level based on active threats"""
        if not self.active_threats:
            self.current_safety_level = SafetyLevel.NORMAL
            return
        
        # Find highest threat level
        max_level = max(threat['level'] for threat in self.active_threats.values())
        self.current_safety_level = max_level
        
        # Publish safety level
        level_msg = Int32()
        level_msg.data = self.current_safety_level.value
        self.safety_level_pub.publish(level_msg)
    
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

def main(args=None):
    rclpy.init(args=args)
    node = AdvancedSafetySystem()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()