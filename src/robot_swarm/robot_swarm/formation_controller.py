#!/usr/bin/env python3
"""
FormationController: Multi-robot formation control

This node manages:
- Formation definitions (line, wedge, circle)
- Formation maintenance during movement
- Collision avoidance between robots
- Dynamic formation reconfiguration
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional
from enum import Enum

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from geometry_msgs.msg import Twist, PoseStamped, Point
from nav_msgs.msg import Odometry
from std_msgs.msg import String
import json


class FormationType(Enum):
    """Types of formations."""
    LINE = "line"
    WEDGE = "wedge"
    CIRCLE = "circle"
    COLUMN = "column"
    DIAMOND = "diamond"


class FormationController(Node):
    """
    Formation control for multi-robot systems.
    
    Features:
    - Multiple formation types
    - Dynamic formation switching
    - Collision avoidance
    - Leader-follower control
    """
    
    def __init__(self):
        super().__init__('formation_controller')
        
        # Declare parameters
        self.declare_parameter('robot_id', '')
        self.declare_parameter('formation_type', 'line')
        self.declare_parameter('robot_index', 0)  # Position in formation
        self.declare_parameter('num_robots', 1)
        self.declare_parameter('spacing', 2.0)  # meters
        self.declare_parameter('formation_radius', 3.0)  # for circle formation
        self.declare_parameter('control_rate', 10.0)  # Hz
        self.declare_parameter('max_linear_vel', 0.5)
        self.declare_parameter('max_angular_vel', 1.0)
        self.declare_parameter('collision_distance', 1.0)  # meters
        
        # Get parameters
        self.robot_id = self.get_parameter('robot_id').value
        self.formation_type = FormationType(self.get_parameter('formation_type').value)
        self.robot_index = self.get_parameter('robot_index').value
        self.num_robots = self.get_parameter('num_robots').value
        self.spacing = self.get_parameter('spacing').value
        self.formation_radius = self.get_parameter('formation_radius').value
        self.control_rate = self.get_parameter('control_rate').value
        self.max_linear_vel = self.get_parameter('max_linear_vel').value
        self.max_angular_vel = self.get_parameter('max_angular_vel').value
        self.collision_distance = self.get_parameter('collision_distance').value
        
        # Robot state
        self.my_position = np.array([0.0, 0.0])
        self.my_orientation = 0.0
        self.my_velocity = np.array([0.0, 0.0])
        
        # Formation state
        self.leader_position = np.array([0.0, 0.0])
        self.leader_orientation = 0.0
        self.leader_velocity = np.array([0.0, 0.0])
        self.target_position = np.array([0.0, 0.0])
        
        # Other robots in formation
        self.robot_positions: Dict[str, np.ndarray] = {}
        
        # QoS profile
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Publishers
        self.cmd_vel_pub = self.create_publisher(
            Twist,
            f'/{self.robot_id}/cmd_vel',
            10
        )
        
        self.formation_status_pub = self.create_publisher(
            String,
            f'/{self.robot_id}/formation_status',
            10
        )
        
        # Subscribers
        self.odom_sub = self.create_subscription(
            Odometry,
            f'/{self.robot_id}/odom',
            self.odom_callback,
            sensor_qos
        )
        
        self.leader_odom_sub = self.create_subscription(
            Odometry,
            '/leader/odom',
            self.leader_odom_callback,
            sensor_qos
        )
        
        # Subscribe to other robots' positions
        for i in range(self.num_robots):
            if i != self.robot_index:
                robot_name = f'robot_{i}'
                self.create_subscription(
                    Odometry,
                    f'/{robot_name}/odom',
                    lambda msg, name=robot_name: self.robot_odom_callback(msg, name),
                    sensor_qos
                )
        
        # Control timer
        self.control_timer = self.create_timer(
            1.0 / self.control_rate,
            self.control_loop
        )
        
        self.get_logger().info(
            f'FormationController initialized for {self.robot_id} '
            f'(index {self.robot_index}, formation: {self.formation_type.value})'
        )
    
    def odom_callback(self, msg: Odometry):
        """Update own position and orientation."""
        self.my_position = np.array([
            msg.pose.pose.position.x,
            msg.pose.pose.position.y
        ])
        self.my_orientation = self.get_yaw_from_quaternion(msg.pose.pose.orientation)
        self.my_velocity = np.array([
            msg.twist.twist.linear.x,
            msg.twist.twist.angular.z
        ])
    
    def leader_odom_callback(self, msg: Odometry):
        """Update leader position and orientation."""
        self.leader_position = np.array([
            msg.pose.pose.position.x,
            msg.pose.pose.position.y
        ])
        self.leader_orientation = self.get_yaw_from_quaternion(msg.pose.pose.orientation)
        self.leader_velocity = np.array([
            msg.twist.twist.linear.x,
            msg.twist.twist.angular.z
        ])
    
    def robot_odom_callback(self, msg: Odometry, robot_name: str):
        """Update other robot positions."""
        self.robot_positions[robot_name] = np.array([
            msg.pose.pose.position.x,
            msg.pose.pose.position.y
        ])
    
    def get_yaw_from_quaternion(self, q) -> float:
        """Extract yaw angle from quaternion."""
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny_cosp, cosy_cosp)
    
    def calculate_formation_position(self) -> np.ndarray:
        """
        Calculate target position in formation based on formation type.
        
        Returns:
            Target position (x, y) in world frame
        """
        if self.formation_type == FormationType.LINE:
            return self.calculate_line_formation()
        elif self.formation_type == FormationType.WEDGE:
            return self.calculate_wedge_formation()
        elif self.formation_type == FormationType.CIRCLE:
            return self.calculate_circle_formation()
        elif self.formation_type == FormationType.COLUMN:
            return self.calculate_column_formation()
        elif self.formation_type == FormationType.DIAMOND:
            return self.calculate_diamond_formation()
        else:
            return self.leader_position
    
    def calculate_line_formation(self) -> np.ndarray:
        """Calculate position for line formation."""
        # Robots arranged in a line perpendicular to leader's heading
        offset_x = 0.0
        offset_y = (self.robot_index - (self.num_robots - 1) / 2) * self.spacing
        
        # Rotate offset by leader's orientation
        cos_theta = math.cos(self.leader_orientation)
        sin_theta = math.sin(self.leader_orientation)
        
        rotated_x = offset_x * cos_theta - offset_y * sin_theta
        rotated_y = offset_x * sin_theta + offset_y * cos_theta
        
        return self.leader_position + np.array([rotated_x, rotated_y])
    
    def calculate_wedge_formation(self) -> np.ndarray:
        """Calculate position for wedge formation."""
        # V-shaped formation behind leader
        row = self.robot_index // 2
        side = 1 if self.robot_index % 2 == 0 else -1
        
        offset_x = -row * self.spacing  # Behind leader
        offset_y = side * row * self.spacing * 0.5  # Spread to sides
        
        # Rotate by leader's orientation
        cos_theta = math.cos(self.leader_orientation)
        sin_theta = math.sin(self.leader_orientation)
        
        rotated_x = offset_x * cos_theta - offset_y * sin_theta
        rotated_y = offset_x * sin_theta + offset_y * cos_theta
        
        return self.leader_position + np.array([rotated_x, rotated_y])
    
    def calculate_circle_formation(self) -> np.ndarray:
        """Calculate position for circle formation."""
        # Robots arranged in a circle around leader
        angle = 2 * math.pi * self.robot_index / self.num_robots
        
        offset_x = self.formation_radius * math.cos(angle)
        offset_y = self.formation_radius * math.sin(angle)
        
        return self.leader_position + np.array([offset_x, offset_y])
    
    def calculate_column_formation(self) -> np.ndarray:
        """Calculate position for column formation."""
        # Robots arranged in a column behind leader
        offset_x = -self.robot_index * self.spacing
        offset_y = 0.0
        
        # Rotate by leader's orientation
        cos_theta = math.cos(self.leader_orientation)
        sin_theta = math.sin(self.leader_orientation)
        
        rotated_x = offset_x * cos_theta - offset_y * sin_theta
        rotated_y = offset_x * sin_theta + offset_y * cos_theta
        
        return self.leader_position + np.array([rotated_x, rotated_y])
    
    def calculate_diamond_formation(self) -> np.ndarray:
        """Calculate position for diamond formation."""
        # Diamond shape with leader at front
        if self.robot_index == 0:
            offset = np.array([0.0, self.spacing])
        elif self.robot_index == 1:
            offset = np.array([0.0, -self.spacing])
        elif self.robot_index == 2:
            offset = np.array([-self.spacing, 0.0])
        else:
            offset = np.array([0.0, 0.0])
        
        # Rotate by leader's orientation
        cos_theta = math.cos(self.leader_orientation)
        sin_theta = math.sin(self.leader_orientation)
        
        rotated_x = offset[0] * cos_theta - offset[1] * sin_theta
        rotated_y = offset[0] * sin_theta + offset[1] * cos_theta
        
        return self.leader_position + np.array([rotated_x, rotated_y])
    
    def check_collision_avoidance(self, desired_velocity: np.ndarray) -> np.ndarray:
        """
        Apply collision avoidance with other robots.
        
        Args:
            desired_velocity: Desired velocity vector
            
        Returns:
            Adjusted velocity vector
        """
        avoidance_force = np.array([0.0, 0.0])
        
        for robot_name, robot_pos in self.robot_positions.items():
            # Calculate distance to other robot
            diff = self.my_position - robot_pos
            distance = np.linalg.norm(diff)
            
            # If too close, add repulsive force
            if distance < self.collision_distance and distance > 0.1:
                # Repulsive force inversely proportional to distance
                force_magnitude = (self.collision_distance - distance) / distance
                force_direction = diff / distance
                avoidance_force += force_magnitude * force_direction
        
        # Combine desired velocity with avoidance force
        adjusted_velocity = desired_velocity + avoidance_force * 0.5
        
        return adjusted_velocity
    
    def control_loop(self):
        """Main control loop for formation maintenance."""
        # Calculate target position in formation
        self.target_position = self.calculate_formation_position()
        
        # Calculate error
        error = self.target_position - self.my_position
        distance_error = np.linalg.norm(error)
        
        if distance_error < 0.1:
            # Already at target position
            self.publish_velocity(0.0, 0.0)
            return
        
        # Calculate desired velocity (proportional control)
        k_p = 0.5  # Proportional gain
        desired_velocity = k_p * error
        
        # Apply collision avoidance
        adjusted_velocity = self.check_collision_avoidance(desired_velocity)
        
        # Convert to robot frame
        angle_to_target = math.atan2(adjusted_velocity[1], adjusted_velocity[0])
        angle_error = self.normalize_angle(angle_to_target - self.my_orientation)
        
        # Calculate linear and angular velocities
        linear_vel = np.linalg.norm(adjusted_velocity)
        angular_vel = 2.0 * angle_error  # Proportional control for orientation
        
        # Limit velocities
        linear_vel = np.clip(linear_vel, -self.max_linear_vel, self.max_linear_vel)
        angular_vel = np.clip(angular_vel, -self.max_angular_vel, self.max_angular_vel)
        
        # Reduce linear velocity if large angular error
        if abs(angle_error) > math.pi / 4:
            linear_vel *= 0.5
        
        # Publish velocity command
        self.publish_velocity(linear_vel, angular_vel)
        
        # Publish formation status
        self.publish_formation_status(distance_error)
    
    def publish_velocity(self, linear: float, angular: float):
        """Publish velocity command."""
        cmd_msg = Twist()
        cmd_msg.linear.x = linear
        cmd_msg.angular.z = angular
        self.cmd_vel_pub.publish(cmd_msg)
    
    def publish_formation_status(self, error: float):
        """Publish formation status."""
        status = {
            'robot_id': self.robot_id,
            'formation_type': self.formation_type.value,
            'position_error': float(error),
            'target_position': self.target_position.tolist(),
            'current_position': self.my_position.tolist()
        }
        
        msg = String()
        msg.data = json.dumps(status)
        self.formation_status_pub.publish(msg)
    
    def normalize_angle(self, angle: float) -> float:
        """Normalize angle to [-pi, pi]."""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle


def main(args=None):
    """Main function."""
    rclpy.init(args=args)
    
    try:
        node = FormationController()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
