#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool, String
from sensor_msgs.msg import LaserScan
from robot_interfaces.msg import SafetyStatus, EmergencyStop
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import yaml
import os


class SafetyLevel(Enum):
    """Safety levels for different conditions"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class SafetyCondition:
    """Represents a safety condition being monitored"""
    name: str
    level: SafetyLevel
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    active: bool = True


@dataclass
class SafetyLimits:
    """Safety limits configuration"""
    max_linear_velocity: float = 0.5  # m/s
    max_angular_velocity: float = 1.0  # rad/s
    obstacle_stop_distance: float = 0.3  # meters
    obstacle_slow_distance: float = 0.6  # meters
    command_timeout: float = 1.0  # seconds
    emergency_stop_timeout: float = 0.5  # seconds
    min_scan_points: int = 10  # minimum valid laser scan points


class SafetySupervisor(Node):
    """
    Safety supervisor that coordinates emergency stops, monitors safety conditions,
    and enforces velocity limits across all robot components.
    """
    
    def __init__(self):
        super().__init__('safety_supervisor')
        
        # Initialize safety state
        self.emergency_stop_active = False
        self.safety_conditions: Dict[str, SafetyCondition] = {}
        self.last_command_time = datetime.now()
        self.last_scan_time = datetime.now()
        self.safety_limits = SafetyLimits()
        
        # Thread safety
        self.safety_lock = threading.RLock()
        
        # Load configuration
        self._load_safety_config()
        
        # QoS profiles
        reliable_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1
        )
        
        # Publishers
        self.emergency_stop_pub = self.create_publisher(
            EmergencyStop, '/emergency_stop', reliable_qos)
        self.safety_status_pub = self.create_publisher(
            SafetyStatus, '/safety_status', 10)
        self.filtered_cmd_vel_pub = self.create_publisher(
            Twist, '/cmd_vel_filtered', 10)
        
        # Subscribers
        self.cmd_vel_sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.laser_scan_sub = self.create_subscription(
            LaserScan, '/scan', self.laser_scan_callback, 10)
        self.emergency_stop_trigger_sub = self.create_subscription(
            Bool, '/emergency_stop_trigger', self.emergency_stop_trigger_callback, reliable_qos)
        self.safety_reset_sub = self.create_subscription(
            Bool, '/safety_reset', self.safety_reset_callback, reliable_qos)
        
        # Services for external safety condition registration
        self.external_safety_callbacks: Dict[str, Callable] = {}
        
        # Timers
        self.safety_monitor_timer = self.create_timer(0.1, self.safety_monitor_callback)
        self.status_publish_timer = self.create_timer(0.5, self.publish_safety_status)
        
        self.get_logger().info("Safety Supervisor initialized")
        
    def _load_safety_config(self):
        """Load safety configuration from robot config file"""
        try:
            config_path = os.path.join(
                os.path.dirname(__file__), '..', '..', '..', '..', 'config', 'robot_config.yaml'
            )
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    
                safety_config = config.get('robot', {}).get('safety', {})
                
                # Update safety limits from config
                self.safety_limits.max_linear_velocity = safety_config.get(
                    'max_linear_velocity', self.safety_limits.max_linear_velocity)
                self.safety_limits.max_angular_velocity = safety_config.get(
                    'max_angular_velocity', self.safety_limits.max_angular_velocity)
                self.safety_limits.obstacle_stop_distance = safety_config.get(
                    'obstacle_stop_distance', self.safety_limits.obstacle_stop_distance)
                self.safety_limits.obstacle_slow_distance = safety_config.get(
                    'obstacle_slow_distance', self.safety_limits.obstacle_slow_distance)
                self.safety_limits.command_timeout = safety_config.get(
                    'command_timeout', self.safety_limits.command_timeout)
                self.safety_limits.emergency_stop_timeout = safety_config.get(
                    'emergency_stop_timeout', self.safety_limits.emergency_stop_timeout)
                
                self.get_logger().info(f"Loaded safety configuration: {self.safety_limits}")
            else:
                self.get_logger().warn(f"Safety config file not found at {config_path}, using defaults")
                
        except Exception as e:
            self.get_logger().error(f"Failed to load safety config: {e}")
    
    def trigger_emergency_stop(self, reason: str, source: str = "unknown") -> None:
        """
        Trigger emergency stop with specified reason
        
        Args:
            reason: Human-readable reason for emergency stop
            source: Component that triggered the stop
        """
        with self.safety_lock:
            if not self.emergency_stop_active:
                self.emergency_stop_active = True
                
                # Add safety condition
                condition = SafetyCondition(
                    name=f"emergency_stop_{source}",
                    level=SafetyLevel.EMERGENCY,
                    message=f"Emergency stop triggered by {source}: {reason}"
                )
                self.safety_conditions[condition.name] = condition
                
                # Publish emergency stop message
                emergency_msg = EmergencyStop()
                emergency_msg.active = True
                emergency_msg.reason = reason
                emergency_msg.source = source
                emergency_msg.timestamp = self.get_clock().now().to_msg()
                self.emergency_stop_pub.publish(emergency_msg)
                
                self.get_logger().error(f"EMERGENCY STOP ACTIVATED: {reason} (source: {source})")
    
    def clear_emergency_stop(self, operator_confirmation: bool = False) -> bool:
        """
        Clear emergency stop if conditions are safe
        
        Args:
            operator_confirmation: Whether operator has confirmed it's safe to resume
            
        Returns:
            True if emergency stop was cleared, False otherwise
        """
        with self.safety_lock:
            if not self.emergency_stop_active:
                return True
                
            # Check if it's safe to clear emergency stop
            if not operator_confirmation:
                self.get_logger().warn("Emergency stop clear attempted without operator confirmation")
                return False
                
            # Check for active critical safety conditions
            critical_conditions = [
                cond for cond in self.safety_conditions.values()
                if cond.active and cond.level in [SafetyLevel.CRITICAL, SafetyLevel.EMERGENCY]
            ]
            
            if critical_conditions:
                self.get_logger().warn(
                    f"Cannot clear emergency stop: {len(critical_conditions)} critical conditions active")
                return False
            
            # Clear emergency stop
            self.emergency_stop_active = False
            
            # Remove emergency stop conditions
            self.safety_conditions = {
                name: cond for name, cond in self.safety_conditions.items()
                if not (cond.level == SafetyLevel.EMERGENCY and "emergency_stop" in name)
            }
            
            # Publish emergency stop cleared message
            emergency_msg = EmergencyStop()
            emergency_msg.active = False
            emergency_msg.reason = "Emergency stop cleared by operator"
            emergency_msg.source = "safety_supervisor"
            emergency_msg.timestamp = self.get_clock().now().to_msg()
            self.emergency_stop_pub.publish(emergency_msg)
            
            self.get_logger().info("Emergency stop cleared")
            return True
    
    def enforce_velocity_limits(self, cmd: Twist) -> Twist:
        """
        Enforce velocity limits and safety constraints on command
        
        Args:
            cmd: Input velocity command
            
        Returns:
            Filtered velocity command
        """
        filtered_cmd = Twist()
        
        with self.safety_lock:
            # If emergency stop is active, zero all commands
            if self.emergency_stop_active:
                return filtered_cmd
            
            # Apply velocity limits
            filtered_cmd.linear.x = max(
                -self.safety_limits.max_linear_velocity,
                min(self.safety_limits.max_linear_velocity, cmd.linear.x)
            )
            filtered_cmd.angular.z = max(
                -self.safety_limits.max_angular_velocity,
                min(self.safety_limits.max_angular_velocity, cmd.angular.z)
            )
            
            # Apply obstacle-based velocity reduction
            obstacle_factor = self._get_obstacle_velocity_factor()
            filtered_cmd.linear.x *= obstacle_factor
            filtered_cmd.angular.z *= obstacle_factor
            
            return filtered_cmd
    
    def _get_obstacle_velocity_factor(self) -> float:
        """
        Calculate velocity reduction factor based on obstacle proximity
        
        Returns:
            Factor between 0.0 and 1.0 to multiply velocity
        """
        # Check for obstacle-related safety conditions
        obstacle_conditions = [
            cond for cond in self.safety_conditions.values()
            if cond.active and "obstacle" in cond.name.lower()
        ]
        
        if not obstacle_conditions:
            return 1.0
        
        # Find the most restrictive condition
        min_factor = 1.0
        for condition in obstacle_conditions:
            if condition.level == SafetyLevel.CRITICAL:
                return 0.0  # Stop completely
            elif condition.level == SafetyLevel.WARNING:
                min_factor = min(min_factor, 0.3)  # Reduce to 30%
        
        return min_factor
    
    def check_safety_conditions(self) -> Dict[str, SafetyCondition]:
        """
        Check all safety conditions and return current status
        
        Returns:
            Dictionary of active safety conditions
        """
        with self.safety_lock:
            current_time = datetime.now()
            
            # Check command timeout
            time_since_command = (current_time - self.last_command_time).total_seconds()
            if time_since_command > self.safety_limits.command_timeout:
                condition = SafetyCondition(
                    name="command_timeout",
                    level=SafetyLevel.WARNING,
                    message=f"No command received for {time_since_command:.1f}s"
                )
                self.safety_conditions["command_timeout"] = condition
            else:
                # Remove timeout condition if commands are being received
                self.safety_conditions.pop("command_timeout", None)
            
            # Check laser scan timeout
            time_since_scan = (current_time - self.last_scan_time).total_seconds()
            if time_since_scan > 2.0:  # 2 second timeout for laser data
                condition = SafetyCondition(
                    name="laser_timeout",
                    level=SafetyLevel.WARNING,
                    message=f"No laser data for {time_since_scan:.1f}s"
                )
                self.safety_conditions["laser_timeout"] = condition
            else:
                self.safety_conditions.pop("laser_timeout", None)
            
            return dict(self.safety_conditions)
    
    def register_external_safety_callback(self, name: str, callback: Callable) -> None:
        """
        Register external safety condition callback
        
        Args:
            name: Name of the safety check
            callback: Function that returns SafetyCondition or None
        """
        self.external_safety_callbacks[name] = callback
        self.get_logger().info(f"Registered external safety callback: {name}")
    
    def cmd_vel_callback(self, msg: Twist) -> None:
        """Handle incoming velocity commands"""
        self.last_command_time = datetime.now()
        
        # Filter and enforce limits
        filtered_cmd = self.enforce_velocity_limits(msg)
        
        # Publish filtered command
        self.filtered_cmd_vel_pub.publish(filtered_cmd)
    
    def laser_scan_callback(self, msg: LaserScan) -> None:
        """Handle laser scan data for obstacle detection"""
        self.last_scan_time = datetime.now()
        
        try:
            # Check for valid scan data
            valid_ranges = [r for r in msg.ranges if msg.range_min <= r <= msg.range_max]
            
            if len(valid_ranges) < self.safety_limits.min_scan_points:
                condition = SafetyCondition(
                    name="laser_quality",
                    level=SafetyLevel.WARNING,
                    message=f"Poor laser data quality: {len(valid_ranges)} valid points"
                )
                self.safety_conditions["laser_quality"] = condition
            else:
                self.safety_conditions.pop("laser_quality", None)
            
            # Check for obstacles
            min_distance = min(valid_ranges) if valid_ranges else float('inf')
            
            if min_distance < self.safety_limits.obstacle_stop_distance:
                condition = SafetyCondition(
                    name="obstacle_critical",
                    level=SafetyLevel.CRITICAL,
                    message=f"Obstacle at {min_distance:.2f}m (stop threshold: {self.safety_limits.obstacle_stop_distance:.2f}m)"
                )
                self.safety_conditions["obstacle_critical"] = condition
                self.safety_conditions.pop("obstacle_warning", None)
                
            elif min_distance < self.safety_limits.obstacle_slow_distance:
                condition = SafetyCondition(
                    name="obstacle_warning",
                    level=SafetyLevel.WARNING,
                    message=f"Obstacle at {min_distance:.2f}m (slow threshold: {self.safety_limits.obstacle_slow_distance:.2f}m)"
                )
                self.safety_conditions["obstacle_warning"] = condition
                self.safety_conditions.pop("obstacle_critical", None)
                
            else:
                # Clear obstacle conditions
                self.safety_conditions.pop("obstacle_critical", None)
                self.safety_conditions.pop("obstacle_warning", None)
                
        except Exception as e:
            self.get_logger().error(f"Error processing laser scan: {e}")
    
    def emergency_stop_trigger_callback(self, msg: Bool) -> None:
        """Handle external emergency stop triggers"""
        if msg.data:
            self.trigger_emergency_stop("External trigger", "external_system")
    
    def safety_reset_callback(self, msg: Bool) -> None:
        """Handle safety reset requests"""
        if msg.data:
            success = self.clear_emergency_stop(operator_confirmation=True)
            if success:
                self.get_logger().info("Safety system reset by operator")
            else:
                self.get_logger().warn("Safety reset failed - conditions not safe")
    
    def safety_monitor_callback(self) -> None:
        """Periodic safety monitoring"""
        try:
            # Update safety conditions
            self.check_safety_conditions()
            
            # Run external safety callbacks
            for name, callback in self.external_safety_callbacks.items():
                try:
                    result = callback()
                    if result:
                        self.safety_conditions[name] = result
                    else:
                        self.safety_conditions.pop(name, None)
                except Exception as e:
                    self.get_logger().error(f"Error in external safety callback {name}: {e}")
            
            # Check for conditions that should trigger emergency stop
            with self.safety_lock:
                critical_conditions = [
                    cond for cond in self.safety_conditions.values()
                    if cond.active and cond.level == SafetyLevel.CRITICAL
                ]
                
                if critical_conditions and not self.emergency_stop_active:
                    reasons = [cond.message for cond in critical_conditions]
                    self.trigger_emergency_stop(
                        f"Critical safety conditions: {'; '.join(reasons)}",
                        "safety_monitor"
                    )
                    
        except Exception as e:
            self.get_logger().error(f"Error in safety monitor: {e}")
    
    def publish_safety_status(self) -> None:
        """Publish current safety status"""
        try:
            status_msg = SafetyStatus()
            status_msg.timestamp = self.get_clock().now().to_msg()
            status_msg.emergency_stop_active = self.emergency_stop_active
            
            with self.safety_lock:
                # Count conditions by level
                conditions_by_level = {}
                for condition in self.safety_conditions.values():
                    if condition.active:
                        level = condition.level.value
                        if level not in conditions_by_level:
                            conditions_by_level[level] = []
                        conditions_by_level[level].append(condition.message)
                
                status_msg.warning_conditions = conditions_by_level.get('warning', [])
                status_msg.critical_conditions = conditions_by_level.get('critical', [])
                status_msg.emergency_conditions = conditions_by_level.get('emergency', [])
                
                # Overall safety level
                if conditions_by_level.get('emergency'):
                    status_msg.overall_safety_level = 'emergency'
                elif conditions_by_level.get('critical'):
                    status_msg.overall_safety_level = 'critical'
                elif conditions_by_level.get('warning'):
                    status_msg.overall_safety_level = 'warning'
                else:
                    status_msg.overall_safety_level = 'normal'
            
            self.safety_status_pub.publish(status_msg)
            
        except Exception as e:
            self.get_logger().error(f"Error publishing safety status: {e}")


def main(args=None):
    rclpy.init(args=args)
    
    try:
        safety_supervisor = SafetySupervisor()
        rclpy.spin(safety_supervisor)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error in safety supervisor: {e}")
    finally:
        if 'safety_supervisor' in locals():
            safety_supervisor.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()