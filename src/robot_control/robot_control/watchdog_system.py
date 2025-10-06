#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import Bool, String
from robot_interfaces.msg import EmergencyStop, HardwareStatus
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import yaml
import os


class WatchdogState(Enum):
    """Watchdog timer states"""
    ACTIVE = "active"
    TIMEOUT = "timeout"
    DISABLED = "disabled"
    RECOVERING = "recovering"


@dataclass
class WatchdogTimer:
    """Individual watchdog timer configuration and state"""
    name: str
    timeout_duration: float  # seconds
    critical: bool = True  # Whether timeout triggers emergency stop
    last_heartbeat: datetime = field(default_factory=datetime.now)
    state: WatchdogState = WatchdogState.ACTIVE
    timeout_count: int = 0
    recovery_callback: Optional[Callable] = None
    description: str = ""


class WatchdogSystem(Node):
    """
    Watchdog timer system that monitors critical components and triggers
    safety actions when components become unresponsive.
    """
    
    def __init__(self):
        super().__init__('watchdog_system')
        
        # Watchdog timers registry
        self.watchdog_timers: Dict[str, WatchdogTimer] = {}
        self.critical_components: Set[str] = set()
        
        # System state
        self.system_healthy = True
        self.emergency_stop_triggered = False
        
        # Configuration
        self.default_timeout = 5.0  # seconds
        self.check_interval = 0.5  # seconds
        self.max_timeout_count = 3  # Max timeouts before permanent disable
        
        # Thread safety
        self.watchdog_lock = threading.RLock()
        
        # Load configuration
        self._load_watchdog_config()
        
        # QoS profiles
        reliable_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1
        )
        
        # Publishers
        self.emergency_stop_pub = self.create_publisher(
            EmergencyStop, '/emergency_stop', reliable_qos)
        self.watchdog_status_pub = self.create_publisher(
            String, '/watchdog_status', 10)
        self.component_alert_pub = self.create_publisher(
            String, '/component_alert', 10)
        
        # Subscribers
        self.component_heartbeat_sub = self.create_subscription(
            String, '/component_heartbeat', self.component_heartbeat_callback, 10)
        self.watchdog_reset_sub = self.create_subscription(
            String, '/watchdog_reset', self.watchdog_reset_callback, 10)
        self.emergency_stop_sub = self.create_subscription(
            EmergencyStop, '/emergency_stop', self.emergency_stop_callback, reliable_qos)
        
        # Timers
        self.watchdog_check_timer = self.create_timer(self.check_interval, self.check_watchdogs)
        self.status_publish_timer = self.create_timer(2.0, self.publish_status)
        
        # Initialize default watchdog timers for critical components
        self._initialize_default_watchdogs()
        
        self.get_logger().info("Watchdog System initialized")
    
    def _load_watchdog_config(self):
        """Load watchdog configuration from robot config"""
        try:
            config_path = os.path.join(
                os.path.dirname(__file__), '..', '..', '..', '..', 'config', 'robot_config.yaml'
            )
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    
                safety_config = config.get('robot', {}).get('safety', {})
                
                # Load watchdog parameters
                self.default_timeout = safety_config.get('watchdog_interval', self.default_timeout)
                self.check_interval = safety_config.get('watchdog_check_interval', self.check_interval)
                
                # Load critical components list
                critical_components = safety_config.get('critical_components', [])
                if critical_components:
                    self.critical_components = set(critical_components)
                else:
                    # Default critical components
                    self.critical_components = {
                        'arduino_bridge', 'hardware_manager', 'safety_supervisor',
                        'emergency_stop_handler', 'velocity_limiter'
                    }
                
                # Load component-specific watchdog configurations
                watchdog_config = safety_config.get('watchdog_timers', {})
                for component, config_data in watchdog_config.items():
                    timeout = config_data.get('timeout', self.default_timeout)
                    critical = config_data.get('critical', component in self.critical_components)
                    description = config_data.get('description', f"Watchdog for {component}")
                    
                    self.register_watchdog(component, timeout, critical, description)
                
                self.get_logger().info(f"Loaded watchdog config: {len(self.watchdog_timers)} timers")
            else:
                self.get_logger().warn("Watchdog config not found, using defaults")
                
        except Exception as e:
            self.get_logger().error(f"Failed to load watchdog config: {e}")
    
    def _initialize_default_watchdogs(self):
        """Initialize watchdog timers for critical components"""
        # Register watchdogs for critical components if not already configured
        for component in self.critical_components:
            if component not in self.watchdog_timers:
                self.register_watchdog(
                    component, 
                    self.default_timeout, 
                    critical=True,
                    description=f"Critical component watchdog for {component}"
                )
    
    def register_watchdog(self, component_name: str, timeout_duration: float, 
                         critical: bool = True, description: str = "") -> bool:
        """
        Register a new watchdog timer for a component
        
        Args:
            component_name: Name of the component to monitor
            timeout_duration: Timeout duration in seconds
            critical: Whether timeout triggers emergency stop
            description: Human-readable description
            
        Returns:
            True if watchdog was registered successfully
        """
        try:
            with self.watchdog_lock:
                if component_name in self.watchdog_timers:
                    self.get_logger().warn(f"Watchdog for {component_name} already exists")
                    return False
                
                watchdog = WatchdogTimer(
                    name=component_name,
                    timeout_duration=timeout_duration,
                    critical=critical,
                    description=description or f"Watchdog for {component_name}"
                )
                
                self.watchdog_timers[component_name] = watchdog
                
                if critical:
                    self.critical_components.add(component_name)
                
                self.get_logger().info(
                    f"Registered watchdog: {component_name} "
                    f"(timeout: {timeout_duration}s, critical: {critical})")
                
                return True
                
        except Exception as e:
            self.get_logger().error(f"Failed to register watchdog for {component_name}: {e}")
            return False
    
    def unregister_watchdog(self, component_name: str) -> bool:
        """
        Unregister a watchdog timer
        
        Args:
            component_name: Name of the component
            
        Returns:
            True if watchdog was unregistered successfully
        """
        with self.watchdog_lock:
            if component_name in self.watchdog_timers:
                del self.watchdog_timers[component_name]
                self.critical_components.discard(component_name)
                self.get_logger().info(f"Unregistered watchdog: {component_name}")
                return True
            else:
                self.get_logger().warn(f"Watchdog for {component_name} not found")
                return False
    
    def feed_watchdog(self, component_name: str) -> bool:
        """
        Feed (reset) a watchdog timer
        
        Args:
            component_name: Name of the component
            
        Returns:
            True if watchdog was fed successfully
        """
        with self.watchdog_lock:
            if component_name not in self.watchdog_timers:
                # Auto-register unknown components with default settings
                self.register_watchdog(
                    component_name, 
                    self.default_timeout, 
                    critical=component_name in self.critical_components
                )
            
            watchdog = self.watchdog_timers[component_name]
            watchdog.last_heartbeat = datetime.now()
            
            # Reset state if it was in timeout
            if watchdog.state == WatchdogState.TIMEOUT:
                watchdog.state = WatchdogState.RECOVERING
                self.get_logger().info(f"Watchdog {component_name} recovering from timeout")
            elif watchdog.state == WatchdogState.RECOVERING:
                watchdog.state = WatchdogState.ACTIVE
                self.get_logger().info(f"Watchdog {component_name} fully recovered")
            
            return True
    
    def disable_watchdog(self, component_name: str, reason: str = "") -> bool:
        """
        Disable a watchdog timer
        
        Args:
            component_name: Name of the component
            reason: Reason for disabling
            
        Returns:
            True if watchdog was disabled successfully
        """
        with self.watchdog_lock:
            if component_name in self.watchdog_timers:
                watchdog = self.watchdog_timers[component_name]
                watchdog.state = WatchdogState.DISABLED
                
                self.get_logger().info(
                    f"Disabled watchdog: {component_name}" + 
                    (f" - {reason}" if reason else ""))
                return True
            else:
                self.get_logger().warn(f"Cannot disable unknown watchdog: {component_name}")
                return False
    
    def enable_watchdog(self, component_name: str) -> bool:
        """
        Enable a previously disabled watchdog timer
        
        Args:
            component_name: Name of the component
            
        Returns:
            True if watchdog was enabled successfully
        """
        with self.watchdog_lock:
            if component_name in self.watchdog_timers:
                watchdog = self.watchdog_timers[component_name]
                if watchdog.state == WatchdogState.DISABLED:
                    watchdog.state = WatchdogState.ACTIVE
                    watchdog.last_heartbeat = datetime.now()  # Reset timer
                    watchdog.timeout_count = 0  # Reset timeout count
                    
                    self.get_logger().info(f"Enabled watchdog: {component_name}")
                    return True
                else:
                    self.get_logger().warn(f"Watchdog {component_name} is not disabled")
                    return False
            else:
                self.get_logger().warn(f"Cannot enable unknown watchdog: {component_name}")
                return False
    
    def check_watchdogs(self) -> None:
        """Check all watchdog timers for timeouts"""
        try:
            current_time = datetime.now()
            timeout_components = []
            
            with self.watchdog_lock:
                for component_name, watchdog in self.watchdog_timers.items():
                    if watchdog.state == WatchdogState.DISABLED:
                        continue
                    
                    # Calculate time since last heartbeat
                    time_since_heartbeat = (current_time - watchdog.last_heartbeat).total_seconds()
                    
                    if time_since_heartbeat > watchdog.timeout_duration:
                        if watchdog.state != WatchdogState.TIMEOUT:
                            # First timeout detection
                            watchdog.state = WatchdogState.TIMEOUT
                            watchdog.timeout_count += 1
                            
                            self.get_logger().error(
                                f"Watchdog timeout: {component_name} "
                                f"({time_since_heartbeat:.1f}s > {watchdog.timeout_duration:.1f}s) "
                                f"- Count: {watchdog.timeout_count}")
                            
                            # Publish component alert
                            alert_msg = String()
                            alert_msg.data = f"TIMEOUT:{component_name}:{time_since_heartbeat:.1f}"
                            self.component_alert_pub.publish(alert_msg)
                            
                            if watchdog.critical:
                                timeout_components.append(component_name)
                            
                            # Disable watchdog if too many timeouts
                            if watchdog.timeout_count >= self.max_timeout_count:
                                self.disable_watchdog(
                                    component_name, 
                                    f"Max timeout count reached ({self.max_timeout_count})")
            
            # Trigger emergency stop if critical components timed out
            if timeout_components and not self.emergency_stop_triggered:
                self._trigger_emergency_stop_for_timeouts(timeout_components)
            
            # Update system health status
            self._update_system_health()
            
        except Exception as e:
            self.get_logger().error(f"Error checking watchdogs: {e}")
    
    def _trigger_emergency_stop_for_timeouts(self, timeout_components: List[str]) -> None:
        """Trigger emergency stop due to component timeouts"""
        reason = f"Critical component timeouts: {', '.join(timeout_components)}"
        
        emergency_msg = EmergencyStop()
        emergency_msg.timestamp = self.get_clock().now().to_msg()
        emergency_msg.active = True
        emergency_msg.reason = reason
        emergency_msg.source = "watchdog_system"
        emergency_msg.sequence = int(time.time())  # Use timestamp as sequence
        
        self.emergency_stop_pub.publish(emergency_msg)
        self.emergency_stop_triggered = True
        
        self.get_logger().error(f"EMERGENCY STOP TRIGGERED BY WATCHDOG: {reason}")
    
    def _update_system_health(self) -> None:
        """Update overall system health status"""
        with self.watchdog_lock:
            # Check if any critical components are in timeout
            critical_timeouts = [
                name for name, watchdog in self.watchdog_timers.items()
                if watchdog.critical and watchdog.state == WatchdogState.TIMEOUT
            ]
            
            self.system_healthy = len(critical_timeouts) == 0
    
    def component_heartbeat_callback(self, msg: String) -> None:
        """Handle component heartbeat messages"""
        component_name = msg.data
        self.feed_watchdog(component_name)
    
    def watchdog_reset_callback(self, msg: String) -> None:
        """Handle watchdog reset requests"""
        component_name = msg.data
        
        if component_name == "ALL":
            # Reset all watchdogs
            with self.watchdog_lock:
                for watchdog in self.watchdog_timers.values():
                    watchdog.last_heartbeat = datetime.now()
                    watchdog.state = WatchdogState.ACTIVE
                    watchdog.timeout_count = 0
            
            self.get_logger().info("All watchdogs reset")
        else:
            # Reset specific watchdog
            if self.enable_watchdog(component_name):
                self.get_logger().info(f"Watchdog reset: {component_name}")
            else:
                self.get_logger().warn(f"Failed to reset watchdog: {component_name}")
    
    def emergency_stop_callback(self, msg: EmergencyStop) -> None:
        """Handle emergency stop messages"""
        if not msg.active:
            # Emergency stop cleared - reset our trigger flag
            self.emergency_stop_triggered = False
            self.get_logger().info("Emergency stop cleared - watchdog system ready")
    
    def publish_status(self) -> None:
        """Publish watchdog system status"""
        try:
            with self.watchdog_lock:
                status_data = {
                    'system_healthy': self.system_healthy,
                    'emergency_stop_triggered': self.emergency_stop_triggered,
                    'total_watchdogs': len(self.watchdog_timers),
                    'critical_watchdogs': len(self.critical_components),
                    'watchdog_states': {}
                }
                
                # Add individual watchdog states
                for name, watchdog in self.watchdog_timers.items():
                    current_time = datetime.now()
                    time_since_heartbeat = (current_time - watchdog.last_heartbeat).total_seconds()
                    
                    status_data['watchdog_states'][name] = {
                        'state': watchdog.state.value,
                        'critical': watchdog.critical,
                        'timeout_duration': watchdog.timeout_duration,
                        'time_since_heartbeat': time_since_heartbeat,
                        'timeout_count': watchdog.timeout_count,
                        'description': watchdog.description
                    }
            
            status_msg = String()
            status_msg.data = str(status_data)
            self.watchdog_status_pub.publish(status_msg)
            
        except Exception as e:
            self.get_logger().error(f"Error publishing watchdog status: {e}")
    
    def get_system_status(self) -> Dict:
        """Get current watchdog system status"""
        with self.watchdog_lock:
            current_time = datetime.now()
            
            return {
                'system_healthy': self.system_healthy,
                'emergency_stop_triggered': self.emergency_stop_triggered,
                'watchdog_timers': {
                    name: {
                        'state': watchdog.state.value,
                        'critical': watchdog.critical,
                        'timeout_duration': watchdog.timeout_duration,
                        'time_since_heartbeat': (current_time - watchdog.last_heartbeat).total_seconds(),
                        'timeout_count': watchdog.timeout_count,
                        'description': watchdog.description
                    }
                    for name, watchdog in self.watchdog_timers.items()
                },
                'critical_components': list(self.critical_components)
            }


def main(args=None):
    rclpy.init(args=args)
    
    try:
        watchdog_system = WatchdogSystem()
        rclpy.spin(watchdog_system)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error in watchdog system: {e}")
    finally:
        if 'watchdog_system' in locals():
            watchdog_system.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()