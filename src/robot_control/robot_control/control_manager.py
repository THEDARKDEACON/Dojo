#!/usr/bin/env python3
"""
High-level Control Manager for Dojo Robot
Coordinates between hardware interface and navigation/perception systems
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
import threading
import time
from enum import Enum
import math

from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import String, Bool
from sensor_msgs.msg import LaserScan, Image

# Import custom interfaces (will be available after building robot_interfaces)
# from robot_interfaces.msg import RobotState, MotorCommand, SensorData
# from robot_interfaces.srv import SetMode

class ControlMode(Enum):
    IDLE = 0
    MANUAL = 1
    AUTONOMOUS = 2
    EMERGENCY_STOP = 3

class ControlManager(Node):
    """High-level robot control coordination"""
    
    def __init__(self):
        super().__init__('control_manager')
        
        # Control state
        self.control_mode = ControlMode.MANUAL
        self.emergency_stop_active = False
        self.last_cmd_vel_time = time.time()
        
        # Safety parameters
        self.declare_parameter('cmd_vel_timeout', 1.0)
        self.declare_parameter('max_linear_velocity', 0.5)
        self.declare_parameter('max_angular_velocity', 1.0)
        self.declare_parameter('safety_stop_distance', 0.3)
        
        # Setup ROS interfaces
        self._setup_publishers()
        self._setup_subscribers()
        self._setup_services()
        
        # Start safety monitoring
        self._start_safety_monitoring()
        
        self.get_logger().info('Control Manager initialized')
    
    def _setup_publishers(self):
        """Setup ROS publishers"""
        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.control_status_pub = self.create_publisher(String, 'control_status', 10)
        self.emergency_stop_pub = self.create_publisher(Bool, 'emergency_stop', 10)
        
        # Status update timer
        self.status_timer = self.create_timer(0.5, self._publish_status)
    
    def _setup_subscribers(self):
        """Setup ROS subscribers"""
        # Command velocity inputs
        self.manual_cmd_sub = self.create_subscription(
            Twist, 'cmd_vel_manual', self._manual_cmd_callback, 10)
        
        self.auto_cmd_sub = self.create_subscription(
            Twist, 'cmd_vel_auto', self._auto_cmd_callback, 10)
        
        # Safety inputs
        self.scan_sub = self.create_subscription(
            LaserScan, 'scan', self._scan_callback, 10)
        
        self.hardware_status_sub = self.create_subscription(
            String, 'system_status', self._hardware_status_callback, 10)
        
        # Emergency stop input
        self.estop_sub = self.create_subscription(
            Bool, 'emergency_stop_request', self._estop_callback, 10)
    
    def _setup_services(self):
        """Setup ROS services"""
        # Mode switching service would go here
        # self.set_mode_srv = self.create_service(SetMode, 'set_control_mode', self._set_mode_callback)
        pass
    
    def _start_safety_monitoring(self):
        """Start safety monitoring thread"""
        self.safety_thread = threading.Thread(target=self._safety_monitor_loop)
        self.safety_thread.daemon = True
        self.safety_thread.start() 
   
    def _safety_monitor_loop(self):
        """Main safety monitoring loop"""
        while rclpy.ok():
            self._check_cmd_vel_timeout()
            self._check_emergency_conditions()
            time.sleep(0.1)
    
    def _check_cmd_vel_timeout(self):
        """Check for command velocity timeout"""
        timeout = self.get_parameter('cmd_vel_timeout').value
        if time.time() - self.last_cmd_vel_time > timeout:
            if self.control_mode != ControlMode.IDLE:
                self.get_logger().warn('Command velocity timeout - stopping robot')
                self._send_stop_command()
    
    def _check_emergency_conditions(self):
        """Check for emergency stop conditions"""
        # Additional safety checks would go here
        pass
    
    def _manual_cmd_callback(self, msg):
        """Handle manual control commands"""
        if self.control_mode == ControlMode.MANUAL and not self.emergency_stop_active:
            filtered_cmd = self._apply_safety_limits(msg)
            self.cmd_vel_pub.publish(filtered_cmd)
            self.last_cmd_vel_time = time.time()
    
    def _auto_cmd_callback(self, msg):
        """Handle autonomous control commands"""
        if self.control_mode == ControlMode.AUTONOMOUS and not self.emergency_stop_active:
            filtered_cmd = self._apply_safety_limits(msg)
            self.cmd_vel_pub.publish(filtered_cmd)
            self.last_cmd_vel_time = time.time()
    
    def _apply_safety_limits(self, cmd_vel):
        """Apply safety limits to command velocity"""
        max_linear = self.get_parameter('max_linear_velocity').value
        max_angular = self.get_parameter('max_angular_velocity').value
        
        # Limit velocities
        limited_cmd = Twist()
        limited_cmd.linear.x = max(-max_linear, min(max_linear, cmd_vel.linear.x))
        limited_cmd.angular.z = max(-max_angular, min(max_angular, cmd_vel.angular.z))
        
        return limited_cmd
    
    def _scan_callback(self, msg):
        """Handle laser scan for obstacle detection"""
        # Simple obstacle detection with robust filtering
        valid = [r for r in msg.ranges if math.isfinite(r) and (r > msg.range_min) and (r < msg.range_max)]
        if not valid:
            # No valid measurements; skip processing this cycle
            return
        min_distance = min(valid)
        safety_distance = self.get_parameter('safety_stop_distance').value
        
        if min_distance < safety_distance:
            self.get_logger().warn(f'Obstacle detected at {min_distance:.2f}m - emergency stop')
            self._trigger_emergency_stop()
    
    def _hardware_status_callback(self, msg):
        """Handle hardware status updates"""
        if msg.data == 'ERROR':
            self.get_logger().error('Hardware error detected - emergency stop')
            self._trigger_emergency_stop()
    
    def _estop_callback(self, msg):
        """Handle emergency stop requests"""
        if msg.data:
            self._trigger_emergency_stop()
        else:
            self._clear_emergency_stop()
    
    def _trigger_emergency_stop(self):
        """Activate emergency stop"""
        if not self.emergency_stop_active:
            self.emergency_stop_active = True
            self.control_mode = ControlMode.EMERGENCY_STOP
            self._send_stop_command()
            
            estop_msg = Bool()
            estop_msg.data = True
            self.emergency_stop_pub.publish(estop_msg)
            
            self.get_logger().error('EMERGENCY STOP ACTIVATED')
    
    def _clear_emergency_stop(self):
        """Clear emergency stop"""
        if self.emergency_stop_active:
            self.emergency_stop_active = False
            self.control_mode = ControlMode.IDLE
            
            estop_msg = Bool()
            estop_msg.data = False
            self.emergency_stop_pub.publish(estop_msg)
            
            self.get_logger().info('Emergency stop cleared')
    
    def _send_stop_command(self):
        """Send stop command to robot"""
        stop_cmd = Twist()
        self.cmd_vel_pub.publish(stop_cmd)
    
    def _publish_status(self):
        """Publish control status"""
        status_msg = String()
        status_msg.data = f"{self.control_mode.name}{'_ESTOP' if self.emergency_stop_active else ''}"
        self.control_status_pub.publish(status_msg)
    
    def set_control_mode(self, mode):
        """Set control mode"""
        if not self.emergency_stop_active:
            self.control_mode = mode
            self.get_logger().info(f'Control mode set to: {mode.name}')
            return True
        return False

def main(args=None):
    rclpy.init(args=args)
    
    try:
        control_manager = ControlManager()
        rclpy.spin(control_manager)
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()