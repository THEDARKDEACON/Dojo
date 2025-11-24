#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from std_srvs.srv import Trigger
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
        
        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # Service Clients
        self.exposure_client = self.create_client(Trigger, '/camera/set_exposure')
        
        # State
        self.corners = self.get_parameter('room_corners').value
        self.step_size = self.get_parameter('step_size').value
        self.max_speed = self.get_parameter('max_speed').value
        self.crab_angle_rad = math.radians(self.get_parameter('crab_angle').value)
        
        self.path = []
        self.current_waypoint_idx = 0
        self.is_surveying = False
        
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
        # We don't block here, just fire and forget for this simple example
        self.get_logger().info("Requested exposure lock")

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
            self.get_logger().info("Survey Complete")
            return

        target_x, target_y = self.path[self.current_waypoint_idx]
        
        # In a real implementation, we would need current pose from TF/Odometry
        # For this scaffold, we'll assume we have a function get_current_pose()
        # Since we don't have TF listener set up in this snippet, I will mock the logic
        # logic: Move towards target_x, target_y BUT keep orientation at path_heading + 45 deg
        
        # TODO: Integrate TF Listener to get 'current_x', 'current_y', 'current_yaw'
        # For now, we print the command logic
        
        # Vector to target
        # dx = target_x - current_x
        # dy = target_y - current_y
        # dist = sqrt(dx*dx + dy*dy)
        
        # if dist < 0.1:
        #    self.current_waypoint_idx += 1
        #    return
            
        # Desired movement vector (normalized)
        # move_x = dx / dist * self.max_speed
        # move_y = dy / dist * self.max_speed
        
        # Holonomic Control (Mecanum)
        # We want to move in (move_x, move_y) but face (path_heading + 45)
        # This requires transforming the velocity vector into the robot's frame
        
        twist = Twist()
        # Placeholder for "Crab Walk" logic
        # twist.linear.x = ...
        # twist.linear.y = ... 
        # twist.angular.z = ... (PID to maintain 45 deg offset)
        
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
