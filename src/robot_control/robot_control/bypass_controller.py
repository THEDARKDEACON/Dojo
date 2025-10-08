#!/usr/bin/env python3
"""
Arduino Integration Bypass Controller

This module provides a bypass mode for the Dojo robot system that allows direct
Arduino communication without safety system interference, similar to the robosync system.
"""

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
import time
import json
from typing import Optional, Dict, Any

# ROS2 message types
from std_msgs.msg import String, Bool
from geometry_msgs.msg import Twist
from std_srvs.srv import SetBool
from robot_interfaces.msg import EmergencyStop


class BypassController(Node):
    """
    Main controller for Arduino Integration Bypass Mode.
    
    This controller manages the bypass mode state, handles mode switching,
    and coordinates direct Arduino communication while maintaining essential
    safety features like emergency stop.
    """
    
    def __init__(self):
        super().__init__('bypass_controller')
        
        # Declare parameters for bypass controller configuration
        self.declare_parameter('bypass_mode_enabled', False)
        self.declare_parameter('debug_logging', True)
        self.declare_parameter('status_publish_rate', 1.0)  # Hz
        self.declare_parameter('cmd_vel_timeout', 2.0)  # seconds
        self.declare_parameter('emergency_stop_timeout', 5.0)  # seconds
        
        # Get parameters
        self.bypass_mode_enabled = self.get_parameter('bypass_mode_enabled').value
        self.debug_logging = self.get_parameter('debug_logging').value
        self.status_publish_rate = self.get_parameter('status_publish_rate').value
        self.cmd_vel_timeout = self.get_parameter('cmd_vel_timeout').value
        self.emergency_stop_timeout = self.get_parameter('emergency_stop_timeout').value
        
        # Mode state variables
        self.bypass_active = self.bypass_mode_enabled
        self.emergency_stop_active = False
        self.last_cmd_vel_time = None
        self.last_emergency_stop_time = None
        self.mode_switch_in_progress = False
        
        # Status tracking
        self.arduino_connected = False
        self.safety_systems_disabled = False
        self.error_message = ""
        self.initialization_complete = False
        
        # Statistics for monitoring
        self.cmd_vel_count = 0
        self.mode_switches = 0
        self.emergency_stops = 0
        
        # Initialize ROS2 interfaces
        self._setup_publishers()
        self._setup_subscribers()
        self._setup_services()
        self._setup_timers()
        
        # Log initialization
        self.get_logger().info(f'Bypass Controller initialized - Mode: {"BYPASS" if self.bypass_active else "NORMAL"}')
        if self.debug_logging:
            self.get_logger().info(f'Debug logging enabled - Status rate: {self.status_publish_rate}Hz')
        
        # Mark initialization as complete
        self.initialization_complete = True
        
        # Publish initial status
        self._publish_status()
    
    def _setup_publishers(self):
        """Set up ROS2 publishers for bypass controller."""
        # QoS profile for status messages - reliable delivery
        status_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1
        )
        
        # Bypass status publisher for system monitoring
        self.bypass_status_pub = self.create_publisher(
            String,
            '/bypass_status',
            status_qos
        )
        
        # Debug publisher for detailed information
        if self.debug_logging:
            self.debug_pub = self.create_publisher(
                String,
                '/bypass_debug',
                10
            )
        
        self.get_logger().info('Publishers initialized')
    
    def _setup_subscribers(self):
        """Set up ROS2 subscribers for bypass controller."""
        # Subscribe to cmd_vel for velocity commands
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10
        )
        
        # Subscribe to emergency stop for safety override
        self.emergency_stop_sub = self.create_subscription(
            EmergencyStop,
            '/emergency_stop',
            self.emergency_stop_callback,
            10
        )
        
        self.get_logger().info('Subscribers initialized')
    
    def _setup_services(self):
        """Set up ROS2 services for bypass controller."""
        # Service for mode switching
        self.set_bypass_mode_srv = self.create_service(
            SetBool,
            '/set_bypass_mode',
            self.set_bypass_mode_callback
        )
        
        self.get_logger().info('Services initialized')
    
    def _setup_timers(self):
        """Set up timers for periodic operations."""
        # Status publishing timer
        status_period = 1.0 / self.status_publish_rate
        self.status_timer = self.create_timer(
            status_period,
            self._publish_status
        )
        
        # Timeout monitoring timer (check every second)
        self.timeout_timer = self.create_timer(
            1.0,
            self._check_timeouts
        )
        
        self.get_logger().info('Timers initialized')
    
    def cmd_vel_callback(self, msg: Twist):
        """
        Handle incoming cmd_vel messages.
        
        Args:
            msg: Twist message containing velocity commands
        """
        # Update statistics
        self.cmd_vel_count += 1
        self.last_cmd_vel_time = self.get_clock().now()
        
        # Check if emergency stop is active
        if self.emergency_stop_active:
            if self.debug_logging:
                self._publish_debug("cmd_vel ignored - emergency stop active")
            return
        
        # Process command based on current mode
        if self.bypass_active:
            self._process_bypass_cmd_vel(msg)
        else:
            self._process_normal_cmd_vel(msg)
        
        if self.debug_logging:
            self._publish_debug(f"cmd_vel processed - linear: {msg.linear.x:.3f}, angular: {msg.angular.z:.3f}")
    
    def _process_bypass_cmd_vel(self, msg: Twist):
        """
        Process cmd_vel in bypass mode.
        
        Args:
            msg: Twist message to process
        """
        # In bypass mode, we'll forward directly to Arduino driver
        # This will be implemented when DirectArduinoDriver is created
        if self.debug_logging:
            self._publish_debug(f"Bypass mode cmd_vel: linear={msg.linear.x:.3f}, angular={msg.angular.z:.3f}")
    
    def _process_normal_cmd_vel(self, msg: Twist):
        """
        Process cmd_vel in normal mode.
        
        Args:
            msg: Twist message to process
        """
        # In normal mode, commands go through safety systems
        # This maintains compatibility with existing system
        if self.debug_logging:
            self._publish_debug(f"Normal mode cmd_vel: linear={msg.linear.x:.3f}, angular={msg.angular.z:.3f}")
    
    def emergency_stop_callback(self, msg: EmergencyStop):
        """
        Handle emergency stop messages.
        
        Args:
            msg: EmergencyStop message
        """
        previous_state = self.emergency_stop_active
        self.emergency_stop_active = msg.active
        self.last_emergency_stop_time = self.get_clock().now()
        
        if msg.active and not previous_state:
            # Emergency stop activated
            self.emergency_stops += 1
            self.get_logger().warn(f"Emergency stop activated: {msg.reason}")
            
            # Immediately stop any motion commands
            self._execute_emergency_stop()
            
        elif not msg.active and previous_state:
            # Emergency stop cleared
            self.get_logger().info("Emergency stop cleared")
            self._clear_emergency_stop()
        
        # Publish updated status
        self._publish_status()
    
    def _execute_emergency_stop(self):
        """Execute emergency stop procedures."""
        # This will send stop commands to Arduino when DirectArduinoDriver is implemented
        if self.debug_logging:
            self._publish_debug("Emergency stop executed - all motion stopped")
    
    def _clear_emergency_stop(self):
        """Clear emergency stop and resume normal operation."""
        if self.debug_logging:
            self._publish_debug("Emergency stop cleared - ready for commands")
    
    def set_bypass_mode_callback(self, request: SetBool.Request, response: SetBool.Response):
        """
        Handle bypass mode switching service calls.
        
        Args:
            request: Service request with desired bypass mode state
            response: Service response to populate
            
        Returns:
            Service response with success status and message
        """
        if self.mode_switch_in_progress:
            response.success = False
            response.message = "Mode switch already in progress"
            return response
        
        desired_mode = request.data
        current_mode = self.bypass_active
        
        if desired_mode == current_mode:
            response.success = True
            response.message = f"Already in {'bypass' if desired_mode else 'normal'} mode"
            return response
        
        # Attempt mode switch
        self.mode_switch_in_progress = True
        
        try:
            if desired_mode:
                success = self.enable_bypass_mode()
                mode_name = "bypass"
            else:
                success = self.disable_bypass_mode()
                mode_name = "normal"
            
            if success:
                self.mode_switches += 1
                response.success = True
                response.message = f"Successfully switched to {mode_name} mode"
                self.get_logger().info(f"Mode switched to {mode_name}")
            else:
                response.success = False
                response.message = f"Failed to switch to {mode_name} mode: {self.error_message}"
                self.get_logger().error(f"Mode switch failed: {self.error_message}")
        
        except Exception as e:
            response.success = False
            response.message = f"Mode switch error: {str(e)}"
            self.get_logger().error(f"Mode switch exception: {str(e)}")
        
        finally:
            self.mode_switch_in_progress = False
        
        # Publish updated status
        self._publish_status()
        
        return response
    
    def enable_bypass_mode(self) -> bool:
        """
        Enable bypass mode by disabling safety systems.
        
        Returns:
            True if bypass mode was successfully enabled, False otherwise
        """
        try:
            self.get_logger().info("Enabling bypass mode...")
            
            # Clear any previous error messages
            self.error_message = ""
            
            # Perform mode transition safety checks
            if not self._validate_bypass_mode_transition():
                return False
            
            # Disable safety systems (will be implemented with SafetyOverrideManager)
            if not self._disable_safety_systems():
                self.error_message = "Failed to disable safety systems"
                return False
            
            # Apply bypass mode configuration (will be implemented with ConfigurationOverride)
            if not self._apply_bypass_configuration():
                self.error_message = "Failed to apply bypass configuration"
                return False
            
            # Update state
            self.bypass_active = True
            self.safety_systems_disabled = True
            
            self.get_logger().info("Bypass mode enabled successfully")
            return True
            
        except Exception as e:
            self.error_message = f"Exception during bypass mode enable: {str(e)}"
            self.get_logger().error(self.error_message)
            return False
    
    def disable_bypass_mode(self) -> bool:
        """
        Disable bypass mode and restore normal operation.
        
        Returns:
            True if normal mode was successfully restored, False otherwise
        """
        try:
            self.get_logger().info("Disabling bypass mode...")
            
            # Clear any previous error messages
            self.error_message = ""
            
            # Stop any current motion commands safely
            self._stop_current_motion()
            
            # Re-enable safety systems (will be implemented with SafetyOverrideManager)
            if not self._enable_safety_systems():
                self.error_message = "Failed to re-enable safety systems"
                return False
            
            # Restore normal configuration
            if not self._restore_normal_configuration():
                self.error_message = "Failed to restore normal configuration"
                return False
            
            # Update state
            self.bypass_active = False
            self.safety_systems_disabled = False
            
            self.get_logger().info("Normal mode restored successfully")
            return True
            
        except Exception as e:
            self.error_message = f"Exception during bypass mode disable: {str(e)}"
            self.get_logger().error(self.error_message)
            return False
    
    def _validate_bypass_mode_transition(self) -> bool:
        """
        Validate that it's safe to transition to bypass mode.
        
        Returns:
            True if transition is safe, False otherwise
        """
        # Check if emergency stop is active
        if self.emergency_stop_active:
            self.error_message = "Cannot enable bypass mode while emergency stop is active"
            return False
        
        # Check if another mode switch is in progress
        if self.mode_switch_in_progress:
            self.error_message = "Mode switch already in progress"
            return False
        
        # Additional safety checks can be added here
        return True
    
    def _disable_safety_systems(self) -> bool:
        """
        Disable safety systems for bypass mode.
        
        Returns:
            True if safety systems were successfully disabled, False otherwise
        """
        # This will be implemented when SafetyOverrideManager is created
        # For now, just log the action
        self.get_logger().info("Safety systems disabled (placeholder)")
        return True
    
    def _enable_safety_systems(self) -> bool:
        """
        Re-enable safety systems for normal mode.
        
        Returns:
            True if safety systems were successfully enabled, False otherwise
        """
        # This will be implemented when SafetyOverrideManager is created
        # For now, just log the action
        self.get_logger().info("Safety systems enabled (placeholder)")
        return True
    
    def _apply_bypass_configuration(self) -> bool:
        """
        Apply bypass mode configuration parameters.
        
        Returns:
            True if configuration was successfully applied, False otherwise
        """
        # This will be implemented when ConfigurationOverride is created
        # For now, just log the action
        self.get_logger().info("Bypass configuration applied (placeholder)")
        return True
    
    def _restore_normal_configuration(self) -> bool:
        """
        Restore normal mode configuration parameters.
        
        Returns:
            True if configuration was successfully restored, False otherwise
        """
        # This will be implemented when ConfigurationOverride is created
        # For now, just log the action
        self.get_logger().info("Normal configuration restored (placeholder)")
        return True
    
    def _stop_current_motion(self):
        """Stop any current motion commands safely."""
        # This will send stop commands when DirectArduinoDriver is implemented
        if self.debug_logging:
            self._publish_debug("Current motion stopped for mode switch")
    
    def _publish_status(self):
        """Publish current bypass controller status."""
        if not self.initialization_complete:
            return
        
        # Create status message
        status_data = {
            "mode": "bypass" if self.bypass_active else "normal",
            "arduino_connected": self.arduino_connected,
            "safety_systems_disabled": self.safety_systems_disabled,
            "emergency_stop_active": self.emergency_stop_active,
            "mode_switch_in_progress": self.mode_switch_in_progress,
            "last_cmd_vel_time": self.last_cmd_vel_time.nanoseconds if self.last_cmd_vel_time else None,
            "error_message": self.error_message,
            "statistics": {
                "cmd_vel_count": self.cmd_vel_count,
                "mode_switches": self.mode_switches,
                "emergency_stops": self.emergency_stops
            },
            "timestamp": self.get_clock().now().nanoseconds
        }
        
        # Publish status as JSON string
        status_msg = String()
        status_msg.data = json.dumps(status_data)
        self.bypass_status_pub.publish(status_msg)
    
    def _publish_debug(self, message: str):
        """
        Publish debug message if debug logging is enabled.
        
        Args:
            message: Debug message to publish
        """
        if self.debug_logging and hasattr(self, 'debug_pub'):
            debug_msg = String()
            debug_msg.data = f"[{self.get_clock().now().nanoseconds}] {message}"
            self.debug_pub.publish(debug_msg)
    
    def _check_timeouts(self):
        """Check for various timeout conditions."""
        current_time = self.get_clock().now()
        
        # Check cmd_vel timeout
        if (self.last_cmd_vel_time and 
            (current_time - self.last_cmd_vel_time).nanoseconds / 1e9 > self.cmd_vel_timeout):
            if self.debug_logging:
                self._publish_debug("cmd_vel timeout detected")
        
        # Check emergency stop timeout
        if (self.last_emergency_stop_time and 
            (current_time - self.last_emergency_stop_time).nanoseconds / 1e9 > self.emergency_stop_timeout):
            if self.debug_logging:
                self._publish_debug("emergency_stop timeout detected")
    
    def destroy_node(self):
        """Clean shutdown of the bypass controller."""
        try:
            self.get_logger().info("Shutting down bypass controller...")
            
            # Stop any current motion
            self._stop_current_motion()
            
            # If in bypass mode, try to restore normal mode
            if self.bypass_active:
                self.get_logger().info("Restoring normal mode before shutdown...")
                self.disable_bypass_mode()
            
            # Publish final status
            self._publish_status()
            
        except Exception as e:
            self.get_logger().error(f"Error during bypass controller shutdown: {e}")
        
        super().destroy_node()


def main(args=None):
    """Main entry point for bypass controller node."""
    rclpy.init(args=args)
    
    try:
        node = BypassController()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()