#!/usr/bin/env python3
"""
Autonomous Movement Controller for Map-Independent Navigation

This node provides autonomous movement capabilities that don't depend on existing maps.
It implements various movement patterns and obstacle avoidance using direct sensor feedback.
"""

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup

import numpy as np
import math
import time
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple, List

from geometry_msgs.msg import Twist, PoseStamped
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import OccupancyGrid
from std_msgs.msg import String, Bool
from robot_interfaces.msg import RobotState

import tf2_ros
from tf2_ros import TransformException


class MovementPattern(Enum):
    """Available movement patterns"""
    SPIRAL = "spiral"
    GRID = "grid" 
    WALL_FOLLOW = "wall_follow"
    RANDOM_WALK = "random_walk"
    STOP = "stop"


@dataclass
class MovementCommand:
    """Structure for movement commands"""
    pattern_type: MovementPattern
    linear_velocity: float
    angular_velocity: float
    duration: float
    safety_enabled: bool = True


@dataclass
class ObstacleInfo:
    """Information about detected obstacles"""
    min_distance: float
    closest_angle: float
    left_clear: bool
    right_clear: bool
    front_clear: bool


class AutonomousMovementController(Node):
    """
    Autonomous Movement Controller that provides map-independent navigation
    """
    
    def __init__(self):
        super().__init__('autonomous_movement_controller')
        
        # Parameters
        self.declare_parameter('default_linear_speed', 0.3)
        self.declare_parameter('default_angular_speed', 0.5)
        self.declare_parameter('obstacle_threshold', 0.8)
        self.declare_parameter('safety_threshold', 0.5)
        self.declare_parameter('spiral_increment', 0.1)
        self.declare_parameter('grid_cell_size', 2.0)
        self.declare_parameter('wall_follow_distance', 0.6)
        self.declare_parameter('movement_timeout', 30.0)
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('map_frame', 'map')
        
        # Get parameters
        self.default_linear_speed = self.get_parameter('default_linear_speed').value
        self.default_angular_speed = self.get_parameter('default_angular_speed').value
        self.obstacle_threshold = self.get_parameter('obstacle_threshold').value
        self.safety_threshold = self.get_parameter('safety_threshold').value
        self.spiral_increment = self.get_parameter('spiral_increment').value
        self.grid_cell_size = self.get_parameter('grid_cell_size').value
        self.wall_follow_distance = self.get_parameter('wall_follow_distance').value
        self.movement_timeout = self.get_parameter('movement_timeout').value
        self.base_frame = self.get_parameter('base_frame').value
        self.map_frame = self.get_parameter('map_frame').value
        
        # State variables
        self.current_pattern = MovementPattern.STOP
        self.movement_active = False
        self.last_scan = None
        self.obstacle_info = None
        self.pattern_start_time = None
        self.movement_start_time = None
        
        # Pattern-specific state
        self.spiral_radius = 0.5
        self.spiral_angle = 0.0
        self.grid_target_x = 0.0
        self.grid_target_y = 0.0
        self.grid_visited = set()
        self.wall_follow_side = 'right'  # 'left' or 'right'
        self.random_walk_direction = 0.0
        self.random_walk_change_time = 0.0
        
        # Safety and monitoring
        self.emergency_stop = False
        self.last_movement_time = None
        self.stuck_detection_threshold = 5.0  # seconds
        self.position_history = []
        
        # Callback group for concurrent operations
        self.callback_group = ReentrantCallbackGroup()
        
        # TF2 buffer and listener
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        
        # Subscribers
        self.scan_subscriber = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10,
            callback_group=self.callback_group
        )
        
        self.map_subscriber = self.create_subscription(
            OccupancyGrid,
            '/map',
            self.map_callback,
            10,
            callback_group=self.callback_group
        )
        
        self.pattern_subscriber = self.create_subscription(
            String,
            '/autonomous_movement/pattern',
            self.pattern_callback,
            10,
            callback_group=self.callback_group
        )
        
        self.enable_subscriber = self.create_subscription(
            Bool,
            '/autonomous_movement/enable',
            self.enable_callback,
            10,
            callback_group=self.callback_group
        )
        
        # Publishers
        self.cmd_vel_publisher = self.create_publisher(
            Twist,
            '/cmd_vel_autonomous',
            10
        )
        
        self.status_publisher = self.create_publisher(
            RobotState,
            '/autonomous_movement/status',
            10
        )
        
        self.obstacle_publisher = self.create_publisher(
            String,
            '/autonomous_movement/obstacles',
            10
        )
        
        # Timers
        self.movement_timer = self.create_timer(
            0.1,  # 10 Hz movement control
            self.movement_control_loop,
            callback_group=self.callback_group
        )
        
        self.status_timer = self.create_timer(
            1.0,  # 1 Hz status updates
            self.publish_status,
            callback_group=self.callback_group
        )
        
        self.stuck_detection_timer = self.create_timer(
            2.0,  # Check for stuck condition every 2 seconds
            self.check_stuck_condition,
            callback_group=self.callback_group
        )
        
        self.get_logger().info("🤖 Autonomous Movement Controller initialized")
        self.get_logger().info(f"📊 Configuration: linear_speed={self.default_linear_speed}, "
                              f"angular_speed={self.default_angular_speed}, "
                              f"obstacle_threshold={self.obstacle_threshold}")
        self.get_logger().info("⏳ Waiting for sensor data and commands...")
    
    def scan_callback(self, msg: LaserScan):
        """Process LiDAR scan data"""
        self.last_scan = msg
        self.obstacle_info = self.analyze_obstacles(msg)
        
        # Emergency stop if obstacle too close
        if self.obstacle_info and self.obstacle_info.min_distance < self.safety_threshold:
            if not self.emergency_stop:
                self.get_logger().warn(f"🚨 Emergency stop! Obstacle at {self.obstacle_info.min_distance:.2f}m")
                self.emergency_stop = True
                self.stop_robot()
        else:
            if self.emergency_stop:
                self.get_logger().info("✅ Emergency stop cleared")
                self.emergency_stop = False
    
    def map_callback(self, msg: OccupancyGrid):
        """Process map data for enhanced navigation"""
        # This can be used for more sophisticated movement patterns
        # For now, we focus on sensor-based navigation
        pass
    
    def pattern_callback(self, msg: String):
        """Handle pattern change requests"""
        try:
            new_pattern = MovementPattern(msg.data)
            self.set_movement_pattern(new_pattern)
        except ValueError:
            self.get_logger().warn(f"Unknown movement pattern: {msg.data}")
    
    def enable_callback(self, msg: Bool):
        """Handle enable/disable requests"""
        if msg.data:
            self.enable_movement()
        else:
            self.disable_movement()
    
    def analyze_obstacles(self, scan: LaserScan) -> ObstacleInfo:
        """Analyze LiDAR data to detect obstacles"""
        if not scan.ranges:
            return ObstacleInfo(float('inf'), 0.0, True, True, True)
        
        ranges = np.array(scan.ranges)
        # Filter out invalid readings
        valid_ranges = ranges[(ranges >= scan.range_min) & (ranges <= scan.range_max)]
        
        if len(valid_ranges) == 0:
            return ObstacleInfo(float('inf'), 0.0, True, True, True)
        
        min_distance = np.min(valid_ranges)
        min_index = np.argmin(ranges)
        closest_angle = scan.angle_min + min_index * scan.angle_increment
        
        # Analyze different sectors
        num_ranges = len(ranges)
        front_sector = ranges[num_ranges//3:2*num_ranges//3]
        left_sector = ranges[2*num_ranges//3:]
        right_sector = ranges[:num_ranges//3]
        
        # Check if sectors are clear
        front_clear = np.all(front_sector > self.obstacle_threshold) or len(front_sector) == 0
        left_clear = np.all(left_sector > self.obstacle_threshold) or len(left_sector) == 0
        right_clear = np.all(right_sector > self.obstacle_threshold) or len(right_sector) == 0
        
        return ObstacleInfo(
            min_distance=min_distance,
            closest_angle=closest_angle,
            left_clear=left_clear,
            right_clear=right_clear,
            front_clear=front_clear
        )
    
    def get_robot_position(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Get current robot position and orientation"""
        try:
            transform = self.tf_buffer.lookup_transform(
                self.map_frame,
                self.base_frame,
                rclpy.time.Time()
            )
            
            x = transform.transform.translation.x
            y = transform.transform.translation.y
            
            # Extract yaw from quaternion
            quat = transform.transform.rotation
            yaw = math.atan2(
                2.0 * (quat.w * quat.z + quat.x * quat.y),
                1.0 - 2.0 * (quat.y * quat.y + quat.z * quat.z)
            )
            
            return x, y, yaw
            
        except TransformException as e:
            self.get_logger().debug(f"Could not get robot position: {e}")
            return None, None, None
    
    def set_movement_pattern(self, pattern: MovementPattern):
        """Set the current movement pattern"""
        if pattern != self.current_pattern:
            self.get_logger().info(f"🔄 Switching to {pattern.value} movement pattern")
            self.current_pattern = pattern
            self.pattern_start_time = time.time()
            self.reset_pattern_state()
    
    def reset_pattern_state(self):
        """Reset pattern-specific state variables"""
        if self.current_pattern == MovementPattern.SPIRAL:
            self.spiral_radius = 0.5
            self.spiral_angle = 0.0
        elif self.current_pattern == MovementPattern.GRID:
            self.grid_visited.clear()
            x, y, _ = self.get_robot_position()
            if x is not None and y is not None:
                self.grid_target_x = x
                self.grid_target_y = y
        elif self.current_pattern == MovementPattern.WALL_FOLLOW:
            self.wall_follow_side = 'right'
        elif self.current_pattern == MovementPattern.RANDOM_WALK:
            self.random_walk_direction = np.random.uniform(0, 2 * np.pi)
            self.random_walk_change_time = time.time()
    
    def enable_movement(self):
        """Enable autonomous movement"""
        if not self.movement_active:
            self.get_logger().info("✅ Autonomous movement enabled")
            self.movement_active = True
            self.movement_start_time = time.time()
            if self.current_pattern == MovementPattern.STOP:
                self.set_movement_pattern(MovementPattern.SPIRAL)  # Default pattern
    
    def disable_movement(self):
        """Disable autonomous movement"""
        if self.movement_active:
            self.get_logger().info("🛑 Autonomous movement disabled")
            self.movement_active = False
            self.stop_robot()
    
    def stop_robot(self):
        """Send stop command to robot"""
        twist = Twist()
        self.cmd_vel_publisher.publish(twist)
    
    def movement_control_loop(self):
        """Main movement control loop"""
        if not self.movement_active or self.emergency_stop:
            return
        
        if self.last_scan is None or self.obstacle_info is None:
            self.get_logger().debug("⏳ Waiting for sensor data...")
            return
        
        # Check for pattern timeout
        if (self.pattern_start_time and 
            time.time() - self.pattern_start_time > self.movement_timeout):
            self.get_logger().info("⏰ Pattern timeout, switching to random walk")
            self.set_movement_pattern(MovementPattern.RANDOM_WALK)
        
        # Generate movement command based on current pattern
        twist = self.generate_movement_command()
        
        if twist:
            self.cmd_vel_publisher.publish(twist)
            self.last_movement_time = time.time()
    
    def generate_movement_command(self) -> Optional[Twist]:
        """Generate movement command based on current pattern and sensor data"""
        if self.current_pattern == MovementPattern.SPIRAL:
            return self.generate_spiral_movement()
        elif self.current_pattern == MovementPattern.GRID:
            return self.generate_grid_movement()
        elif self.current_pattern == MovementPattern.WALL_FOLLOW:
            return self.generate_wall_follow_movement()
        elif self.current_pattern == MovementPattern.RANDOM_WALK:
            return self.generate_random_walk_movement()
        else:
            return None
    
    def generate_spiral_movement(self) -> Twist:
        """Generate spiral movement pattern"""
        twist = Twist()
        
        # Check for obstacles and adjust
        if not self.obstacle_info.front_clear:
            # Turn away from obstacle
            if self.obstacle_info.right_clear:
                twist.angular.z = -self.default_angular_speed
            elif self.obstacle_info.left_clear:
                twist.angular.z = self.default_angular_speed
            else:
                # Reverse if blocked
                twist.linear.x = -self.default_linear_speed * 0.5
                twist.angular.z = self.default_angular_speed
        else:
            # Normal spiral movement
            self.spiral_angle += 0.1
            self.spiral_radius += self.spiral_increment * 0.01
            
            # Limit spiral radius
            if self.spiral_radius > 3.0:
                self.spiral_radius = 0.5
                self.spiral_angle = 0.0
            
            twist.linear.x = self.default_linear_speed
            twist.angular.z = self.default_angular_speed * 0.3 / max(self.spiral_radius, 0.1)
        
        return twist
    
    def generate_grid_movement(self) -> Twist:
        """Generate grid-based movement pattern"""
        twist = Twist()
        
        x, y, yaw = self.get_robot_position()
        if x is None:
            # Fallback to simple forward movement
            twist.linear.x = self.default_linear_speed
            return twist
        
        # Calculate distance to current target
        dx = self.grid_target_x - x
        dy = self.grid_target_y - y
        distance_to_target = math.sqrt(dx*dx + dy*dy)
        
        # If close to target, select new target
        if distance_to_target < 0.5:
            self.select_next_grid_target(x, y)
            dx = self.grid_target_x - x
            dy = self.grid_target_y - y
        
        # Calculate desired heading
        target_angle = math.atan2(dy, dx)
        angle_diff = target_angle - yaw
        
        # Normalize angle difference
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        
        # Check for obstacles
        if not self.obstacle_info.front_clear:
            # Obstacle avoidance
            if self.obstacle_info.right_clear:
                twist.angular.z = -self.default_angular_speed
            elif self.obstacle_info.left_clear:
                twist.angular.z = self.default_angular_speed
            else:
                twist.linear.x = -self.default_linear_speed * 0.3
                twist.angular.z = self.default_angular_speed
        else:
            # Move towards target
            if abs(angle_diff) > 0.2:
                # Turn towards target
                twist.angular.z = self.default_angular_speed * np.sign(angle_diff)
            else:
                # Move forward
                twist.linear.x = self.default_linear_speed
                twist.angular.z = angle_diff * 0.5  # Small correction
        
        return twist
    
    def select_next_grid_target(self, current_x: float, current_y: float):
        """Select next grid cell to visit"""
        # Round current position to grid
        grid_x = round(current_x / self.grid_cell_size) * self.grid_cell_size
        grid_y = round(current_y / self.grid_cell_size) * self.grid_cell_size
        
        # Mark current cell as visited
        self.grid_visited.add((grid_x, grid_y))
        
        # Find unvisited adjacent cells
        candidates = [
            (grid_x + self.grid_cell_size, grid_y),
            (grid_x - self.grid_cell_size, grid_y),
            (grid_x, grid_y + self.grid_cell_size),
            (grid_x, grid_y - self.grid_cell_size)
        ]
        
        unvisited = [cell for cell in candidates if cell not in self.grid_visited]
        
        if unvisited:
            # Choose closest unvisited cell
            distances = [math.sqrt((cell[0] - current_x)**2 + (cell[1] - current_y)**2) 
                        for cell in unvisited]
            min_idx = np.argmin(distances)
            self.grid_target_x, self.grid_target_y = unvisited[min_idx]
        else:
            # All adjacent cells visited, pick a random direction
            angle = np.random.uniform(0, 2 * math.pi)
            self.grid_target_x = current_x + self.grid_cell_size * math.cos(angle)
            self.grid_target_y = current_y + self.grid_cell_size * math.sin(angle)
    
    def generate_wall_follow_movement(self) -> Twist:
        """Generate wall-following movement"""
        twist = Twist()
        
        if not self.last_scan:
            return twist
        
        ranges = np.array(self.last_scan.ranges)
        num_ranges = len(ranges)
        
        # Get wall distance based on follow side
        if self.wall_follow_side == 'right':
            wall_ranges = ranges[:num_ranges//4]  # Right side
            turn_direction = -1  # Turn right to follow wall
        else:
            wall_ranges = ranges[3*num_ranges//4:]  # Left side
            turn_direction = 1  # Turn left to follow wall
        
        # Filter valid ranges
        valid_wall_ranges = wall_ranges[(wall_ranges >= self.last_scan.range_min) & 
                                       (wall_ranges <= self.last_scan.range_max)]
        
        if len(valid_wall_ranges) == 0:
            # No wall detected, search for wall
            twist.angular.z = turn_direction * self.default_angular_speed
            return twist
        
        wall_distance = np.mean(valid_wall_ranges)
        
        # Wall following logic
        if not self.obstacle_info.front_clear:
            # Obstacle in front, turn away from wall
            twist.angular.z = -turn_direction * self.default_angular_speed
        elif wall_distance > self.wall_follow_distance * 1.5:
            # Too far from wall, turn towards it
            twist.linear.x = self.default_linear_speed * 0.7
            twist.angular.z = turn_direction * self.default_angular_speed * 0.5
        elif wall_distance < self.wall_follow_distance * 0.7:
            # Too close to wall, turn away
            twist.linear.x = self.default_linear_speed * 0.5
            twist.angular.z = -turn_direction * self.default_angular_speed * 0.5
        else:
            # Good distance, move forward
            twist.linear.x = self.default_linear_speed
        
        return twist
    
    def generate_random_walk_movement(self) -> Twist:
        """Generate random walk movement with obstacle avoidance"""
        twist = Twist()
        
        current_time = time.time()
        
        # Change direction periodically
        if current_time - self.random_walk_change_time > np.random.uniform(3, 8):
            self.random_walk_direction = np.random.uniform(0, 2 * math.pi)
            self.random_walk_change_time = current_time
        
        # Check for obstacles
        if not self.obstacle_info.front_clear:
            # Obstacle avoidance
            if self.obstacle_info.right_clear and self.obstacle_info.left_clear:
                # Both sides clear, choose randomly
                turn_direction = np.random.choice([-1, 1])
            elif self.obstacle_info.right_clear:
                turn_direction = -1  # Turn right
            elif self.obstacle_info.left_clear:
                turn_direction = 1   # Turn left
            else:
                # Both sides blocked, reverse and turn
                twist.linear.x = -self.default_linear_speed * 0.3
                twist.angular.z = np.random.choice([-1, 1]) * self.default_angular_speed
                return twist
            
            twist.angular.z = turn_direction * self.default_angular_speed
            # Update random direction after obstacle avoidance
            self.random_walk_direction = np.random.uniform(0, 2 * math.pi)
            self.random_walk_change_time = current_time
        else:
            # No obstacles, move in random direction
            twist.linear.x = self.default_linear_speed
            
            # Add some angular velocity for more interesting movement
            x, y, yaw = self.get_robot_position()
            if yaw is not None:
                angle_diff = self.random_walk_direction - yaw
                # Normalize angle
                while angle_diff > math.pi:
                    angle_diff -= 2 * math.pi
                while angle_diff < -math.pi:
                    angle_diff += 2 * math.pi
                
                twist.angular.z = angle_diff * 0.5  # Gentle steering
        
        return twist
    
    def check_stuck_condition(self):
        """Check if robot is stuck and take corrective action"""
        if not self.movement_active:
            return
        
        x, y, _ = self.get_robot_position()
        if x is None:
            return
        
        # Add current position to history
        current_time = time.time()
        self.position_history.append((x, y, current_time))
        
        # Keep only recent history (last 10 seconds)
        self.position_history = [(px, py, t) for px, py, t in self.position_history 
                                if current_time - t < 10.0]
        
        # Check if robot has moved significantly
        if len(self.position_history) > 5:
            oldest_pos = self.position_history[0]
            distance_moved = math.sqrt((x - oldest_pos[0])**2 + (y - oldest_pos[1])**2)
            time_elapsed = current_time - oldest_pos[2]
            
            if distance_moved < 0.5 and time_elapsed > self.stuck_detection_threshold:
                self.get_logger().warn("🚨 Robot appears stuck, switching to random walk")
                self.set_movement_pattern(MovementPattern.RANDOM_WALK)
                self.position_history.clear()
    
    def publish_status(self):
        """Publish current status"""
        status = RobotState()
        status.header.stamp = self.get_clock().now().to_msg()
        status.header.frame_id = self.base_frame
        
        # Fill status information
        if self.movement_active:
            status.current_state = RobotState.AUTONOMOUS
        else:
            status.current_state = RobotState.IDLE
        
        status.previous_state = RobotState.UNKNOWN
        status.state_change_time = self.get_clock().now().to_msg()
        
        # System health
        status.hardware_ok = True
        status.software_ok = True
        status.communication_ok = True
        status.sensors_ok = self.last_scan is not None
        
        # Capabilities
        status.can_move = not self.emergency_stop
        status.can_navigate = self.movement_active
        status.can_perceive = self.last_scan is not None
        
        # Error information
        if self.emergency_stop:
            status.active_errors = ["Emergency stop active due to obstacle"]
        else:
            status.active_errors = []
        
        status.warnings = []
        
        # Performance metrics (placeholder values)
        status.cpu_usage = 0.0
        status.memory_usage = 0.0
        status.network_usage = 0.0
        
        self.status_publisher.publish(status)
        
        # Publish obstacle information
        if self.obstacle_info:
            obstacle_msg = String()
            obstacle_msg.data = (f"min_dist:{self.obstacle_info.min_distance:.2f},"
                               f"front:{self.obstacle_info.front_clear},"
                               f"left:{self.obstacle_info.left_clear},"
                               f"right:{self.obstacle_info.right_clear}")
            self.obstacle_publisher.publish(obstacle_msg)


def main(args=None):
    rclpy.init(args=args)
    
    controller = AutonomousMovementController()
    
    # Use MultiThreadedExecutor for concurrent operations
    executor = MultiThreadedExecutor()
    executor.add_node(controller)
    
    try:
        controller.get_logger().info("Starting autonomous movement controller...")
        executor.spin()
    except KeyboardInterrupt:
        controller.get_logger().info("Autonomous movement controller interrupted by user")
    finally:
        controller.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()