#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import Bool, String
from geometry_msgs.msg import Twist
from robot_interfaces.msg import EmergencyStop, HardwareStatus
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from enum import Enum
import yaml
import os


class EmergencyStopState(Enum):
    """Emergency stop system states"""
    NORMAL = "normal"
    STOPPING = "stopping"
    STOPPED = "stopped"
    RECOVERING = "recovering"


@dataclass
class ComponentStatus:
    """Status of a component in the emergency stop system"""
    name: str
    acknowledged: bool = False
    stopped: bool = False
    last_heartbeat: datetime = None
    recovery_ready: bool = False


class EmergencyStopHandler(Node):
    """
    Emergency stop handler that coordinates emergency stops across all robot components.
    Manages emergency stop state, component acknowledgment, and recovery procedures.
    """
    
    def __init__(self):
        super().__init__('emergency_stop_handler')
        
        # Emergency stop state
        self.state = EmergencyStopState.NORMAL
        self.emergency_stop_sequence = 0
        self.emergency_stop_reason = ""
        self.emergency_stop_source = ""
        self.emergency_stop_timestamp = None
        
        # Component tracking
        self.registered_components: Dict[str, ComponentStatus] = {}
        self.critical_components = {'arduino_bridge', 'hardware_manager', 'safety_supervisor'}
        
        # Configuration
        self.stop_timeout = 5.0  # seconds to wait for components to stop
        self.heartbeat_timeout = 3.0  # seconds before considering component unresponsive
        
        # Thread safety
        self.state_lock = threading.RLock()
        
        # Load configuration
        self._load_emergency_stop_config()
        
        # QoS profiles
        reliable_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1
        )
        
        # Publishers
        self.emergency_stop_pub = self.create_publisher(
            EmergencyStop, '/emergency_stop', reliable_qos)
        self.emergency_stop_status_pub = self.create_publisher(
            String, '/emergency_stop_status', 10)
        self.zero_cmd_vel_pub = self.create_publisher(
            Twist, '/cmd_vel_emergency', 10)
        
        # Subscribers
        self.emergency_stop_trigger_sub = self.create_subscription(
            Bool, '/emergency_stop_trigger', self.emergency_stop_trigger_callback, reliable_qos)
        self.emergency_stop_ack_sub = self.create_subscription(
            String, '/emergency_stop_ack', self.emergency_stop_ack_callback, reliable_qos)
        self.component_heartbeat_sub = self.create_subscription(
            String, '/component_heartbeat', self.component_heartbeat_callback, 10)
        self.recovery_ready_sub = self.create_subscription(
            String, '/recovery_ready', self.recovery_ready_callback, reliable_qos)
        self.safety_reset_sub = self.create_subscription(
            Bool, '/safety_reset', self.safety_reset_callback, reliable_qos)
        
        # Timers
        self.state_monitor_timer = self.create_timer(0.1, self.state_monitor_callback)
        self.heartbeat_check_timer = self.create_timer(1.0, self.check_component_heartbeats)
        self.zero_cmd_timer = None  # Created when emergency stop is active
        
        # Register this handler as a component
        self.register_component('emergency_stop_handler')
        
        self.get_logger().info("Emergency Stop Handler initialized")
    
    def _load_emergency_stop_config(self):
        """Load emergency stop configuration"""
        try:
            config_path = os.path.join(
                os.path.dirname(__file__), '..', '..', '..', '..', 'config', 'robot_config.yaml'
            )
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    
                safety_config = config.get('robot', {}).get('safety', {})
                
                self.stop_timeout = safety_config.get('emergency_stop_timeout', self.stop_timeout)
                self.heartbeat_timeout = safety_config.get('heartbeat_timeout', self.heartbeat_timeout)
                
                # Load critical components list
                critical_components = safety_config.get('critical_components', [])
                if critical_components:
                    self.critical_components = set(critical_components)
                
                self.get_logger().info(f"Emergency stop config loaded: timeout={self.stop_timeout}s")
            else:
                self.get_logger().warn("Emergency stop config not found, using defaults")
                
        except Exception as e:
            self.get_logger().error(f"Failed to load emergency stop config: {e}")
    
    def register_component(self, component_name: str) -> None:
        """
        Register a component with the emergency stop system
        
        Args:
            component_name: Name of the component to register
        """
        with self.state_lock:
            if component_name not in self.registered_components:
                self.registered_components[component_name] = ComponentStatus(
                    name=component_name,
                    last_heartbeat=datetime.now()
                )
                self.get_logger().info(f"Registered component: {component_name}")
    
    def trigger_emergency_stop(self, reason: str, source: str = "unknown") -> None:
        """
        Trigger emergency stop across all components
        
        Args:
            reason: Reason for emergency stop
            source: Component that triggered the stop
        """
        with self.state_lock:
            if self.state == EmergencyStopState.NORMAL:
                self.state = EmergencyStopState.STOPPING
                self.emergency_stop_sequence += 1
                self.emergency_stop_reason = reason
                self.emergency_stop_source = source
                self.emergency_stop_timestamp = datetime.now()
                
                # Reset component acknowledgments
                for component in self.registered_components.values():
                    component.acknowledged = False
                    component.stopped = False
                    component.recovery_ready = False
                
                # Publish emergency stop message
                self._publish_emergency_stop_message(True)
                
                # Start publishing zero velocity commands
                self._start_zero_cmd_timer()
                
                self.get_logger().error(
                    f"EMERGENCY STOP TRIGGERED: {reason} (source: {source}, seq: {self.emergency_stop_sequence})")
    
    def clear_emergency_stop(self) -> bool:
        """
        Attempt to clear emergency stop and return to normal operation
        
        Returns:
            True if emergency stop was successfully cleared
        """
        with self.state_lock:
            if self.state not in [EmergencyStopState.STOPPED, EmergencyStopState.RECOVERING]:
                self.get_logger().warn("Cannot clear emergency stop: not in stopped state")
                return False
            
            # Check if all critical components are ready for recovery
            critical_ready = all(
                self.registered_components.get(comp, ComponentStatus("")).recovery_ready
                for comp in self.critical_components
                if comp in self.registered_components
            )
            
            if not critical_ready:
                missing_components = [
                    comp for comp in self.critical_components
                    if comp in self.registered_components and 
                    not self.registered_components[comp].recovery_ready
                ]
                self.get_logger().warn(
                    f"Cannot clear emergency stop: components not ready: {missing_components}")
                return False
            
            # Transition to recovery state
            self.state = EmergencyStopState.RECOVERING
            
            # Publish emergency stop cleared message
            self._publish_emergency_stop_message(False)
            
            # Stop zero velocity commands
            self._stop_zero_cmd_timer()
            
            # Wait a moment for components to process the clear message
            self.create_timer(1.0, self._complete_recovery, count=1)
            
            self.get_logger().info("Emergency stop clearing initiated")
            return True
    
    def _complete_recovery(self) -> None:
        """Complete the recovery process and return to normal state"""
        with self.state_lock:
            self.state = EmergencyStopState.NORMAL
            self.emergency_stop_reason = ""
            self.emergency_stop_source = ""
            self.emergency_stop_timestamp = None
            
            # Reset component states
            for component in self.registered_components.values():
                component.acknowledged = False
                component.stopped = False
                component.recovery_ready = False
            
            self.get_logger().info("Emergency stop recovery completed - system normal")
    
    def _publish_emergency_stop_message(self, active: bool) -> None:
        """Publish emergency stop message to all components"""
        msg = EmergencyStop()
        msg.timestamp = self.get_clock().now().to_msg()
        msg.active = active
        msg.reason = self.emergency_stop_reason
        msg.source = self.emergency_stop_source
        msg.sequence = self.emergency_stop_sequence
        
        self.emergency_stop_pub.publish(msg)
        
        # Also publish status string
        status_msg = String()
        if active:
            status_msg.data = f"EMERGENCY_STOP_ACTIVE:{self.emergency_stop_reason}"
        else:
            status_msg.data = "EMERGENCY_STOP_CLEARED"
        self.emergency_stop_status_pub.publish(status_msg)
    
    def _start_zero_cmd_timer(self) -> None:
        """Start publishing zero velocity commands"""
        if self.zero_cmd_timer is not None:
            self.zero_cmd_timer.cancel()
        
        self.zero_cmd_timer = self.create_timer(0.1, self._publish_zero_cmd_vel)
    
    def _stop_zero_cmd_timer(self) -> None:
        """Stop publishing zero velocity commands"""
        if self.zero_cmd_timer is not None:
            self.zero_cmd_timer.cancel()
            self.zero_cmd_timer = None
    
    def _publish_zero_cmd_vel(self) -> None:
        """Publish zero velocity command"""
        zero_cmd = Twist()
        self.zero_cmd_vel_pub.publish(zero_cmd)
    
    def emergency_stop_trigger_callback(self, msg: Bool) -> None:
        """Handle external emergency stop triggers"""
        if msg.data:
            self.trigger_emergency_stop("External trigger", "external_system")
    
    def emergency_stop_ack_callback(self, msg: String) -> None:
        """Handle emergency stop acknowledgments from components"""
        component_name = msg.data
        
        with self.state_lock:
            if component_name in self.registered_components:
                self.registered_components[component_name].acknowledged = True
                self.registered_components[component_name].stopped = True
                self.get_logger().info(f"Component {component_name} acknowledged emergency stop")
            else:
                self.get_logger().warn(f"Unknown component acknowledged emergency stop: {component_name}")
    
    def component_heartbeat_callback(self, msg: String) -> None:
        """Handle component heartbeat messages"""
        component_name = msg.data
        
        with self.state_lock:
            if component_name not in self.registered_components:
                self.register_component(component_name)
            
            self.registered_components[component_name].last_heartbeat = datetime.now()
    
    def recovery_ready_callback(self, msg: String) -> None:
        """Handle recovery ready notifications from components"""
        component_name = msg.data
        
        with self.state_lock:
            if component_name in self.registered_components:
                self.registered_components[component_name].recovery_ready = True
                self.get_logger().info(f"Component {component_name} ready for recovery")
            else:
                self.get_logger().warn(f"Unknown component reported recovery ready: {component_name}")
    
    def safety_reset_callback(self, msg: Bool) -> None:
        """Handle safety reset requests"""
        if msg.data:
            success = self.clear_emergency_stop()
            if success:
                self.get_logger().info("Emergency stop cleared by safety reset")
            else:
                self.get_logger().warn("Safety reset failed")
    
    def state_monitor_callback(self) -> None:
        """Monitor emergency stop state and handle transitions"""
        try:
            with self.state_lock:
                current_time = datetime.now()
                
                if self.state == EmergencyStopState.STOPPING:
                    # Check if all critical components have acknowledged
                    critical_acked = all(
                        self.registered_components.get(comp, ComponentStatus("")).acknowledged
                        for comp in self.critical_components
                        if comp in self.registered_components
                    )
                    
                    # Check timeout
                    if self.emergency_stop_timestamp:
                        time_since_stop = (current_time - self.emergency_stop_timestamp).total_seconds()
                        
                        if critical_acked or time_since_stop > self.stop_timeout:
                            self.state = EmergencyStopState.STOPPED
                            if not critical_acked:
                                self.get_logger().warn(
                                    f"Emergency stop timeout reached ({self.stop_timeout}s) - "
                                    "proceeding without all acknowledgments")
                            else:
                                self.get_logger().info("All critical components stopped")
                
        except Exception as e:
            self.get_logger().error(f"Error in state monitor: {e}")
    
    def check_component_heartbeats(self) -> None:
        """Check for component heartbeat timeouts"""
        try:
            current_time = datetime.now()
            
            with self.state_lock:
                for component_name, status in self.registered_components.items():
                    if status.last_heartbeat:
                        time_since_heartbeat = (current_time - status.last_heartbeat).total_seconds()
                        
                        if time_since_heartbeat > self.heartbeat_timeout:
                            if component_name in self.critical_components:
                                self.get_logger().error(
                                    f"Critical component {component_name} heartbeat timeout "
                                    f"({time_since_heartbeat:.1f}s)")
                                
                                if self.state == EmergencyStopState.NORMAL:
                                    self.trigger_emergency_stop(
                                        f"Component heartbeat timeout: {component_name}",
                                        "emergency_stop_handler"
                                    )
                            else:
                                self.get_logger().warn(
                                    f"Component {component_name} heartbeat timeout "
                                    f"({time_since_heartbeat:.1f}s)")
                
        except Exception as e:
            self.get_logger().error(f"Error checking heartbeats: {e}")
    
    def get_system_status(self) -> Dict:
        """Get current emergency stop system status"""
        with self.state_lock:
            return {
                'state': self.state.value,
                'sequence': self.emergency_stop_sequence,
                'reason': self.emergency_stop_reason,
                'source': self.emergency_stop_source,
                'timestamp': self.emergency_stop_timestamp.isoformat() if self.emergency_stop_timestamp else None,
                'registered_components': len(self.registered_components),
                'critical_components': list(self.critical_components),
                'component_status': {
                    name: {
                        'acknowledged': status.acknowledged,
                        'stopped': status.stopped,
                        'recovery_ready': status.recovery_ready,
                        'last_heartbeat': status.last_heartbeat.isoformat() if status.last_heartbeat else None
                    }
                    for name, status in self.registered_components.items()
                }
            }


def main(args=None):
    rclpy.init(args=args)
    
    try:
        emergency_stop_handler = EmergencyStopHandler()
        rclpy.spin(emergency_stop_handler)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error in emergency stop handler: {e}")
    finally:
        if 'emergency_stop_handler' in locals():
            emergency_stop_handler.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()