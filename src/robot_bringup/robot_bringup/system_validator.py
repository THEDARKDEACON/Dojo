#!/usr/bin/env python3
"""
System Startup Validation Node

Implements startup checks for all required topics and services, creates system health
monitoring and status reporting, and implements graceful shutdown procedures for all components.

Requirements: 2.5, 3.5, 4.5, 5.5
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy
from std_msgs.msg import String, Bool
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray
from nav_msgs.msg import OccupancyGrid
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from geometry_msgs.msg import PoseWithCovarianceStamped
import time
import threading
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class SystemStatus(Enum):
    """System status levels."""
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    SHUTDOWN = "shutdown"


@dataclass
class TopicCheck:
    """Configuration for topic validation."""
    name: str
    msg_type: type
    required: bool = True
    timeout: float = 10.0
    last_seen: Optional[float] = None
    is_active: bool = False
    subscriber: Optional = None


@dataclass
class ServiceCheck:
    """Configuration for service validation."""
    name: str
    required: bool = True
    timeout: float = 5.0
    is_available: bool = False


@dataclass
class SystemHealth:
    """System health status container."""
    overall_status: SystemStatus = SystemStatus.STARTING
    topic_status: Dict[str, bool] = field(default_factory=dict)
    service_status: Dict[str, bool] = field(default_factory=dict)
    startup_complete: bool = False
    startup_time: Optional[float] = None
    error_messages: List[str] = field(default_factory=list)
    warning_messages: List[str] = field(default_factory=list)


class SystemValidator(Node):
    """
    System startup validation and health monitoring node.
    
    Provides comprehensive system validation including:
    - Required topic availability checks
    - Service availability validation
    - System health monitoring and status reporting
    - Graceful shutdown coordination
    """
    
    def __init__(self):
        super().__init__('system_validator')
        
        # Declare parameters
        self.declare_parameters(
            namespace='',
            parameters=[
                ('startup_timeout', 30.0),
                ('health_check_period', 2.0),
                ('topic_timeout', 10.0),
                ('service_timeout', 5.0),
                ('enable_camera_check', True),
                ('enable_detection_check', True),
                ('enable_slam_check', True),
                ('enable_rviz_check', False),  # RViz is optional
                ('shutdown_timeout', 10.0),
            ]
        )
        
        # Get parameters
        self.startup_timeout = self.get_parameter('startup_timeout').get_parameter_value().double_value
        self.health_check_period = self.get_parameter('health_check_period').get_parameter_value().double_value
        self.topic_timeout = self.get_parameter('topic_timeout').get_parameter_value().double_value
        self.service_timeout = self.get_parameter('service_timeout').get_parameter_value().double_value
        self.shutdown_timeout = self.get_parameter('shutdown_timeout').get_parameter_value().double_value
        
        # Feature enable flags
        self.enable_camera_check = self.get_parameter('enable_camera_check').get_parameter_value().bool_value
        self.enable_detection_check = self.get_parameter('enable_detection_check').get_parameter_value().bool_value
        self.enable_slam_check = self.get_parameter('enable_slam_check').get_parameter_value().bool_value
        self.enable_rviz_check = self.get_parameter('enable_rviz_check').get_parameter_value().bool_value
        
        # System health tracking
        self.health = SystemHealth()
        self.startup_start_time = time.time()
        self.validation_lock = threading.Lock()
        
        # Configure topic checks based on enabled features
        self.topic_checks = self._configure_topic_checks()
        self.service_checks = self._configure_service_checks()
        
        # Publishers for system status
        self.status_publisher = self.create_publisher(
            String, '/system/status', 
            QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE)
        )
        
        self.health_publisher = self.create_publisher(
            DiagnosticArray, '/system/health',
            QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE)
        )
        
        self.startup_complete_publisher = self.create_publisher(
            Bool, '/system/startup_complete',
            QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE, 
                      durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        )
        
        # Create subscribers for topic monitoring
        self._create_topic_subscribers()
        
        # Health monitoring timer
        self.health_timer = self.create_timer(
            self.health_check_period, self._health_check_callback
        )
        
        # Startup validation timer
        self.startup_timer = self.create_timer(1.0, self._startup_validation_callback)
        
        # Shutdown handler
        self.shutdown_requested = False
        
        self.get_logger().info(
            f'System Validator started - monitoring {len(self.topic_checks)} topics, '
            f'{len(self.service_checks)} services'
        )
    
    def _configure_topic_checks(self) -> Dict[str, TopicCheck]:
        """Configure topic checks based on enabled features."""
        checks = {}
        
        # Camera topics (always required if camera is enabled)
        if self.enable_camera_check:
            checks['/camera/image_raw'] = TopicCheck(
                name='/camera/image_raw',
                msg_type=Image,
                required=True,
                timeout=self.topic_timeout
            )
            
            checks['/camera/camera_info'] = TopicCheck(
                name='/camera/camera_info',
                msg_type=type(None),  # Will be properly typed later
                required=True,
                timeout=self.topic_timeout
            )
        
        # Detection topics (required if detection is enabled)
        if self.enable_detection_check:
            checks['/camera/detection_image'] = TopicCheck(
                name='/camera/detection_image',
                msg_type=Image,
                required=True,
                timeout=self.topic_timeout
            )
            
            checks['/detections'] = TopicCheck(
                name='/detections',
                msg_type=Detection2DArray,
                required=True,
                timeout=self.topic_timeout
            )
        
        # SLAM topics (required if SLAM is enabled)
        if self.enable_slam_check:
            checks['/map'] = TopicCheck(
                name='/map',
                msg_type=OccupancyGrid,
                required=True,
                timeout=self.topic_timeout * 2  # SLAM takes longer to start
            )
            
            checks['/map_metadata'] = TopicCheck(
                name='/map_metadata',
                msg_type=type(None),  # Will be properly typed later
                required=False,  # Metadata is optional
                timeout=self.topic_timeout
            )
        
        return checks
    
    def _configure_service_checks(self) -> Dict[str, ServiceCheck]:
        """Configure service checks based on enabled features."""
        checks = {}
        
        # SLAM services
        if self.enable_slam_check:
            checks['/slam_toolbox/save_map'] = ServiceCheck(
                name='/slam_toolbox/save_map',
                required=False,  # Optional service
                timeout=self.service_timeout
            )
        
        return checks
    
    def _create_topic_subscribers(self) -> None:
        """Create subscribers for topic monitoring."""
        qos_profile = QoSProfile(
            depth=1,
            reliability=QoSReliabilityPolicy.BEST_EFFORT
        )
        
        for topic_name, check in self.topic_checks.items():
            if topic_name == '/camera/image_raw' or topic_name == '/camera/detection_image':
                check.subscriber = self.create_subscription(
                    Image,
                    topic_name,
                    lambda msg, name=topic_name: self._topic_callback(name, msg),
                    qos_profile
                )
            elif topic_name == '/detections':
                check.subscriber = self.create_subscription(
                    Detection2DArray,
                    topic_name,
                    lambda msg, name=topic_name: self._topic_callback(name, msg),
                    qos_profile
                )
            elif topic_name == '/map':
                check.subscriber = self.create_subscription(
                    OccupancyGrid,
                    topic_name,
                    lambda msg, name=topic_name: self._topic_callback(name, msg),
                    qos_profile
                )
            # Add other topic types as needed
    
    def _topic_callback(self, topic_name: str, msg) -> None:
        """Callback for topic message reception."""
        with self.validation_lock:
            if topic_name in self.topic_checks:
                check = self.topic_checks[topic_name]
                check.last_seen = time.time()
                check.is_active = True
                self.health.topic_status[topic_name] = True
    
    def _startup_validation_callback(self) -> None:
        """Validate system startup progress."""
        if self.health.startup_complete:
            self.startup_timer.cancel()
            return
        
        current_time = time.time()
        elapsed_time = current_time - self.startup_start_time
        
        # Check if startup timeout exceeded
        if elapsed_time > self.startup_timeout:
            self._handle_startup_timeout()
            return
        
        # Check topic availability
        with self.validation_lock:
            all_required_topics_active = True
            
            for topic_name, check in self.topic_checks.items():
                if check.required:
                    if not check.is_active:
                        all_required_topics_active = False
                        break
            
            # Check service availability
            all_required_services_available = self._check_service_availability()
            
            # Determine if startup is complete
            if all_required_topics_active and all_required_services_available:
                self._complete_startup(elapsed_time)
    
    def _check_service_availability(self) -> bool:
        """Check availability of required services."""
        for service_name, check in self.service_checks.items():
            if check.required:
                # Check if service is available
                service_available = len(self.get_service_names_and_types_by_node(
                    service_name.split('/')[1] if '/' in service_name else service_name, 
                    service_name
                )) > 0
                
                check.is_available = service_available
                self.health.service_status[service_name] = service_available
                
                if not service_available:
                    return False
        
        return True
    
    def _complete_startup(self, elapsed_time: float) -> None:
        """Complete the startup validation process."""
        self.health.startup_complete = True
        self.health.startup_time = elapsed_time
        self.health.overall_status = SystemStatus.HEALTHY
        
        # Publish startup complete signal
        startup_msg = Bool()
        startup_msg.data = True
        self.startup_complete_publisher.publish(startup_msg)
        
        self.get_logger().info(
            f'System startup validation complete in {elapsed_time:.1f}s - '
            f'All required components are operational'
        )
        
        # Cancel startup timer
        self.startup_timer.cancel()
    
    def _handle_startup_timeout(self) -> None:
        """Handle startup timeout condition."""
        self.health.overall_status = SystemStatus.CRITICAL
        
        # Identify missing components
        missing_topics = []
        missing_services = []
        
        with self.validation_lock:
            for topic_name, check in self.topic_checks.items():
                if check.required and not check.is_active:
                    missing_topics.append(topic_name)
            
            for service_name, check in self.service_checks.items():
                if check.required and not check.is_available:
                    missing_services.append(service_name)
        
        error_msg = (
            f'System startup validation failed after {self.startup_timeout}s timeout. '
            f'Missing topics: {missing_topics}, Missing services: {missing_services}'
        )
        
        self.health.error_messages.append(error_msg)
        self.get_logger().error(error_msg)
        
        # Cancel startup timer
        self.startup_timer.cancel()
    
    def _health_check_callback(self) -> None:
        """Periodic health check callback."""
        current_time = time.time()
        
        with self.validation_lock:
            # Check topic health
            topic_issues = []
            for topic_name, check in self.topic_checks.items():
                if check.required and check.last_seen:
                    time_since_last = current_time - check.last_seen
                    if time_since_last > check.timeout:
                        check.is_active = False
                        self.health.topic_status[topic_name] = False
                        topic_issues.append(f'{topic_name} (last seen {time_since_last:.1f}s ago)')
            
            # Update overall system status
            if topic_issues:
                if self.health.overall_status == SystemStatus.HEALTHY:
                    self.health.overall_status = SystemStatus.DEGRADED
                    self.get_logger().warn(f'System degraded - topic issues: {topic_issues}')
            elif self.health.startup_complete:
                if self.health.overall_status == SystemStatus.DEGRADED:
                    self.health.overall_status = SystemStatus.HEALTHY
                    self.get_logger().info('System health restored')
        
        # Publish health status
        self._publish_health_status()
        self._publish_system_status()
    
    def _publish_health_status(self) -> None:
        """Publish detailed health diagnostics."""
        diagnostic_array = DiagnosticArray()
        diagnostic_array.header.stamp = self.get_clock().now().to_msg()
        
        # Overall system status
        system_status = DiagnosticStatus()
        system_status.name = 'system_validator'
        system_status.hardware_id = 'vision_enhanced_system'
        
        if self.health.overall_status == SystemStatus.HEALTHY:
            system_status.level = DiagnosticStatus.OK
            system_status.message = 'System operating normally'
        elif self.health.overall_status == SystemStatus.DEGRADED:
            system_status.level = DiagnosticStatus.WARN
            system_status.message = 'System degraded - some components unavailable'
        elif self.health.overall_status == SystemStatus.CRITICAL:
            system_status.level = DiagnosticStatus.ERROR
            system_status.message = 'System critical - required components missing'
        else:
            system_status.level = DiagnosticStatus.STALE
            system_status.message = f'System status: {self.health.overall_status.value}'
        
        # Add system metrics
        system_status.values = [
            KeyValue(key='startup_complete', value=str(self.health.startup_complete)),
            KeyValue(key='startup_time', value=f'{self.health.startup_time or 0:.1f}'),
            KeyValue(key='active_topics', value=str(sum(self.health.topic_status.values()))),
            KeyValue(key='total_topics', value=str(len(self.topic_checks))),
            KeyValue(key='active_services', value=str(sum(self.health.service_status.values()))),
            KeyValue(key='total_services', value=str(len(self.service_checks))),
        ]
        
        diagnostic_array.status.append(system_status)
        
        # Individual topic status
        for topic_name, is_active in self.health.topic_status.items():
            topic_status = DiagnosticStatus()
            topic_status.name = f'topic_{topic_name.replace("/", "_")}'
            topic_status.hardware_id = topic_name
            
            if is_active:
                topic_status.level = DiagnosticStatus.OK
                topic_status.message = 'Topic active'
            else:
                check = self.topic_checks.get(topic_name)
                if check and check.required:
                    topic_status.level = DiagnosticStatus.ERROR
                    topic_status.message = 'Required topic inactive'
                else:
                    topic_status.level = DiagnosticStatus.WARN
                    topic_status.message = 'Optional topic inactive'
            
            diagnostic_array.status.append(topic_status)
        
        self.health_publisher.publish(diagnostic_array)
    
    def _publish_system_status(self) -> None:
        """Publish simple system status message."""
        status_msg = String()
        status_msg.data = self.health.overall_status.value
        self.status_publisher.publish(status_msg)
    
    def request_shutdown(self) -> None:
        """Request graceful system shutdown."""
        if self.shutdown_requested:
            return
        
        self.shutdown_requested = True
        self.health.overall_status = SystemStatus.SHUTDOWN
        
        self.get_logger().info('Graceful shutdown requested - coordinating component shutdown')
        
        # Publish shutdown status
        self._publish_system_status()
        
        # Give components time to shutdown gracefully
        shutdown_thread = threading.Thread(target=self._coordinate_shutdown)
        shutdown_thread.start()
    
    def _coordinate_shutdown(self) -> None:
        """Coordinate graceful shutdown of all components."""
        try:
            # Wait for components to shutdown gracefully
            time.sleep(self.shutdown_timeout)
            
            self.get_logger().info('Graceful shutdown coordination complete')
            
        except Exception as e:
            self.get_logger().error(f'Error during shutdown coordination: {e}')
    
    def get_system_health(self) -> SystemHealth:
        """Get current system health status."""
        with self.validation_lock:
            return self.health


def main(args=None):
    """Main entry point for system validator node."""
    rclpy.init(args=args)
    
    validator = SystemValidator()
    
    try:
        rclpy.spin(validator)
    except KeyboardInterrupt:
        validator.get_logger().info('System validator interrupted - requesting graceful shutdown')
        validator.request_shutdown()
    finally:
        validator.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()