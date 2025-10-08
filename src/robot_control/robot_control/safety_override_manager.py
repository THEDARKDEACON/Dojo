#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
import rclpy.parameter
from std_msgs.msg import Bool, String
from geometry_msgs.msg import Twist
from robot_interfaces.msg import EmergencyStop, SafetyStatus
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass
from enum import Enum
import yaml
import os


class SafetySystemState(Enum):
    """Safety system states"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    BYPASSED = "bypassed"
    EMERGENCY_ONLY = "emergency_only"


@dataclass
class SafetySystemInfo:
    """Information about a safety system component"""
    name: str
    state: SafetySystemState
    original_enabled: bool = True
    bypass_reason: str = ""
    bypass_timestamp: Optional[datetime] = None
    emergency_stop_preserved: bool = True


class SafetyOverrideManager(Node):
    """
    Safety Override Manager for Arduino Integration Bypass Mode
    
    Manages selective disabling of safety systems while preserving
    essential emergency stop functionality for bypass mode operation.
    """
    
    def __init__(self):
        super().__init__('safety_override_manager')
        
        # Safety system tracking
        self.safety_systems: Dict[str, SafetySystemInfo] = {}
        self.bypass_mode_active = False
        self.emergency_stop_active = False
        self.emergency_stop_preserved = True
        
        # Thread safety
        self.override_lock = threading.RLock()
        
        # Configuration
        self.declare_parameter('preserve_emergency_stop', True)
        self.declare_parameter('bypass_timeout', 3600.0)  # 1 hour default timeout
        
        self.preserve_emergency_stop = self.get_parameter('preserve_emergency_stop').value
        self.bypass_timeout = self.get_parameter('bypass_timeout').value
        
        # QoS profiles
        reliable_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1
        )
        
        # Publishers
        self.override_status_pub = self.create_publisher(
            String, '/safety_override_status', reliable_qos)
        self.emergency_stop_pub = self.create_publisher(
            EmergencyStop, '/emergency_stop', reliable_qos)
        self.safety_bypass_pub = self.create_publisher(
            Bool, '/safety_bypass_active', reliable_qos)
        
        # Subscribers for emergency stop preservation
        self.emergency_stop_trigger_sub = self.create_subscription(
            Bool, '/emergency_stop_trigger', self.emergency_stop_trigger_callback, reliable_qos)
        self.safety_reset_sub = self.create_subscription(
            Bool, '/safety_reset', self.safety_reset_callback, reliable_qos)
        
        # Safety system control publishers (for disabling components)
        self.emergency_stop_handler_disable_pub = self.create_publisher(
            Bool, '/emergency_stop_handler/disable_auto_triggers', 10)
        self.safety_supervisor_bypass_pub = self.create_publisher(
            Bool, '/safety_supervisor/bypass_velocity_limits', 10)
        self.hardware_manager_disable_timeouts_pub = self.create_publisher(
            Bool, '/hardware_manager/disable_timeouts', 10)
        self.hardware_discovery_disable_pub = self.create_publisher(
            Bool, '/hardware_discovery/disable_requirements', 10)
        
        # Initialize safety system registry
        self._initialize_safety_systems()
        
        # Timer for monitoring bypass timeout
        self.bypass_monitor_timer = self.create_timer(10.0, self._monitor_bypass_timeout)
        
        self.get_logger().info("Safety Override Manager initialized")
    
    def _initialize_safety_systems(self):
        """Initialize the registry of safety systems that can be overridden"""
        safety_systems = [
            'emergency_stop_handler',
            'safety_supervisor', 
            'hardware_manager',
            'hardware_discovery',
            'camera_driver',
            'lidar_driver'
        ]
        
        for system_name in safety_systems:
            self.safety_systems[system_name] = SafetySystemInfo(
                name=system_name,
                state=SafetySystemState.ENABLED
            )
        
        self.get_logger().info(f"Initialized {len(safety_systems)} safety systems for override management")
    
    def disable_safety_systems(self, reason: str = "bypass_mode") -> bool:
        """
        Disable safety systems for bypass mode while preserving emergency stop
        
        Args:
            reason: Reason for disabling safety systems
            
        Returns:
            True if safety systems were successfully disabled
        """
        with self.override_lock:
            if self.bypass_mode_active:
                self.get_logger().warn("Safety systems already disabled for bypass mode")
                return True
            
            try:
                self.get_logger().info(f"Disabling safety systems for bypass mode: {reason}")
                
                # Disable EmergencyStopHandler automatic triggers but preserve manual triggers
                self._disable_emergency_stop_handler()
                
                # Bypass SafetySupervisor velocity limiting
                self._bypass_safety_supervisor()
                
                # Disable hardware discovery timeout emergency stops
                self._disable_hardware_discovery_timeouts()
                
                # Remove camera/LiDAR dependency requirements
                self._disable_sensor_dependencies()
                
                # Mark bypass mode as active
                self.bypass_mode_active = True
                
                # Update all safety system states
                for system_info in self.safety_systems.values():
                    if system_info.name == 'emergency_stop_handler':
                        # Emergency stop handler is set to emergency-only mode
                        system_info.state = SafetySystemState.EMERGENCY_ONLY
                    else:
                        system_info.state = SafetySystemState.DISABLED
                    
                    system_info.bypass_reason = reason
                    system_info.bypass_timestamp = datetime.now()
                
                # Publish bypass status
                self._publish_override_status()
                
                # Publish safety bypass active signal
                bypass_msg = Bool()
                bypass_msg.data = True
                self.safety_bypass_pub.publish(bypass_msg)
                
                self.get_logger().info("Safety systems successfully disabled for bypass mode")
                return True
                
            except Exception as e:
                self.get_logger().error(f"Failed to disable safety systems: {e}")
                return False
    
    def enable_safety_systems(self) -> bool:
        """
        Re-enable all safety systems and return to normal operation
        
        Returns:
            True if safety systems were successfully re-enabled
        """
        with self.override_lock:
            if not self.bypass_mode_active:
                self.get_logger().warn("Safety systems not currently disabled")
                return True
            
            try:
                self.get_logger().info("Re-enabling safety systems for normal operation")
                
                # Re-enable EmergencyStopHandler automatic triggers
                self._enable_emergency_stop_handler()
                
                # Re-enable SafetySupervisor velocity limiting
                self._enable_safety_supervisor()
                
                # Re-enable hardware discovery timeouts
                self._enable_hardware_discovery_timeouts()
                
                # Re-enable sensor dependencies
                self._enable_sensor_dependencies()
                
                # Mark bypass mode as inactive
                self.bypass_mode_active = False
                
                # Update all safety system states
                for system_info in self.safety_systems.values():
                    system_info.state = SafetySystemState.ENABLED
                    system_info.bypass_reason = ""
                    system_info.bypass_timestamp = None
                
                # Publish bypass status
                self._publish_override_status()
                
                # Publish safety bypass inactive signal
                bypass_msg = Bool()
                bypass_msg.data = False
                self.safety_bypass_pub.publish(bypass_msg)
                
                self.get_logger().info("Safety systems successfully re-enabled")
                return True
                
            except Exception as e:
                self.get_logger().error(f"Failed to re-enable safety systems: {e}")
                # Try the enhanced restart method as fallback
                return self.enable_safety_systems_with_restart()
    
    def _disable_emergency_stop_handler(self):
        """Disable EmergencyStopHandler automatic triggers while preserving manual emergency stop"""
        try:
            # Create a parameter override to disable automatic triggers
            # This approach works by setting parameters that the emergency stop handler can check
            self.set_parameters([
                rclpy.parameter.Parameter('emergency_stop_handler.disable_auto_triggers', 
                                        rclpy.Parameter.Type.BOOL, True),
                rclpy.parameter.Parameter('emergency_stop_handler.disable_heartbeat_monitoring', 
                                        rclpy.Parameter.Type.BOOL, True),
                rclpy.parameter.Parameter('emergency_stop_handler.bypass_mode_active', 
                                        rclpy.Parameter.Type.BOOL, True)
            ])
            
            # Send signal to disable automatic triggers (heartbeat timeouts, etc.)
            disable_msg = Bool()
            disable_msg.data = True
            self.emergency_stop_handler_disable_pub.publish(disable_msg)
            
            # Update system info
            system_info = self.safety_systems['emergency_stop_handler']
            system_info.emergency_stop_preserved = True
            
            self.get_logger().info("Disabled EmergencyStopHandler automatic triggers (manual emergency stop preserved)")
            
        except Exception as e:
            self.get_logger().error(f"Failed to disable emergency stop handler: {e}")
            raise
    
    def _enable_emergency_stop_handler(self):
        """Re-enable EmergencyStopHandler automatic triggers"""
        try:
            # Reset parameter overrides
            self.set_parameters([
                rclpy.parameter.Parameter('emergency_stop_handler.disable_auto_triggers', 
                                        rclpy.Parameter.Type.BOOL, False),
                rclpy.parameter.Parameter('emergency_stop_handler.disable_heartbeat_monitoring', 
                                        rclpy.Parameter.Type.BOOL, False),
                rclpy.parameter.Parameter('emergency_stop_handler.bypass_mode_active', 
                                        rclpy.Parameter.Type.BOOL, False)
            ])
            
            disable_msg = Bool()
            disable_msg.data = False
            self.emergency_stop_handler_disable_pub.publish(disable_msg)
            
            self.get_logger().info("Re-enabled EmergencyStopHandler automatic triggers")
            
        except Exception as e:
            self.get_logger().error(f"Failed to re-enable emergency stop handler: {e}")
            raise
    
    def _bypass_safety_supervisor(self):
        """Bypass SafetySupervisor velocity limiting"""
        try:
            # Set parameters to bypass velocity limiting
            self.set_parameters([
                rclpy.parameter.Parameter('safety_supervisor.bypass_velocity_limits', 
                                        rclpy.Parameter.Type.BOOL, True),
                rclpy.parameter.Parameter('safety_supervisor.disable_obstacle_detection', 
                                        rclpy.Parameter.Type.BOOL, True),
                rclpy.parameter.Parameter('safety_supervisor.bypass_mode_active', 
                                        rclpy.Parameter.Type.BOOL, True)
            ])
            
            bypass_msg = Bool()
            bypass_msg.data = True
            self.safety_supervisor_bypass_pub.publish(bypass_msg)
            
            self.get_logger().info("Bypassed SafetySupervisor velocity limiting")
            
        except Exception as e:
            self.get_logger().error(f"Failed to bypass safety supervisor: {e}")
            raise
    
    def _enable_safety_supervisor(self):
        """Re-enable SafetySupervisor velocity limiting"""
        try:
            # Reset parameter overrides
            self.set_parameters([
                rclpy.parameter.Parameter('safety_supervisor.bypass_velocity_limits', 
                                        rclpy.Parameter.Type.BOOL, False),
                rclpy.parameter.Parameter('safety_supervisor.disable_obstacle_detection', 
                                        rclpy.Parameter.Type.BOOL, False),
                rclpy.parameter.Parameter('safety_supervisor.bypass_mode_active', 
                                        rclpy.Parameter.Type.BOOL, False)
            ])
            
            bypass_msg = Bool()
            bypass_msg.data = False
            self.safety_supervisor_bypass_pub.publish(bypass_msg)
            
            self.get_logger().info("Re-enabled SafetySupervisor velocity limiting")
            
        except Exception as e:
            self.get_logger().error(f"Failed to re-enable safety supervisor: {e}")
            raise
    
    def _disable_hardware_discovery_timeouts(self):
        """Disable hardware discovery timeout emergency stops"""
        try:
            # Set parameters to disable hardware discovery timeouts
            self.set_parameters([
                rclpy.parameter.Parameter('hardware_manager.disable_timeout_emergency_stops', 
                                        rclpy.Parameter.Type.BOOL, True),
                rclpy.parameter.Parameter('hardware_discovery.disable_requirements', 
                                        rclpy.Parameter.Type.BOOL, True),
                rclpy.parameter.Parameter('hardware_manager.bypass_mode_active', 
                                        rclpy.Parameter.Type.BOOL, True)
            ])
            
            disable_msg = Bool()
            disable_msg.data = True
            self.hardware_manager_disable_timeouts_pub.publish(disable_msg)
            self.hardware_discovery_disable_pub.publish(disable_msg)
            
            self.get_logger().info("Disabled hardware discovery timeout emergency stops")
            
        except Exception as e:
            self.get_logger().error(f"Failed to disable hardware discovery timeouts: {e}")
            raise
    
    def _enable_hardware_discovery_timeouts(self):
        """Re-enable hardware discovery timeout emergency stops"""
        try:
            # Reset parameter overrides
            self.set_parameters([
                rclpy.parameter.Parameter('hardware_manager.disable_timeout_emergency_stops', 
                                        rclpy.Parameter.Type.BOOL, False),
                rclpy.parameter.Parameter('hardware_discovery.disable_requirements', 
                                        rclpy.Parameter.Type.BOOL, False),
                rclpy.parameter.Parameter('hardware_manager.bypass_mode_active', 
                                        rclpy.Parameter.Type.BOOL, False)
            ])
            
            disable_msg = Bool()
            disable_msg.data = False
            self.hardware_manager_disable_timeouts_pub.publish(disable_msg)
            self.hardware_discovery_disable_pub.publish(disable_msg)
            
            self.get_logger().info("Re-enabled hardware discovery timeout emergency stops")
            
        except Exception as e:
            self.get_logger().error(f"Failed to re-enable hardware discovery timeouts: {e}")
            raise
    
    def _disable_sensor_dependencies(self):
        """Remove camera/LiDAR dependency requirements"""
        try:
            # Set parameters to disable sensor dependency requirements
            self.set_parameters([
                rclpy.parameter.Parameter('camera_driver.required_for_operation', 
                                        rclpy.Parameter.Type.BOOL, False),
                rclpy.parameter.Parameter('lidar_driver.required_for_operation', 
                                        rclpy.Parameter.Type.BOOL, False),
                rclpy.parameter.Parameter('hardware_manager.camera_required', 
                                        rclpy.Parameter.Type.BOOL, False),
                rclpy.parameter.Parameter('hardware_manager.lidar_required', 
                                        rclpy.Parameter.Type.BOOL, False),
                rclpy.parameter.Parameter('safety_supervisor.require_laser_scan', 
                                        rclpy.Parameter.Type.BOOL, False),
                rclpy.parameter.Parameter('system.sensor_dependencies_bypassed', 
                                        rclpy.Parameter.Type.BOOL, True)
            ])
            
            # Send signals to components to operate without sensor dependencies
            sensor_bypass_msg = Bool()
            sensor_bypass_msg.data = True
            
            # Create publishers for sensor bypass if they don't exist
            if not hasattr(self, 'camera_bypass_pub'):
                self.camera_bypass_pub = self.create_publisher(
                    Bool, '/camera_driver/bypass_requirements', 10)
            if not hasattr(self, 'lidar_bypass_pub'):
                self.lidar_bypass_pub = self.create_publisher(
                    Bool, '/lidar_driver/bypass_requirements', 10)
            
            self.camera_bypass_pub.publish(sensor_bypass_msg)
            self.lidar_bypass_pub.publish(sensor_bypass_msg)
            
            # Update safety system states
            for sensor in ['camera_driver', 'lidar_driver']:
                if sensor in self.safety_systems:
                    self.safety_systems[sensor].state = SafetySystemState.BYPASSED
            
            self.get_logger().info("Disabled camera/LiDAR dependency requirements")
            
        except Exception as e:
            self.get_logger().error(f"Failed to disable sensor dependencies: {e}")
            raise
    
    def _enable_sensor_dependencies(self):
        """Re-enable camera/LiDAR dependency requirements"""
        try:
            # Reset parameter overrides
            self.set_parameters([
                rclpy.parameter.Parameter('camera_driver.required_for_operation', 
                                        rclpy.Parameter.Type.BOOL, True),
                rclpy.parameter.Parameter('lidar_driver.required_for_operation', 
                                        rclpy.Parameter.Type.BOOL, True),
                rclpy.parameter.Parameter('hardware_manager.camera_required', 
                                        rclpy.Parameter.Type.BOOL, True),
                rclpy.parameter.Parameter('hardware_manager.lidar_required', 
                                        rclpy.Parameter.Type.BOOL, True),
                rclpy.parameter.Parameter('safety_supervisor.require_laser_scan', 
                                        rclpy.Parameter.Type.BOOL, True),
                rclpy.parameter.Parameter('system.sensor_dependencies_bypassed', 
                                        rclpy.Parameter.Type.BOOL, False)
            ])
            
            # Send signals to re-enable sensor dependencies
            sensor_bypass_msg = Bool()
            sensor_bypass_msg.data = False
            
            if hasattr(self, 'camera_bypass_pub'):
                self.camera_bypass_pub.publish(sensor_bypass_msg)
            if hasattr(self, 'lidar_bypass_pub'):
                self.lidar_bypass_pub.publish(sensor_bypass_msg)
            
            # Update safety system states
            for sensor in ['camera_driver', 'lidar_driver']:
                if sensor in self.safety_systems:
                    self.safety_systems[sensor].state = SafetySystemState.ENABLED
            
            self.get_logger().info("Re-enabled camera/LiDAR dependency requirements")
            
        except Exception as e:
            self.get_logger().error(f"Failed to re-enable sensor dependencies: {e}")
            raise
    
    def disable_specific_safety_component(self, component_name: str, reason: str = "manual_override") -> bool:
        """
        Disable a specific safety component
        
        Args:
            component_name: Name of the safety component to disable
            reason: Reason for disabling the component
            
        Returns:
            True if component was successfully disabled
        """
        with self.override_lock:
            if component_name not in self.safety_systems:
                self.get_logger().error(f"Unknown safety component: {component_name}")
                return False
            
            try:
                system_info = self.safety_systems[component_name]
                
                if component_name == 'emergency_stop_handler':
                    self._disable_emergency_stop_handler()
                    system_info.state = SafetySystemState.EMERGENCY_ONLY
                elif component_name == 'safety_supervisor':
                    self._bypass_safety_supervisor()
                    system_info.state = SafetySystemState.DISABLED
                elif component_name == 'hardware_manager':
                    self._disable_hardware_discovery_timeouts()
                    system_info.state = SafetySystemState.DISABLED
                elif component_name in ['camera_driver', 'lidar_driver']:
                    self._disable_individual_sensor(component_name)
                    system_info.state = SafetySystemState.BYPASSED
                else:
                    # Generic component disabling
                    self._disable_generic_component(component_name)
                    system_info.state = SafetySystemState.DISABLED
                
                system_info.bypass_reason = reason
                system_info.bypass_timestamp = datetime.now()
                
                self.get_logger().info(f"Disabled safety component: {component_name}")
                return True
                
            except Exception as e:
                self.get_logger().error(f"Failed to disable safety component {component_name}: {e}")
                return False
    
    def enable_specific_safety_component(self, component_name: str) -> bool:
        """
        Re-enable a specific safety component
        
        Args:
            component_name: Name of the safety component to re-enable
            
        Returns:
            True if component was successfully re-enabled
        """
        with self.override_lock:
            if component_name not in self.safety_systems:
                self.get_logger().error(f"Unknown safety component: {component_name}")
                return False
            
            try:
                system_info = self.safety_systems[component_name]
                
                if component_name == 'emergency_stop_handler':
                    self._enable_emergency_stop_handler()
                elif component_name == 'safety_supervisor':
                    self._enable_safety_supervisor()
                elif component_name == 'hardware_manager':
                    self._enable_hardware_discovery_timeouts()
                elif component_name in ['camera_driver', 'lidar_driver']:
                    self._enable_individual_sensor(component_name)
                else:
                    # Generic component re-enabling
                    self._enable_generic_component(component_name)
                
                system_info.state = SafetySystemState.ENABLED
                system_info.bypass_reason = ""
                system_info.bypass_timestamp = None
                
                self.get_logger().info(f"Re-enabled safety component: {component_name}")
                return True
                
            except Exception as e:
                self.get_logger().error(f"Failed to re-enable safety component {component_name}: {e}")
                return False
    
    def _disable_individual_sensor(self, sensor_name: str):
        """Disable an individual sensor dependency"""
        try:
            param_name = f"{sensor_name}.required_for_operation"
            self.set_parameters([
                rclpy.parameter.Parameter(param_name, rclpy.Parameter.Type.BOOL, False)
            ])
            
            # Send bypass signal to specific sensor
            bypass_msg = Bool()
            bypass_msg.data = True
            
            if sensor_name == 'camera_driver':
                if not hasattr(self, 'camera_bypass_pub'):
                    self.camera_bypass_pub = self.create_publisher(
                        Bool, '/camera_driver/bypass_requirements', 10)
                self.camera_bypass_pub.publish(bypass_msg)
            elif sensor_name == 'lidar_driver':
                if not hasattr(self, 'lidar_bypass_pub'):
                    self.lidar_bypass_pub = self.create_publisher(
                        Bool, '/lidar_driver/bypass_requirements', 10)
                self.lidar_bypass_pub.publish(bypass_msg)
            
            self.get_logger().info(f"Disabled {sensor_name} dependency")
            
        except Exception as e:
            self.get_logger().error(f"Failed to disable {sensor_name}: {e}")
            raise
    
    def _enable_individual_sensor(self, sensor_name: str):
        """Re-enable an individual sensor dependency"""
        try:
            param_name = f"{sensor_name}.required_for_operation"
            self.set_parameters([
                rclpy.parameter.Parameter(param_name, rclpy.Parameter.Type.BOOL, True)
            ])
            
            # Send enable signal to specific sensor
            bypass_msg = Bool()
            bypass_msg.data = False
            
            if sensor_name == 'camera_driver' and hasattr(self, 'camera_bypass_pub'):
                self.camera_bypass_pub.publish(bypass_msg)
            elif sensor_name == 'lidar_driver' and hasattr(self, 'lidar_bypass_pub'):
                self.lidar_bypass_pub.publish(bypass_msg)
            
            self.get_logger().info(f"Re-enabled {sensor_name} dependency")
            
        except Exception as e:
            self.get_logger().error(f"Failed to re-enable {sensor_name}: {e}")
            raise
    
    def _disable_generic_component(self, component_name: str):
        """Disable a generic safety component"""
        try:
            # Set generic bypass parameters
            self.set_parameters([
                rclpy.parameter.Parameter(f"{component_name}.bypass_mode_active", 
                                        rclpy.Parameter.Type.BOOL, True),
                rclpy.parameter.Parameter(f"{component_name}.safety_disabled", 
                                        rclpy.Parameter.Type.BOOL, True)
            ])
            
            # Create and publish bypass signal
            if not hasattr(self, f'{component_name}_bypass_pub'):
                pub = self.create_publisher(Bool, f'/{component_name}/bypass_safety', 10)
                setattr(self, f'{component_name}_bypass_pub', pub)
            
            bypass_msg = Bool()
            bypass_msg.data = True
            getattr(self, f'{component_name}_bypass_pub').publish(bypass_msg)
            
            self.get_logger().info(f"Disabled generic safety component: {component_name}")
            
        except Exception as e:
            self.get_logger().error(f"Failed to disable generic component {component_name}: {e}")
            raise
    
    def _enable_generic_component(self, component_name: str):
        """Re-enable a generic safety component"""
        try:
            # Reset generic bypass parameters
            self.set_parameters([
                rclpy.parameter.Parameter(f"{component_name}.bypass_mode_active", 
                                        rclpy.Parameter.Type.BOOL, False),
                rclpy.parameter.Parameter(f"{component_name}.safety_disabled", 
                                        rclpy.Parameter.Type.BOOL, False)
            ])
            
            # Publish enable signal
            if hasattr(self, f'{component_name}_bypass_pub'):
                bypass_msg = Bool()
                bypass_msg.data = False
                getattr(self, f'{component_name}_bypass_pub').publish(bypass_msg)
            
            self.get_logger().info(f"Re-enabled generic safety component: {component_name}")
            
        except Exception as e:
            self.get_logger().error(f"Failed to re-enable generic component {component_name}: {e}")
            raise
    
    def enable_safety_systems_with_restart(self) -> bool:
        """
        Re-enable safety systems with individual component restart capability
        
        Returns:
            True if safety systems were successfully re-enabled
        """
        with self.override_lock:
            if not self.bypass_mode_active:
                self.get_logger().warn("Safety systems not currently disabled")
                return True
            
            try:
                self.get_logger().info("Re-enabling safety systems with restart capability")
                
                # Track individual component success
                component_results = {}
                
                # Re-enable each component individually with restart capability
                for system_name in self.safety_systems.keys():
                    component_results[system_name] = self._restart_and_enable_component(system_name)
                
                # Check overall success
                successful_components = sum(1 for success in component_results.values() if success)
                total_components = len(component_results)
                
                if successful_components >= total_components * 0.8:  # 80% success threshold
                    self.bypass_mode_active = False
                    
                    # Update successful component states
                    for system_name, success in component_results.items():
                        if success:
                            self.safety_systems[system_name].state = SafetySystemState.ENABLED
                            self.safety_systems[system_name].bypass_reason = ""
                            self.safety_systems[system_name].bypass_timestamp = None
                    
                    # Publish status updates
                    self._publish_override_status()
                    
                    bypass_msg = Bool()
                    bypass_msg.data = False
                    self.safety_bypass_pub.publish(bypass_msg)
                    
                    self.get_logger().info(f"Safety systems re-enabled: {successful_components}/{total_components} successful")
                    return True
                else:
                    self.get_logger().error(f"Failed to re-enable sufficient safety systems: {successful_components}/{total_components}")
                    return self._graceful_fallback_on_enable_failure()
                    
            except Exception as e:
                self.get_logger().error(f"Exception during safety system re-enabling: {e}")
                return self._graceful_fallback_on_enable_failure()
    
    def _restart_and_enable_component(self, component_name: str) -> bool:
        """
        Restart and re-enable a specific safety component
        
        Args:
            component_name: Name of the component to restart and enable
            
        Returns:
            True if component was successfully restarted and enabled
        """
        max_attempts = 3
        retry_delay = 2.0  # seconds
        
        for attempt in range(max_attempts):
            try:
                self.get_logger().info(f"Attempting to restart {component_name} (attempt {attempt + 1}/{max_attempts})")
                
                # First, ensure component is fully disabled
                self.disable_specific_safety_component(component_name, "restart_preparation")
                
                # Wait for clean shutdown
                time.sleep(retry_delay)
                
                # Attempt to re-enable
                if self.enable_specific_safety_component(component_name):
                    self.get_logger().info(f"Successfully restarted {component_name}")
                    return True
                else:
                    self.get_logger().warn(f"Failed to restart {component_name} on attempt {attempt + 1}")
                    
            except Exception as e:
                self.get_logger().error(f"Exception during {component_name} restart attempt {attempt + 1}: {e}")
            
            # Wait before next attempt (exponential backoff)
            if attempt < max_attempts - 1:
                wait_time = retry_delay * (2 ** attempt)
                self.get_logger().info(f"Waiting {wait_time}s before next restart attempt for {component_name}")
                time.sleep(wait_time)
        
        self.get_logger().error(f"Failed to restart {component_name} after {max_attempts} attempts")
        return False
    
    def _graceful_fallback_on_enable_failure(self) -> bool:
        """
        Implement graceful fallback if re-enabling safety systems fails
        
        Returns:
            True if fallback was successful, False if manual intervention required
        """
        try:
            self.get_logger().warn("Attempting graceful fallback after safety system enable failure")
            
            # Priority order for safety systems (most critical first)
            priority_systems = [
                'emergency_stop_handler',  # Most critical - must work
                'safety_supervisor',       # Second priority - velocity limiting
                'hardware_manager',        # Third priority - hardware monitoring
                'camera_driver',           # Lower priority - sensor
                'lidar_driver'            # Lower priority - sensor
            ]
            
            # Try to enable systems in priority order
            critical_success_count = 0
            total_critical = 2  # emergency_stop_handler and safety_supervisor are critical
            
            for system_name in priority_systems:
                if system_name not in self.safety_systems:
                    continue
                
                try:
                    success = self._attempt_single_component_recovery(system_name)
                    
                    if success:
                        self.safety_systems[system_name].state = SafetySystemState.ENABLED
                        self.safety_systems[system_name].bypass_reason = "fallback_recovery"
                        
                        # Count critical system successes
                        if system_name in ['emergency_stop_handler', 'safety_supervisor']:
                            critical_success_count += 1
                        
                        self.get_logger().info(f"Fallback recovery successful for {system_name}")
                    else:
                        self.safety_systems[system_name].state = SafetySystemState.FAILED
                        self.get_logger().error(f"Fallback recovery failed for {system_name}")
                        
                except Exception as e:
                    self.get_logger().error(f"Exception during fallback recovery for {system_name}: {e}")
                    self.safety_systems[system_name].state = SafetySystemState.FAILED
            
            # Determine if fallback was successful
            if critical_success_count >= total_critical:
                self.get_logger().info(f"Graceful fallback successful: {critical_success_count}/{total_critical} critical systems recovered")
                
                # Partial bypass mode - only critical systems enabled
                self.bypass_mode_active = False
                self._publish_override_status()
                
                return True
            else:
                self.get_logger().error(f"Graceful fallback failed: only {critical_success_count}/{total_critical} critical systems recovered")
                
                # Remain in bypass mode with error state
                self._publish_fallback_failure_status()
                
                return False
                
        except Exception as e:
            self.get_logger().error(f"Exception during graceful fallback: {e}")
            return False
    
    def _attempt_single_component_recovery(self, component_name: str) -> bool:
        """
        Attempt to recover a single component with minimal dependencies
        
        Args:
            component_name: Name of component to recover
            
        Returns:
            True if component recovery was successful
        """
        try:
            # Use basic recovery approach for each component type
            if component_name == 'emergency_stop_handler':
                # Emergency stop handler is most critical - try basic enable
                self._enable_emergency_stop_handler()
                return True
                
            elif component_name == 'safety_supervisor':
                # Safety supervisor - try to enable with reduced functionality
                self._enable_safety_supervisor()
                return True
                
            elif component_name == 'hardware_manager':
                # Hardware manager - enable with relaxed timeouts
                self._enable_hardware_discovery_timeouts()
                return True
                
            elif component_name in ['camera_driver', 'lidar_driver']:
                # Sensors - enable but mark as optional
                self._enable_individual_sensor(component_name)
                return True
                
            else:
                # Generic component - try basic enable
                self._enable_generic_component(component_name)
                return True
                
        except Exception as e:
            self.get_logger().error(f"Failed single component recovery for {component_name}: {e}")
            return False
    
    def _publish_fallback_failure_status(self):
        """Publish status indicating fallback failure and manual intervention needed"""
        status_data = {
            'bypass_mode_active': True,
            'fallback_failed': True,
            'manual_intervention_required': True,
            'emergency_stop_active': self.emergency_stop_active,
            'emergency_stop_preserved': self.emergency_stop_preserved,
            'critical_systems_failed': True,
            'safety_systems': {}
        }
        
        for name, info in self.safety_systems.items():
            status_data['safety_systems'][name] = {
                'state': info.state.value,
                'bypass_reason': info.bypass_reason,
                'requires_manual_intervention': info.state == SafetySystemState.FAILED
            }
        
        status_msg = String()
        status_msg.data = f"FALLBACK_FAILURE:{str(status_data)}"
        self.override_status_pub.publish(status_msg)
        
        self.get_logger().error("MANUAL INTERVENTION REQUIRED: Safety system fallback failed")
    
    def emergency_stop_trigger_callback(self, msg: Bool):
        """Handle emergency stop triggers (preserved even in bypass mode)"""
        if msg.data:
            with self.override_lock:
                self.emergency_stop_active = True
                
                # Publish emergency stop message
                emergency_msg = EmergencyStop()
                emergency_msg.active = True
                emergency_msg.reason = "Manual emergency stop trigger"
                emergency_msg.source = "safety_override_manager"
                emergency_msg.timestamp = self.get_clock().now().to_msg()
                self.emergency_stop_pub.publish(emergency_msg)
                
                self.get_logger().error("EMERGENCY STOP ACTIVATED (preserved in bypass mode)")
    
    def safety_reset_callback(self, msg: Bool):
        """Handle safety reset requests"""
        if msg.data:
            with self.override_lock:
                if self.emergency_stop_active:
                    self.emergency_stop_active = False
                    
                    # Publish emergency stop cleared message
                    emergency_msg = EmergencyStop()
                    emergency_msg.active = False
                    emergency_msg.reason = "Safety reset by operator"
                    emergency_msg.source = "safety_override_manager"
                    emergency_msg.timestamp = self.get_clock().now().to_msg()
                    self.emergency_stop_pub.publish(emergency_msg)
                    
                    self.get_logger().info("Emergency stop cleared by safety reset")
    
    def _monitor_bypass_timeout(self):
        """Monitor bypass mode timeout to prevent indefinite bypass"""
        if not self.bypass_mode_active:
            return
        
        with self.override_lock:
            # Check if any system has been bypassed for too long
            current_time = datetime.now()
            
            for system_info in self.safety_systems.values():
                if (system_info.bypass_timestamp and 
                    (current_time - system_info.bypass_timestamp).total_seconds() > self.bypass_timeout):
                    
                    self.get_logger().warn(
                        f"Bypass timeout reached for {system_info.name} "
                        f"({self.bypass_timeout}s), consider returning to normal mode"
                    )
    
    def _publish_override_status(self):
        """Publish current safety override status"""
        status_data = {
            'bypass_mode_active': self.bypass_mode_active,
            'emergency_stop_active': self.emergency_stop_active,
            'emergency_stop_preserved': self.emergency_stop_preserved,
            'safety_systems': {}
        }
        
        for name, info in self.safety_systems.items():
            status_data['safety_systems'][name] = {
                'state': info.state.value,
                'bypass_reason': info.bypass_reason,
                'bypass_timestamp': info.bypass_timestamp.isoformat() if info.bypass_timestamp else None,
                'emergency_stop_preserved': info.emergency_stop_preserved
            }
        
        status_msg = String()
        status_msg.data = str(status_data)
        self.override_status_pub.publish(status_msg)
    
    def get_override_status(self) -> Dict:
        """Get current safety override status"""
        with self.override_lock:
            return {
                'bypass_mode_active': self.bypass_mode_active,
                'emergency_stop_active': self.emergency_stop_active,
                'emergency_stop_preserved': self.emergency_stop_preserved,
                'safety_systems': {
                    name: {
                        'state': info.state.value,
                        'bypass_reason': info.bypass_reason,
                        'bypass_timestamp': info.bypass_timestamp.isoformat() if info.bypass_timestamp else None,
                        'emergency_stop_preserved': info.emergency_stop_preserved
                    }
                    for name, info in self.safety_systems.items()
                }
            }
    
    def is_bypass_mode_active(self) -> bool:
        """Check if bypass mode is currently active"""
        return self.bypass_mode_active
    
    def is_emergency_stop_preserved(self) -> bool:
        """Check if emergency stop functionality is preserved"""
        return self.emergency_stop_preserved


def main(args=None):
    rclpy.init(args=args)
    
    try:
        safety_override_manager = SafetyOverrideManager()
        rclpy.spin(safety_override_manager)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error in safety override manager: {e}")
    finally:
        if 'safety_override_manager' in locals():
            safety_override_manager.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()