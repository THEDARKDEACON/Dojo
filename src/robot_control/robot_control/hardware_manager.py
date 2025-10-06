#!/usr/bin/env python3
"""
Enhanced Hardware Manager for Dojo Robot

This module provides comprehensive hardware management with health monitoring,
automatic recovery procedures, and graceful degradation capabilities.
"""

import time
import threading
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import json

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import String, Bool
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from geometry_msgs.msg import Twist

from .device_abstraction import HardwareDevice, DeviceStatus, DeviceManager
from .hardware_discovery import HardwareDiscovery


class ComponentState(Enum):
    """Component lifecycle states"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    DEGRADED = "degraded"
    FAILED = "failed"
    RECOVERING = "recovering"
    SHUTDOWN = "shutdown"


class HealthLevel(Enum):
    """System health levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"


class RecoveryStrategy(Enum):
    """Recovery strategy types"""
    RESTART_COMPONENT = "restart_component"
    RECONNECT_DEVICE = "reconnect_device"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    SYSTEM_RESTART = "system_restart"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class HealthMetrics:
    """Health metrics for a component"""
    component_name: str
    state: ComponentState
    health_level: HealthLevel
    uptime: timedelta = field(default_factory=lambda: timedelta(0))
    error_count: int = 0
    last_error: Optional[str] = None
    last_successful_operation: datetime = field(default_factory=datetime.now)
    recovery_attempts: int = 0
    performance_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class RecoveryProcedure:
    """Recovery procedure definition"""
    name: str
    strategy: RecoveryStrategy
    component_types: List[str]
    max_attempts: int = 3
    cooldown_period: float = 30.0  # seconds
    procedure_func: Optional[Callable] = None
    prerequisites: List[str] = field(default_factory=list)


@dataclass
class DegradationRule:
    """Graceful degradation rule"""
    trigger_condition: str  # Component or condition that triggers degradation
    affected_components: List[str]  # Components to disable/modify
    fallback_behavior: str  # Description of fallback behavior
    severity_threshold: HealthLevel  # Minimum severity to trigger
    recovery_condition: str  # Condition for automatic recovery


