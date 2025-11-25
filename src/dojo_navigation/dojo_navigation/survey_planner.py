#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped, TransformStamped
from std_srvs.srv import Trigger
from tf2_ros import TransformListener, Buffer
import math
import numpy as np
import time

class SurveyPlanner(Node):
    def __init__(self):
        super().__init__('survey_planner')
        
        # Parameters
        self.declare_parameter('room_corners', [0.0, 0.0, 5.0, 5.0]) # x1, y1, x2, y2
        self.declare_parameter('step_size', 0.5) # Distance between zig-zag lines
        self.declare_parameter('max_speed', 0.2) # m/s
        self.declare_parameter('crab_angle', 45.0) # Degrees
        self.declare_parameter('position_tolerance', 0.1) # m
        self.declare_parameter('angle_kp', 1.0) # PID proportional gain for angle
        
        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # Service Clients
        self.exposure_client = self.create_client(Trigger, '/camera/set_exposure')
        
        # TF2
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        # State
        self.corners = self.get_parameter('room_corners').value
        self.step_size = self.get_parameter('step_size').value
        self.max_speed = self.get_parameter('max_speed').value
        self.crab_angle_rad = math.radians(self.get_parameter('crab_angle').value)
        self.position_tolerance = self.get_parameter('position_tolerance').value
        self.angle_kp = self.get_parameter('angle_kp').value
        
        self.path = []
        self.current_waypoint_idx = 0
        self.is_surveying = False
        
        # Current pose (will be updated from TF)
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_yaw = 0.0
        
        self.get_logger().info("Survey Planner Initialized")

    def generate_lawnmower_path(self):
        """Generates a zig-zag path within the defined rectangle."""
        x1, y1, x2, y2 = self.corners
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)
        
        path = []
        y = min_y
        direction = 1 # 1 for right, -1 for left
        
        while y <= max_y:
            if direction == 1:
                path.append((min_x, y))
                path.append((max_x, y))
            else:
                path.append((max_x, y))
                path.append((min_x, y))
            
            y += self.step_size
            direction *= -1
            
        self.path = path
        self.get_logger().info(f"Generated path with {len(path)} waypoints")

    def lock_exposure(self):
        """Calls the service to lock camera exposure."""
        if not self.exposure_client.wait_for_service(timeout_sec=2.0):
            self.get_logger().warn("Exposure service not available, skipping.")
            return
            
        req = Trigger.Request()
        future = self.exposure_client.call_async(req)
        self.get_logger().info("Requested exposure lock")

    def get_current_pose(self):
        """Get current robot pose from TF."""
        try:
            transform = self.tf_buffer.lookup_transform(
                'map',
                'base_link',
                rclpy.time.Time(),
                timeout=rclpy.duration.Duration(seconds=0.1)
            )
            
            # Extract position
            self.current_x = transform.transform.translation.x
            self.current_y = transform.transform.translation.y
            
            # Extract yaw from quaternion
            quat = transform.transform.rotation
            siny_cosp = 2 * (quat.w * quat.z + quat.x * quat.y)
            cosy_cosp = 1 - 2 * (quat.y * quat.y + quat.z * quat.z)
            self.current_yaw = math.atan2(siny_cosp, cosy_cosp)
            
            return True
        except Exception as e:
            self.get_logger().warn(f"TF lookup failed: {e}", throttle_duration_sec=2.0)
            return False

    def start_survey(self):
        self.generate_lawnmower_path()
        self.lock_exposure()
        self.is_surveying = True
        self.current_waypoint_idx = 0
        
        # Start control loop
        self.timer = self.create_timer(0.1, self.control_loop)

    def control_loop(self):
        if not self.is_surveying or self.current_waypoint_idx >= len(self.path):
            self.stop_robot()
            self.is_surveying = False
            if self.current_waypoint_idx >= len(self.path):
                self.get_logger().info("Survey Complete")
            return

        # Get current pose from TF
        if not self.get_current_pose():
            return  # Skip this iteration if TF is not available
        
        target_x, target_y = self.path[self.current_waypoint_idx]
        
        # Calculate vector to target
        dx = target_x - self.current_x
        dy = target_y - self.current_y
        dist = math.sqrt(dx*dx + dy*dy)
        
        # Check if we've reached the waypoint
        if dist < self.position_tolerance:
            self.current_waypoint_idx += 1
            self.get_logger().info(f"Reached waypoint {self.current_waypoint_idx}/{len(self.path)}")
            return
        
        # Calculate desired path heading
        path_heading = math.atan2(dy, dx)
        
        # Calculate desired robot heading (path heading + crab angle)
        desired_heading = path_heading + self.crab_angle_rad
        
        # Normalize to [-pi, pi]
        while desired_heading > math.pi:
            desired_heading -= 2 * math.pi
        while desired_heading < -math.pi:
            desired_heading += 2 * math.pi
        
        # Calculate heading error
        heading_error = desired_heading - self.current_yaw
        while heading_error > math.pi:
            heading_error -= 2 * math.pi
        while heading_error < -math.pi:
            heading_error += 2 * math.pi
        
        # Calculate desired movement vector (normalized)
        move_x = (dx / dist) * self.max_speed
        move_y = (dy / dist) * self.max_speed
        
        # Transform movement vector to robot frame
        # Robot is at angle self.current_yaw, we want to move in global (move_x, move_y)
        cos_yaw = math.cos(self.current_yaw)
        sin_yaw = math.sin(self.current_yaw)
        
        robot_vx = cos_yaw * move_x + sin_yaw * move_y
        robot_vy = -sin_yaw * move_x + cos_yaw * move_y
        
        # PID control for angular velocity to maintain desired heading
        angular_z = self.angle_kp * heading_error
        
        # Limit angular velocity
        max_angular = 0.5  # rad/s
        angular_z = max(-max_angular, min(max_angular, angular_z))
        
        # Publish velocity command
        twist = Twist()
        twist.linear.x = robot_vx
        twist.linear.y = robot_vy  # Only works for holonomic robots (mecanum)
        twist.angular.z = angular_z
        
        self.cmd_vel_pub.publish(twist)

    def stop_robot(self):
        self.cmd_vel_pub.publish(Twist())

def main(args=None):
    rclpy.init(args=args)
    node = SurveyPlanner()
    
    # For testing, auto-start
    node.start_survey()
    
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
