#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool, String
from sensor_msgs.msg import LaserScan
from robot_interfaces.msg import EmergencyStop, SafetyStatus
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import yaml
import os
import math


class VelocityLimitMode(Enum):
    """Velocity limiting modes"""
    NORMAL = "normal"
    REDUCED = "reduced"
    EMERGENCY = "emergency"
    STOPPED = "stopped"


@dataclass
class VelocityLimits:
    """Velocity limits configuration"""
    max_linear: float = 0.5  # m/s
    max_angular: float = 1.0  # rad/s
    max_acceleration: float = 1.0  # m/s²
    max_deceleration: float = 2.0  # m/s²
    max_angular_acceleration: float = 2.0  # rad/s²


@dataclass
class CommandTimeout:
    """Command timeout tracking"""
    timeout_duration: float = 1.0  # seconds
    last_command_time: datetime = None
    timeout_active: bool = False


class VelocityLimiter(Node):
    """
    Velocity limiter that enforces safety constraints on robot motion commands.
    Provides command filtering, timeout detection, and adaptive velocity limiting.
    """
    
    def __init__(self):
        super().__init__('velocity_limiter')
        
        # Velocity limiting state
        self.current_mode = VelocityLimitMode.NORMAL
        self.velocity_limits = VelocityLimits()
        self.command_timeout = CommandTimeout()
        
        # Current velocity tracking for acceleration limiting
        self.current_linear_vel = 0.0
        self.current_angular_vel = 0.0
        self.last_update_time = datetime.now()
        
        # Emergency stop state
        self.emergency_stop_active = False
        
        # Obstacle-based velocity scaling
        self.obstacle_velocity_factor = 1.0
        self.min_obstacle_distance = float('inf')
        
        # Thread safety
        self.velocity_lock = threading.RLock()
        
        # Load configuration
        self._load_velocity_config()
        
        # QoS profiles
        reliable_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1
        )
        
        # Publishers
        self.cmd_vel_limited_pub = self.create_publisher(
            Twist, '/cmd_vel_limited', 10)
        self.velocity_status_pub = self.create_publisher(
            String, '/velocity_limiter_status', 10)
        
        # Subscribers
        self.cmd_vel_sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.emergency_stop_sub = self.create_subscription(
            EmergencyStop, '/emergency_stop', self.emergency_stop_callback, reliable_qos)
        self.safety_status_sub = self.create_subscription(
            SafetyStatus, '/safety_status', self.safety_status_callback, 10)
        self.laser_scan_sub = self.create_subscription(
            LaserScan, '/scan', self.laser_scan_callback, 10)
        self.velocity_mode_sub = self.create_subscription(
            String, '/velocity_limit_mode', self.velocity_mode_callback, 10)
        
        # Timers
        self.timeout_check_timer = self.create_timer(0.1, self.check_command_timeout)
        self.status_publish_timer = self.create_timer(1.0, self.publish_status)
        
        self.get_logger().info("Velocity Limiter initialized")
    
    def _load_velocity_config(self):
        """Load velocity limiting configuration"""
        try:
            config_path = os.path.join(
                os.path.dirname(__file__), '..', '..', '..', '..', 'config', 'robot_config.yaml'
            )
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    
                # Load physical parameters
                physical_params = config.get('robot', {}).get('physical_parameters', {})
                self.velocity_limits.max_linear = physical_params.get(
                    'max_linear_velocity', self.velocity_limits.max_linear)
                self.velocity_limits.max_angular = physical_params.get(
                    'max_angular_velocity', self.velocity_limits.max_angular)
                
                # Load safety parameters
                safety_params = config.get('robot', {}).get('safety', {})
                self.command_timeout.timeout_duration = safety_params.get(
                    'command_timeout', self.command_timeout.timeout_duration)
                
                # Load acceleration limits if available
                self.velocity_limits.max_acceleration = safety_params.get(
                    'max_acceleration', self.velocity_limits.max_acceleration)
                self.velocity_limits.max_deceleration = safety_params.get(
                    'max_deceleration', self.velocity_limits.max_deceleration)
                self.velocity_limits.max_angular_acceleration = safety_params.get(
                    'max_angular_acceleration', self.velocity_limits.max_angular_acceleration)
                
                self.get_logger().info(f"Loaded velocity limits: {self.velocity_limits}")
            else:
                self.get_logger().warn("Velocity config not found, using defaults")
                
        except Exception as e:
            self.get_logger().error(f"Failed to load velocity config: {e}")
    
    def set_velocity_limit_mode(self, mode: VelocityLimitMode) -> None:
        """
        Set the velocity limiting mode
        
        Args:
            mode: New velocity limiting mode
        """
        with self.velocity_lock:
            if self.current_mode != mode:
                old_mode = self.current_mode
                self.current_mode = mode
                self.get_logger().info(f"Velocity limit mode changed: {old_mode.value} -> {mode.value}")
    
    def apply_velocity_limits(self, cmd: Twist) -> Twist:
        """
        Apply velocity limits and safety constraints to command
        
        Args:
            cmd: Input velocity command
            
        Returns:
            Limited velocity command
        """
        limited_cmd = Twist()
        
        with self.velocity_lock:
            current_time = datetime.now()
            dt = (current_time - self.last_update_time).total_seconds()
            dt = max(dt, 0.001)  # Prevent division by zero
            
            # Get mode-specific limits
            linear_limit, angular_limit = self._get_mode_limits()
            
            # Apply basic velocity limits
            target_linear = max(-linear_limit, min(linear_limit, cmd.linear.x))
            target_angular = max(-angular_limit, min(angular_limit, cmd.angular.z))
            
            # Apply obstacle-based velocity scaling
            target_linear *= self.obstacle_velocity_factor
            target_angular *= self.obstacle_velocity_factor
            
            # Apply acceleration limits
            limited_cmd.linear.x = self._apply_acceleration_limit(
                self.current_linear_vel, target_linear, dt, 
                self.velocity_limits.max_acceleration, self.velocity_limits.max_deceleration)
            
            limited_cmd.angular.z = self._apply_acceleration_limit(
                self.current_angular_vel, target_angular, dt,
                self.velocity_limits.max_angular_acceleration, self.velocity_limits.max_angular_acceleration)
            
            # Update current velocity tracking
            self.current_linear_vel = limited_cmd.linear.x
            self.current_angular_vel = limited_cmd.angular.z
            self.last_update_time = current_time
            
            return limited_cmd
    
    def _get_mode_limits(self) -> Tuple[float, float]:
        """
        Get velocity limits based on current mode
        
        Returns:
            Tuple of (linear_limit, angular_limit)
        """
        if self.current_mode == VelocityLimitMode.EMERGENCY or self.emergency_stop_active:
            return 0.0, 0.0
        elif self.current_mode == VelocityLimitMode.STOPPED:
            return 0.0, 0.0
        elif self.current_mode == VelocityLimitMode.REDUCED:
            return (self.velocity_limits.max_linear * 0.3, 
                   self.velocity_limits.max_angular * 0.3)
        else:  # NORMAL mode
            return self.velocity_limits.max_linear, self.velocity_limits.max_angular
    
    def _apply_acceleration_limit(self, current_vel: float, target_vel: float, 
                                dt: float, max_accel: float, max_decel: float) -> float:
        """
        Apply acceleration limits to velocity change
        
        Args:
            current_vel: Current velocity
            target_vel: Desired target velocity
            dt: Time step
            max_accel: Maximum acceleration
            max_decel: Maximum deceleration
            
        Returns:
            Limited velocity
        """
        vel_diff = target_vel - current_vel
        
        if abs(vel_diff) < 0.001:  # No significant change
            return target_vel
        
        # Determine if accelerating or decelerating
        if (vel_diff > 0 and current_vel >= 0) or (vel_diff < 0 and current_vel <= 0):
            # Accelerating in same direction or starting from zero
            max_change = max_accel * dt
        else:
            # Decelerating or changing direction
            max_change = max_decel * dt
        
        # Limit the velocity change
        if abs(vel_diff) > max_change:
            return current_vel + math.copysign(max_change, vel_diff)
        else:
            return target_vel
    
    def update_obstacle_factor(self, min_distance: float) -> None:
        """
        Update velocity scaling factor based on obstacle distance
        
        Args:
            min_distance: Minimum distance to obstacles
        """
        with self.velocity_lock:
            self.min_obstacle_distance = min_distance
            
            # Define distance thresholds
            stop_distance = 0.3  # meters
            slow_distance = 0.6  # meters
            
            if min_distance < stop_distance:
                self.obstacle_velocity_factor = 0.0
            elif min_distance < slow_distance:
                # Linear scaling between stop and slow distances
                factor = (min_distance - stop_distance) / (slow_distance - stop_distance)
                self.obstacle_velocity_factor = max(0.1, min(1.0, factor))
            else:
                self.obstacle_velocity_factor = 1.0
    
    def cmd_vel_callback(self, msg: Twist) -> None:
        """Handle incoming velocity commands"""
        # Update command timeout tracking
        self.command_timeout.last_command_time = datetime.now()
        self.command_timeout.timeout_active = False
        
        # Apply velocity limits
        limited_cmd = self.apply_velocity_limits(msg)
        
        # Publish limited command
        self.cmd_vel_limited_pub.publish(limited_cmd)
        
        # Log significant velocity reductions
        if (abs(msg.linear.x - limited_cmd.linear.x) > 0.1 or 
            abs(msg.angular.z - limited_cmd.angular.z) > 0.1):
            self.get_logger().debug(
                f"Velocity limited: ({msg.linear.x:.2f}, {msg.angular.z:.2f}) -> "
                f"({limited_cmd.linear.x:.2f}, {limited_cmd.angular.z:.2f})")
    
    def emergency_stop_callback(self, msg: EmergencyStop) -> None:
        """Handle emergency stop messages"""
        with self.velocity_lock:
            self.emergency_stop_active = msg.active
            
            if msg.active:
                self.set_velocity_limit_mode(VelocityLimitMode.EMERGENCY)
                # Immediately publish zero velocity
                zero_cmd = Twist()
                self.cmd_vel_limited_pub.publish(zero_cmd)
                self.current_linear_vel = 0.0
                self.current_angular_vel = 0.0
            else:
                self.set_velocity_limit_mode(VelocityLimitMode.NORMAL)
    
    def safety_status_callback(self, msg: SafetyStatus) -> None:
        """Handle safety status updates"""
        with self.velocity_lock:
            # Adjust velocity mode based on safety level
            if msg.overall_safety_level == 'emergency':
                self.set_velocity_limit_mode(VelocityLimitMode.EMERGENCY)
            elif msg.overall_safety_level == 'critical':
                self.set_velocity_limit_mode(VelocityLimitMode.STOPPED)
            elif msg.overall_safety_level == 'warning':
                self.set_velocity_limit_mode(VelocityLimitMode.REDUCED)
            else:  # normal
                if not self.emergency_stop_active:
                    self.set_velocity_limit_mode(VelocityLimitMode.NORMAL)
    
    def laser_scan_callback(self, msg: LaserScan) -> None:
        """Handle laser scan data for obstacle-based velocity limiting"""
        try:
            # Filter valid ranges
            valid_ranges = [r for r in msg.ranges if msg.range_min <= r <= msg.range_max]
            
            if valid_ranges:
                min_distance = min(valid_ranges)
                self.update_obstacle_factor(min_distance)
            else:
                # No valid laser data - be conservative
                self.update_obstacle_factor(0.1)
                
        except Exception as e:
            self.get_logger().error(f"Error processing laser scan: {e}")
    
    def velocity_mode_callback(self, msg: String) -> None:
        """Handle velocity mode change requests"""
        try:
            mode = VelocityLimitMode(msg.data.lower())
            self.set_velocity_limit_mode(mode)
        except ValueError:
            self.get_logger().warn(f"Invalid velocity limit mode: {msg.data}")
    
    def check_command_timeout(self) -> None:
        """Check for command timeout and handle accordingly"""
        if self.command_timeout.last_command_time is None:
            return
        
        current_time = datetime.now()
        time_since_command = (current_time - self.command_timeout.last_command_time).total_seconds()
        
        if time_since_command > self.command_timeout.timeout_duration:
            if not self.command_timeout.timeout_active:
                self.command_timeout.timeout_active = True
                self.get_logger().warn(f"Command timeout detected ({time_since_command:.1f}s)")
                
                # Publish zero velocity on timeout
                zero_cmd = Twist()
                self.cmd_vel_limited_pub.publish(zero_cmd)
                
                with self.velocity_lock:
                    self.current_linear_vel = 0.0
                    self.current_angular_vel = 0.0
        else:
            self.command_timeout.timeout_active = False
    
    def publish_status(self) -> None:
        """Publish velocity limiter status"""
        try:
            status_msg = String()
            
            with self.velocity_lock:
                status_data = {
                    'mode': self.current_mode.value,
                    'emergency_stop_active': self.emergency_stop_active,
                    'command_timeout_active': self.command_timeout.timeout_active,
                    'obstacle_factor': self.obstacle_velocity_factor,
                    'min_obstacle_distance': self.min_obstacle_distance,
                    'current_linear_vel': self.current_linear_vel,
                    'current_angular_vel': self.current_angular_vel,
                    'limits': {
                        'max_linear': self.velocity_limits.max_linear,
                        'max_angular': self.velocity_limits.max_angular
                    }
                }
            
            status_msg.data = str(status_data)
            self.velocity_status_pub.publish(status_msg)
            
        except Exception as e:
            self.get_logger().error(f"Error publishing status: {e}")
    
    def get_current_status(self) -> Dict:
        """Get current velocity limiter status"""
        with self.velocity_lock:
            return {
                'mode': self.current_mode.value,
                'emergency_stop_active': self.emergency_stop_active,
                'command_timeout_active': self.command_timeout.timeout_active,
                'obstacle_velocity_factor': self.obstacle_velocity_factor,
                'min_obstacle_distance': self.min_obstacle_distance,
                'current_velocities': {
                    'linear': self.current_linear_vel,
                    'angular': self.current_angular_vel
                },
                'velocity_limits': {
                    'max_linear': self.velocity_limits.max_linear,
                    'max_angular': self.velocity_limits.max_angular,
                    'max_acceleration': self.velocity_limits.max_acceleration,
                    'max_deceleration': self.velocity_limits.max_deceleration
                }
            }


def main(args=None):
    rclpy.init(args=args)
    
    try:
        velocity_limiter = VelocityLimiter()
        rclpy.spin(velocity_limiter)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error in velocity limiter: {e}")
    finally:
        if 'velocity_limiter' in locals():
            velocity_limiter.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()