class EnhancedHardwareManager(Node):
    """
    Enhanced Hardware Manager with comprehensive health monitoring and recovery
    
    Provides:
    - Component lifecycle management
    - Health monitoring with metrics collection
    - Automatic recovery procedures
    - Graceful degradation strategies
    - Diagnostic reporting
    """
    
    def __init__(self):
        super().__init__('enhanced_hardware_manager')
        
        self.logger = self.get_logger()
        
        # Component management
        self.components: Dict[str, HardwareDevice] = {}
        self.component_metrics: Dict[str, HealthMetrics] = {}
        self.component_states: Dict[str, ComponentState] = {}
        
        # Health monitoring
        self.system_health = HealthLevel.HEALTHY
        self.monitoring_active = False
        self.monitor_thread = None
        self.health_check_interval = 1.0  # seconds
        
        # Recovery management
        self.recovery_procedures: Dict[str, RecoveryProcedure] = {}
        self.active_recoveries: Dict[str, datetime] = {}
        self.recovery_history: List[Dict] = []
        
        # Degradation management
        self.degradation_rules: List[DegradationRule] = []
        self.active_degradations: Set[str] = set()
        self.degraded_components: Set[str] = set()
        
        # Configuration
        self.declare_parameter('health_check_interval', 1.0)
        self.declare_parameter('max_recovery_attempts', 3)
        self.declare_parameter('recovery_cooldown', 30.0)
        self.declare_parameter('enable_auto_recovery', True)
        self.declare_parameter('enable_graceful_degradation', True)
        
        self.health_check_interval = self.get_parameter('health_check_interval').value
        self.max_recovery_attempts = self.get_parameter('max_recovery_attempts').value
        self.recovery_cooldown = self.get_parameter('recovery_cooldown').value
        self.enable_auto_recovery = self.get_parameter('enable_auto_recovery').value
        self.enable_graceful_degradation = self.get_parameter('enable_graceful_degradation').value
        
        # Publishers
        self.health_pub = self.create_publisher(
            DiagnosticArray,
            '/diagnostics/hardware_health',
            10
        )
        
        self.system_status_pub = self.create_publisher(
            String,
            '/system/health_status',
            10
        )
        
        self.degradation_status_pub = self.create_publisher(
            String,
            '/system/degradation_status',
            10
        )
        
        # Subscribers
        self.emergency_stop_sub = self.create_subscription(
            Bool,
            '/emergency_stop',
            self._on_emergency_stop,
            10
        )
        
        # Timers
        self.health_timer = self.create_timer(2.0, self._publish_health_diagnostics)
        self.metrics_timer = self.create_timer(5.0, self._update_performance_metrics)
        
        # Initialize recovery procedures and degradation rules
        self._initialize_recovery_procedures()
        self._initialize_degradation_rules()
        
        # Start health monitoring
        self.start_health_monitoring()
        
        self.logger.info("Enhanced Hardware Manager initialized")
    
    def register_component(self, component: HardwareDevice) -> bool:
        """
        Register a hardware component with the manager
        
        Args:
            component: Hardware device to register
            
        Returns:
            True if registration successful, False otherwise
        """
        if component.name in self.components:
            self.logger.warning(f"Component {component.name} already registered")
            return False
        
        # Register component
        self.components[component.name] = component
        self.component_states[component.name] = ComponentState.UNINITIALIZED
        
        # Initialize health metrics
        self.component_metrics[component.name] = HealthMetrics(
            component_name=component.name,
            state=ComponentState.UNINITIALIZED,
            health_level=HealthLevel.HEALTHY
        )
        
        # Add status callback to monitor component
        component.add_status_callback(
            lambda status: self._on_component_status_change(component.name, status)
        )
        
        self.logger.info(f"Registered component: {component.name}")
        return True
    
    def unregister_component(self, name: str) -> bool:
        """
        Unregister a hardware component
        
        Args:
            name: Name of component to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        if name not in self.components:
            self.logger.warning(f"Component {name} not registered")
            return False
        
        # Stop any active recovery
        if name in self.active_recoveries:
            del self.active_recoveries[name]
        
        # Remove from degraded components
        self.degraded_components.discard(name)
        
        # Disconnect and remove
        component = self.components[name]
        component.disconnect()
        
        del self.components[name]
        del self.component_states[name]
        del self.component_metrics[name]
        
        self.logger.info(f"Unregistered component: {name}")
        return True
    
    def initialize_component(self, name: str) -> bool:
        """
        Initialize a specific component
        
        Args:
            name: Name of component to initialize
            
        Returns:
            True if initialization successful, False otherwise
        """
        if name not in self.components:
            self.logger.error(f"Component {name} not registered")
            return False
        
        component = self.components[name]
        metrics = self.component_metrics[name]
        
        # Update state
        self._update_component_state(name, ComponentState.INITIALIZING)
        
        try:
            # Attempt to connect
            if component.connect():
                self._update_component_state(name, ComponentState.ACTIVE)
                metrics.health_level = HealthLevel.HEALTHY
                metrics.last_successful_operation = datetime.now()
                self.logger.info(f"Successfully initialized component: {name}")
                return True
            else:
                self._update_component_state(name, ComponentState.FAILED)
                metrics.health_level = HealthLevel.FAILED
                metrics.error_count += 1
                metrics.last_error = "Initialization failed"
                self.logger.error(f"Failed to initialize component: {name}")
                
                # Trigger recovery if enabled
                if self.enable_auto_recovery:
                    self._trigger_recovery(name, "initialization_failed")
                
                return False
                
        except Exception as e:
            self._update_component_state(name, ComponentState.FAILED)
            metrics.health_level = HealthLevel.FAILED
            metrics.error_count += 1
            metrics.last_error = str(e)
            self.logger.error(f"Exception during component initialization {name}: {e}")
            return False
    
    def initialize_all_components(self) -> Dict[str, bool]:
        """
        Initialize all registered components
        
        Returns:
            Dictionary mapping component names to initialization success
        """
        results = {}
        
        for name in self.components.keys():
            results[name] = self.initialize_component(name)
        
        # Update system health
        self._update_system_health()
        
        return results
    
    def shutdown_component(self, name: str) -> bool:
        """
        Gracefully shutdown a component
        
        Args:
            name: Name of component to shutdown
            
        Returns:
            True if shutdown successful, False otherwise
        """
        if name not in self.components:
            self.logger.error(f"Component {name} not registered")
            return False
        
        component = self.components[name]
        
        try:
            # Update state
            self._update_component_state(name, ComponentState.SHUTDOWN)
            
            # Disconnect component
            component.disconnect()
            
            self.logger.info(f"Successfully shutdown component: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error shutting down component {name}: {e}")
            return False
    
    def shutdown_all_components(self):
        """Gracefully shutdown all components"""
        for name in list(self.components.keys()):
            self.shutdown_component(name)
    
    def get_component_health(self, name: str) -> Optional[HealthMetrics]:
        """Get health metrics for a specific component"""
        return self.component_metrics.get(name)
    
    def get_system_health(self) -> HealthLevel:
        """Get overall system health level"""
        return self.system_health
    
    def get_component_state(self, name: str) -> Optional[ComponentState]:
        """Get current state of a component"""
        return self.component_states.get(name)
    
    def start_health_monitoring(self):
        """Start continuous health monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._health_monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("Started health monitoring")
    
    def stop_health_monitoring(self):
        """Stop health monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        
        self.logger.info("Stopped health monitoring")
    
    def _health_monitoring_loop(self):
        """Main health monitoring loop"""
        while self.monitoring_active:
            try:
                # Check health of all components
                for name, component in self.components.items():
                    self._check_component_health(name, component)
                
                # Update system health
                self._update_system_health()
                
                # Check for recovery opportunities
                self._check_recovery_opportunities()
                
                # Check degradation conditions
                if self.enable_graceful_degradation:
                    self._check_degradation_conditions()
                
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(self.health_check_interval)
    
    def _check_component_health(self, name: str, component: HardwareDevice):
        """Check health of a specific component"""
        metrics = self.component_metrics[name]
        current_state = self.component_states[name]
        
        # Skip if component is shutdown or uninitialized
        if current_state in [ComponentState.SHUTDOWN, ComponentState.UNINITIALIZED]:
            return
        
        try:
            # Get device diagnostics
            device_diagnostics = component.get_diagnostics()
            
            # Update metrics based on device status
            if component.health.status == DeviceStatus.CONNECTED:
                if current_state != ComponentState.ACTIVE:
                    self._update_component_state(name, ComponentState.ACTIVE)
                
                metrics.health_level = HealthLevel.HEALTHY
                metrics.last_successful_operation = datetime.now()
                
            elif component.health.status == DeviceStatus.RECONNECTING:
                if current_state != ComponentState.RECOVERING:
                    self._update_component_state(name, ComponentState.RECOVERING)
                
                metrics.health_level = HealthLevel.WARNING
                
            elif component.health.status in [DeviceStatus.ERROR, DeviceStatus.DISCONNECTED]:
                if current_state not in [ComponentState.FAILED, ComponentState.RECOVERING]:
                    self._update_component_state(name, ComponentState.FAILED)
                
                metrics.health_level = HealthLevel.CRITICAL
                metrics.error_count += 1
                metrics.last_error = component.health.last_error or "Communication error"
                
                # Trigger recovery if not already active
                if (self.enable_auto_recovery and 
                    name not in self.active_recoveries and
                    metrics.recovery_attempts < self.max_recovery_attempts):
                    self._trigger_recovery(name, "health_check_failed")
            
            # Update performance metrics
            self._update_component_performance_metrics(name, component)
            
        except Exception as e:
            self.logger.error(f"Error checking health for component {name}: {e}")
            metrics.error_count += 1
            metrics.last_error = str(e)    

    def _update_component_performance_metrics(self, name: str, component: HardwareDevice):
        """Update performance metrics for a component"""
        metrics = self.component_metrics[name]
        
        # Calculate uptime
        if component.health.status == DeviceStatus.CONNECTED:
            # This is simplified - in reality you'd track connection start time
            metrics.uptime = datetime.now() - metrics.last_successful_operation
        
        # Add component-specific metrics
        metrics.performance_metrics['error_rate'] = (
            metrics.error_count / max(1, (datetime.now() - metrics.last_successful_operation).total_seconds() / 3600)
        )
        
        # Add device-specific performance metrics
        if hasattr(component, 'health'):
            metrics.performance_metrics['reconnect_attempts'] = component.health.reconnect_attempts
            
            # Calculate communication latency if available
            time_since_last_comm = (datetime.now() - component.health.last_communication).total_seconds()
            metrics.performance_metrics['last_communication_age'] = time_since_last_comm
    
    def _update_component_state(self, name: str, new_state: ComponentState):
        """Update component state and log changes"""
        old_state = self.component_states.get(name, ComponentState.UNINITIALIZED)
        
        if old_state != new_state:
            self.component_states[name] = new_state
            self.component_metrics[name].state = new_state
            
            self.logger.info(f"Component {name} state changed: {old_state.value} -> {new_state.value}")
            
            # Publish state change
            self._publish_component_state_change(name, old_state, new_state)
    
    def _update_system_health(self):
        """Update overall system health based on component states"""
        if not self.component_metrics:
            self.system_health = HealthLevel.HEALTHY
            return
        
        # Count components by health level
        health_counts = {level: 0 for level in HealthLevel}
        
        for metrics in self.component_metrics.values():
            health_counts[metrics.health_level] += 1
        
        total_components = len(self.component_metrics)
        
        # Determine system health
        if health_counts[HealthLevel.FAILED] > 0:
            if health_counts[HealthLevel.FAILED] >= total_components * 0.5:
                new_health = HealthLevel.FAILED
            else:
                new_health = HealthLevel.CRITICAL
        elif health_counts[HealthLevel.CRITICAL] > 0:
            new_health = HealthLevel.CRITICAL
        elif health_counts[HealthLevel.WARNING] > 0:
            new_health = HealthLevel.WARNING
        else:
            new_health = HealthLevel.HEALTHY
        
        if self.system_health != new_health:
            old_health = self.system_health
            self.system_health = new_health
            self.logger.info(f"System health changed: {old_health.value} -> {new_health.value}")
            
            # Publish system health change
            self._publish_system_health_change(old_health, new_health)
    
    def _on_component_status_change(self, component_name: str, status: DeviceStatus):
        """Handle component status changes from device abstraction layer"""
        self.logger.debug(f"Component {component_name} device status changed to {status.value}")
        
        # The health monitoring loop will pick up this change
        # This callback is mainly for immediate notifications
    
    def _on_emergency_stop(self, msg: Bool):
        """Handle emergency stop signal"""
        if msg.data:
            self.logger.warning("Emergency stop activated - shutting down all components")
            self.shutdown_all_components()
        else:
            self.logger.info("Emergency stop cleared - components can be reinitialized")
    
    def _trigger_recovery(self, component_name: str, reason: str):
        """
        Trigger recovery procedure for a component
        
        Args:
            component_name: Name of component to recover
            reason: Reason for triggering recovery
        """
        if component_name in self.active_recoveries:
            # Check cooldown period
            last_recovery = self.active_recoveries[component_name]
            if (datetime.now() - last_recovery).total_seconds() < self.recovery_cooldown:
                self.logger.debug(f"Recovery for {component_name} still in cooldown period")
                return
        
        metrics = self.component_metrics.get(component_name)
        if not metrics:
            return
        
        if metrics.recovery_attempts >= self.max_recovery_attempts:
            self.logger.warning(f"Max recovery attempts reached for {component_name}")
            return
        
        self.logger.info(f"Triggering recovery for {component_name}, reason: {reason}")
        
        # Mark recovery as active
        self.active_recoveries[component_name] = datetime.now()
        metrics.recovery_attempts += 1
        
        # Find appropriate recovery procedure
        recovery_procedure = self._find_recovery_procedure(component_name, reason)
        
        if recovery_procedure:
            # Execute recovery in separate thread
            recovery_thread = threading.Thread(
                target=self._execute_recovery,
                args=(component_name, recovery_procedure, reason),
                daemon=True
            )
            recovery_thread.start()
        else:
            self.logger.warning(f"No recovery procedure found for {component_name}")
            # Remove from active recoveries
            if component_name in self.active_recoveries:
                del self.active_recoveries[component_name]
    
    def _find_recovery_procedure(self, component_name: str, reason: str) -> Optional[RecoveryProcedure]:
        """Find appropriate recovery procedure for a component"""
        component = self.components.get(component_name)
        if not component:
            return None
        
        # Get component type from device
        component_type = getattr(component, 'device_type', component.__class__.__name__.lower())
        
        # Find matching recovery procedures
        for procedure in self.recovery_procedures.values():
            if component_type in procedure.component_types or 'all' in procedure.component_types:
                return procedure
        
        # Return default recovery procedure
        return self.recovery_procedures.get('default_reconnect')
    
    def _execute_recovery(self, component_name: str, procedure: RecoveryProcedure, reason: str):
        """
        Execute recovery procedure for a component
        
        Args:
            component_name: Name of component to recover
            procedure: Recovery procedure to execute
            reason: Reason for recovery
        """
        try:
            self.logger.info(f"Executing recovery procedure '{procedure.name}' for {component_name}")
            
            # Update component state
            self._update_component_state(component_name, ComponentState.RECOVERING)
            
            # Execute recovery based on strategy
            success = False
            
            if procedure.strategy == RecoveryStrategy.RESTART_COMPONENT:
                success = self._recovery_restart_component(component_name)
            elif procedure.strategy == RecoveryStrategy.RECONNECT_DEVICE:
                success = self._recovery_reconnect_device(component_name)
            elif procedure.strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                success = self._recovery_graceful_degradation(component_name)
            elif procedure.procedure_func:
                success = procedure.procedure_func(component_name)
            
            # Record recovery attempt
            recovery_record = {
                'timestamp': datetime.now().isoformat(),
                'component': component_name,
                'procedure': procedure.name,
                'reason': reason,
                'success': success
            }
            self.recovery_history.append(recovery_record)
            
            # Keep only last 100 recovery records
            if len(self.recovery_history) > 100:
                self.recovery_history = self.recovery_history[-100:]
            
            if success:
                self.logger.info(f"Recovery successful for {component_name}")
                self._update_component_state(component_name, ComponentState.ACTIVE)
                
                # Reset error metrics
                metrics = self.component_metrics[component_name]
                metrics.health_level = HealthLevel.HEALTHY
                metrics.last_successful_operation = datetime.now()
            else:
                self.logger.warning(f"Recovery failed for {component_name}")
                self._update_component_state(component_name, ComponentState.FAILED)
                
                # Consider graceful degradation if recovery failed
                if self.enable_graceful_degradation:
                    self._consider_degradation(component_name)
            
        except Exception as e:
            self.logger.error(f"Exception during recovery for {component_name}: {e}")
            self._update_component_state(component_name, ComponentState.FAILED)
        
        finally:
            # Remove from active recoveries
            if component_name in self.active_recoveries:
                del self.active_recoveries[component_name]
    
    def _recovery_restart_component(self, component_name: str) -> bool:
        """Restart component recovery strategy"""
        try:
            # Shutdown and reinitialize
            self.shutdown_component(component_name)
            time.sleep(2.0)  # Wait for clean shutdown
            return self.initialize_component(component_name)
        except Exception as e:
            self.logger.error(f"Error in restart recovery for {component_name}: {e}")
            return False
    
    def _recovery_reconnect_device(self, component_name: str) -> bool:
        """Reconnect device recovery strategy"""
        component = self.components.get(component_name)
        if not component:
            return False
        
        try:
            # Disconnect and reconnect
            component.disconnect()
            time.sleep(1.0)
            return component.connect()
        except Exception as e:
            self.logger.error(f"Error in reconnect recovery for {component_name}: {e}")
            return False
    
    def _recovery_graceful_degradation(self, component_name: str) -> bool:
        """Graceful degradation recovery strategy"""
        try:
            # Mark component as degraded but operational
            self.degraded_components.add(component_name)
            self._update_component_state(component_name, ComponentState.DEGRADED)
            
            # Apply degradation rules
            self._apply_degradation_rules(component_name)
            
            return True
        except Exception as e:
            self.logger.error(f"Error in degradation recovery for {component_name}: {e}")
            return False
    
    def _check_recovery_opportunities(self):
        """Check for components that might be ready for recovery"""
        current_time = datetime.now()
        
        for name, component in self.components.items():
            metrics = self.component_metrics[name]
            
            # Skip if component is not in a failed state
            if metrics.state not in [ComponentState.FAILED, ComponentState.DEGRADED]:
                continue
            
            # Skip if recovery is active or in cooldown
            if name in self.active_recoveries:
                continue
            
            # Check if enough time has passed since last recovery attempt
            if metrics.recovery_attempts > 0:
                # Exponential backoff for recovery attempts
                backoff_time = self.recovery_cooldown * (2 ** (metrics.recovery_attempts - 1))
                if (current_time - metrics.last_successful_operation).total_seconds() < backoff_time:
                    continue
            
            # Check if component might be available again
            if component.health.status == DeviceStatus.CONNECTED:
                self.logger.info(f"Component {name} appears to be available again, attempting recovery")
                self._trigger_recovery(name, "automatic_recovery_check")
    
    def _initialize_recovery_procedures(self):
        """Initialize default recovery procedures"""
        # Default reconnect procedure
        self.recovery_procedures['default_reconnect'] = RecoveryProcedure(
            name="Default Reconnect",
            strategy=RecoveryStrategy.RECONNECT_DEVICE,
            component_types=['all'],
            max_attempts=3,
            cooldown_period=30.0
        )
        
        # Arduino-specific recovery
        self.recovery_procedures['arduino_restart'] = RecoveryProcedure(
            name="Arduino Restart",
            strategy=RecoveryStrategy.RESTART_COMPONENT,
            component_types=['arduino', 'arduinodevice'],
            max_attempts=5,
            cooldown_period=15.0
        )
        
        # Camera-specific recovery
        self.recovery_procedures['camera_reconnect'] = RecoveryProcedure(
            name="Camera Reconnect",
            strategy=RecoveryStrategy.RECONNECT_DEVICE,
            component_types=['camera', 'cameradevice'],
            max_attempts=3,
            cooldown_period=20.0
        )
        
        # LiDAR-specific recovery
        self.recovery_procedures['lidar_restart'] = RecoveryProcedure(
            name="LiDAR Restart",
            strategy=RecoveryStrategy.RESTART_COMPONENT,
            component_types=['lidar', 'lidardevice'],
            max_attempts=3,
            cooldown_period=25.0
        )
        
        # Graceful degradation procedure
        self.recovery_procedures['graceful_degradation'] = RecoveryProcedure(
            name="Graceful Degradation",
            strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
            component_types=['all'],
            max_attempts=1,
            cooldown_period=60.0
        )
    
    def _initialize_degradation_rules(self):
        """Initialize graceful degradation rules"""
        # Camera failure - continue with basic navigation
        self.degradation_rules.append(DegradationRule(
            trigger_condition="camera_failed",
            affected_components=["vision_system", "object_detection"],
            fallback_behavior="Disable vision-based navigation, use LiDAR only",
            severity_threshold=HealthLevel.CRITICAL,
            recovery_condition="camera_restored"
        ))
        
        # LiDAR failure - reduce navigation capabilities
        self.degradation_rules.append(DegradationRule(
            trigger_condition="lidar_failed",
            affected_components=["slam", "navigation", "obstacle_avoidance"],
            fallback_behavior="Disable autonomous navigation, manual control only",
            severity_threshold=HealthLevel.CRITICAL,
            recovery_condition="lidar_restored"
        ))
        
        # Arduino failure - emergency stop
        self.degradation_rules.append(DegradationRule(
            trigger_condition="arduino_failed",
            affected_components=["motor_control", "encoder_feedback"],
            fallback_behavior="Emergency stop, no motor control",
            severity_threshold=HealthLevel.CRITICAL,
            recovery_condition="arduino_restored"
        ))
    
    def _check_degradation_conditions(self):
        """Check if any degradation rules should be triggered"""
        for rule in self.degradation_rules:
            if rule.trigger_condition not in self.active_degradations:
                if self._should_trigger_degradation(rule):
                    self._trigger_degradation(rule)
            else:
                if self._should_recover_from_degradation(rule):
                    self._recover_from_degradation(rule)
    
    def _should_trigger_degradation(self, rule: DegradationRule) -> bool:
        """Check if a degradation rule should be triggered"""
        # Parse trigger condition (simplified)
        if "camera" in rule.trigger_condition:
            camera_components = [name for name, comp in self.components.items() 
                               if 'camera' in name.lower()]
            return any(self.component_metrics[name].health_level >= rule.severity_threshold 
                      for name in camera_components if name in self.component_metrics)
        
        elif "lidar" in rule.trigger_condition:
            lidar_components = [name for name, comp in self.components.items() 
                              if 'lidar' in name.lower()]
            return any(self.component_metrics[name].health_level >= rule.severity_threshold 
                      for name in lidar_components if name in self.component_metrics)
        
        elif "arduino" in rule.trigger_condition:
            arduino_components = [name for name, comp in self.components.items() 
                                if 'arduino' in name.lower()]
            return any(self.component_metrics[name].health_level >= rule.severity_threshold 
                      for name in arduino_components if name in self.component_metrics)
        
        return False
    
    def _should_recover_from_degradation(self, rule: DegradationRule) -> bool:
        """Check if recovery from degradation is possible"""
        # Parse recovery condition (simplified)
        if "camera" in rule.recovery_condition:
            camera_components = [name for name, comp in self.components.items() 
                               if 'camera' in name.lower()]
            return all(self.component_metrics[name].health_level == HealthLevel.HEALTHY 
                      for name in camera_components if name in self.component_metrics)
        
        elif "lidar" in rule.recovery_condition:
            lidar_components = [name for name, comp in self.components.items() 
                              if 'lidar' in name.lower()]
            return all(self.component_metrics[name].health_level == HealthLevel.HEALTHY 
                      for name in lidar_components if name in self.component_metrics)
        
        elif "arduino" in rule.recovery_condition:
            arduino_components = [name for name, comp in self.components.items() 
                                if 'arduino' in name.lower()]
            return all(self.component_metrics[name].health_level == HealthLevel.HEALTHY 
                      for name in arduino_components if name in self.component_metrics)
        
        return False
    
    def _trigger_degradation(self, rule: DegradationRule):
        """Trigger a degradation rule"""
        self.logger.warning(f"Triggering degradation: {rule.trigger_condition}")
        self.active_degradations.add(rule.trigger_condition)
        
        # Apply degradation to affected components
        self._apply_degradation_rules(rule.trigger_condition)
        
        # Publish degradation status
        self._publish_degradation_status(rule, True)
    
    def _recover_from_degradation(self, rule: DegradationRule):
        """Recover from a degradation rule"""
        self.logger.info(f"Recovering from degradation: {rule.trigger_condition}")
        self.active_degradations.discard(rule.trigger_condition)
        
        # Remove degradation from affected components
        self._remove_degradation_rules(rule.trigger_condition)
        
        # Publish degradation status
        self._publish_degradation_status(rule, False)
    
    def _apply_degradation_rules(self, trigger_condition: str):
        """Apply degradation rules for a specific trigger"""
        for rule in self.degradation_rules:
            if rule.trigger_condition == trigger_condition:
                for component_name in rule.affected_components:
                    self.degraded_components.add(component_name)
                    self.logger.info(f"Applied degradation to {component_name}: {rule.fallback_behavior}")
    
    def _remove_degradation_rules(self, trigger_condition: str):
        """Remove degradation rules for a specific trigger"""
        for rule in self.degradation_rules:
            if rule.trigger_condition == trigger_condition:
                for component_name in rule.affected_components:
                    self.degraded_components.discard(component_name)
                    self.logger.info(f"Removed degradation from {component_name}")
    
    def _consider_degradation(self, component_name: str):
        """Consider applying graceful degradation for a failed component"""
        # This would trigger appropriate degradation rules based on the failed component
        pass
    
    def _publish_health_diagnostics(self):
        """Publish comprehensive health diagnostics"""
        msg = DiagnosticArray()
        msg.header.stamp = self.get_clock().now().to_msg()
        
        # System-level status
        system_status = DiagnosticStatus()
        system_status.name = "hardware_manager/system_health"
        system_status.hardware_id = "system"
        
        if self.system_health == HealthLevel.HEALTHY:
            system_status.level = DiagnosticStatus.OK
            system_status.message = "System healthy"
        elif self.system_health == HealthLevel.WARNING:
            system_status.level = DiagnosticStatus.WARN
            system_status.message = "System has warnings"
        elif self.system_health == HealthLevel.CRITICAL:
            system_status.level = DiagnosticStatus.ERROR
            system_status.message = "System has critical issues"
        else:
            system_status.level = DiagnosticStatus.STALE
            system_status.message = "System failed"
        
        system_status.values.append(KeyValue(key="system_health", value=self.system_health.value))
        system_status.values.append(KeyValue(key="total_components", value=str(len(self.components))))
        system_status.values.append(KeyValue(key="active_recoveries", value=str(len(self.active_recoveries))))
        system_status.values.append(KeyValue(key="degraded_components", value=str(len(self.degraded_components))))
        
        msg.status.append(system_status)
        
        # Component-level status
        for name, metrics in self.component_metrics.items():
            status = DiagnosticStatus()
            status.name = f"hardware_manager/{name}"
            status.hardware_id = name
            
            if metrics.health_level == HealthLevel.HEALTHY:
                status.level = DiagnosticStatus.OK
                status.message = f"Component {name} healthy"
            elif metrics.health_level == HealthLevel.WARNING:
                status.level = DiagnosticStatus.WARN
                status.message = f"Component {name} has warnings"
            elif metrics.health_level == HealthLevel.CRITICAL:
                status.level = DiagnosticStatus.ERROR
                status.message = f"Component {name} has critical issues"
            else:
                status.level = DiagnosticStatus.STALE
                status.message = f"Component {name} failed"
            
            # Add component metrics
            status.values.append(KeyValue(key="state", value=metrics.state.value))
            status.values.append(KeyValue(key="health_level", value=metrics.health_level.value))
            status.values.append(KeyValue(key="error_count", value=str(metrics.error_count)))
            status.values.append(KeyValue(key="recovery_attempts", value=str(metrics.recovery_attempts)))
            status.values.append(KeyValue(key="uptime_hours", value=f"{metrics.uptime.total_seconds() / 3600:.2f}"))
            
            if metrics.last_error:
                status.values.append(KeyValue(key="last_error", value=metrics.last_error))
            
            # Add performance metrics
            for metric_name, metric_value in metrics.performance_metrics.items():
                status.values.append(KeyValue(key=f"perf_{metric_name}", value=str(metric_value)))
            
            msg.status.append(status)
        
        self.health_pub.publish(msg)
    
    def _update_performance_metrics(self):
        """Update performance metrics for all components"""
        for name, component in self.components.items():
            if name in self.component_metrics:
                self._update_component_performance_metrics(name, component)
    
    def _publish_component_state_change(self, name: str, old_state: ComponentState, new_state: ComponentState):
        """Publish component state change notification"""
        msg = String()
        msg.data = json.dumps({
            'component': name,
            'old_state': old_state.value,
            'new_state': new_state.value,
            'timestamp': datetime.now().isoformat()
        })
        # Would publish to a state change topic if needed
    
    def _publish_system_health_change(self, old_health: HealthLevel, new_health: HealthLevel):
        """Publish system health change notification"""
        msg = String()
        msg.data = json.dumps({
            'old_health': old_health.value,
            'new_health': new_health.value,
            'timestamp': datetime.now().isoformat(),
            'active_degradations': list(self.active_degradations)
        })
        self.system_status_pub.publish(msg)
    
    def _publish_degradation_status(self, rule: DegradationRule, activated: bool):
        """Publish degradation status change"""
        msg = String()
        msg.data = json.dumps({
            'rule': rule.trigger_condition,
            'activated': activated,
            'affected_components': rule.affected_components,
            'fallback_behavior': rule.fallback_behavior,
            'timestamp': datetime.now().isoformat()
        })
        self.degradation_status_pub.publish(msg)
    
    def get_recovery_history(self) -> List[Dict]:
        """Get recovery attempt history"""
        return self.recovery_history.copy()
    
    def get_active_degradations(self) -> Set[str]:
        """Get currently active degradations"""
        return self.active_degradations.copy()
    
    def get_degraded_components(self) -> Set[str]:
        """Get currently degraded components"""
        return self.degraded_components.copy()
    
    def force_recovery(self, component_name: str, reason: str = "manual_trigger") -> bool:
        """
        Manually trigger recovery for a component
        
        Args:
            component_name: Name of component to recover
            reason: Reason for manual recovery
            
        Returns:
            True if recovery was triggered, False otherwise
        """
        if component_name not in self.components:
            self.logger.error(f"Component {component_name} not registered")
            return False
        
        self.logger.info(f"Manual recovery triggered for {component_name}")
        self._trigger_recovery(component_name, reason)
        return True
    
    def destroy_node(self):
        """Clean shutdown of hardware manager"""
        self.logger.info("Shutting down Enhanced Hardware Manager")
        
        # Stop monitoring
        self.stop_health_monitoring()
        
        # Shutdown all components
        self.shutdown_all_components()
        
        super().destroy_node()


def main(args=None):
    """Main entry point for enhanced hardware manager"""
    rclpy.init(args=args)
    
    try:
        hardware_manager = EnhancedHardwareManager()
        rclpy.spin(hardware_manager)
    except KeyboardInterrupt:
        pass
    finally:
        if 'hardware_manager' in locals():
            hardware_manager.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()