#!/usr/bin/env python3
"""
Enhanced LiDAR Driver with Auto-Discovery and Model Detection

This module provides an advanced LiDAR driver that automatically discovers
LiDAR devices, identifies their models, and provides adaptive configuration.
"""

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Header, String
from geometry_msgs.msg import Twist
from robot_interfaces.msg import EmergencyStop
import math
import time
from typing import Dict, List, Optional, Tuple
import numpy as np

from .hardware_discovery import HardwareDiscovery
from .device_abstraction import DeviceManager, DeviceStatus
from .device_implementations import LiDARDevice


class LiDARDriver(Node):
    """
    Enhanced LiDAR Driver with auto-discovery and model detection
    
    Features:
    - Automatic LiDAR device discovery
    - Model identification (RPLIDAR, etc.)
    - Adaptive configuration based on model capabilities
    - Multiple LiDAR support
    - Automatic reconnection
    - Safety integration
    """
    
    def __init__(self):
        super().__init__('lidar_driver')
        
        # Declare parameters
        self.declare_parameter('auto_discover', True)
        self.declare_parameter('fallback_port', '/dev/ttyUSB0')
        self.declare_parameter('fallback_model', 'RPLIDAR')
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('frame_id', 'laser')
        self.declare_parameter('scan_frequency', 10.0)
        self.declare_parameter('range_min', 0.15)
        self.declare_parameter('range_max', 12.0)
        self.declare_parameter('angle_min', 0.0)
        self.declare_parameter('angle_max', 6.28318530718)  # 2*pi
        self.declare_parameter('publish_intensity', True)
        self.declare_parameter('inverted', False)
        self.declare_parameter('angle_compensate', True)
        self.declare_parameter('max_lidars', 2)
        
        # Get parameters
        self.auto_discover = self.get_parameter('auto_discover').value
        self.fallback_port = self.get_parameter('fallback_port').value
        self.fallback_model = self.get_parameter('fallback_model').value
        self.baud_rate = self.get_parameter('baud_rate').value
        self.frame_id = self.get_parameter('frame_id').value
        self.scan_frequency = self.get_parameter('scan_frequency').value
        self.range_min = self.get_parameter('range_min').value
        self.range_max = self.get_parameter('range_max').value
        self.angle_min = self.get_parameter('angle_min').value
        self.angle_max = self.get_parameter('angle_max').value
        self.publish_intensity = self.get_parameter('publish_intensity').value
        self.inverted = self.get_parameter('inverted').value
        self.angle_compensate = self.get_parameter('angle_compensate').value
        self.max_lidars = self.get_parameter('max_lidars').value
        
        # Initialize components
        self.hardware_discovery = None
        self.device_manager = DeviceManager()
        
        # LiDAR management
        self.lidar_devices: Dict[str, LiDARDevice] = {}
        self.publishers: Dict[str, rclpy.publisher.Publisher] = {}
        
        # Scan data management
        self.scan_data: Dict[str, Dict] = {}
        self.last_scan_time: Dict[str, float] = {}
        
        # Safety monitoring
        self.obstacle_detected = False
        self.min_obstacle_distance = float('inf')
        
        # Safety system integration
        self.emergency_stop_active = False
        self.last_heartbeat_time = self.get_clock().now()
        
        # Safety system publishers
        self.component_heartbeat_pub = self.create_publisher(
            String, '/component_heartbeat', 10)
        self.emergency_stop_ack_pub = self.create_publisher(
            String, '/emergency_stop_ack', 10)
        self.recovery_ready_pub = self.create_publisher(
            String, '/recovery_ready', 10)
        
        # Safety system subscribers
        self.emergency_stop_sub = self.create_subscription(
            EmergencyStop,
            '/emergency_stop',
            self.emergency_stop_callback,
            10
        )
        
        # Initialize hardware discovery if enabled
        if self.auto_discover:
            self.hardware_discovery = HardwareDiscovery()
        
        # Discover and initialize LiDARs
        self.initialize_lidars()
        
        # Timer for processing scans
        self.scan_timer = self.create_timer(1.0 / self.scan_frequency, self.process_scans)
        
        # Safety system heartbeat timer
        self.heartbeat_timer = self.create_timer(1.0, self.send_heartbeat)
        
        # Timer for safety monitoring
        self.safety_timer = self.create_timer(0.1, self.monitor_safety)  # 10 Hz
        
        self.get_logger().info(f'LiDAR driver initialized with {len(self.lidar_devices)} LiDARs')
    
    def initialize_lidars(self):
        """Initialize LiDAR devices using auto-discovery or fallback."""
        if self.auto_discover and self.hardware_discovery:
            self.get_logger().info('Discovering LiDAR devices...')
            
            # Discover all devices
            devices = self.hardware_discovery.discover_all_devices()
            lidar_devices = [dev for dev in devices.values() 
                           if dev.device_type == 'lidar' and dev.status == 'available']
            
            if lidar_devices:
                # Limit number of LiDARs
                lidar_devices = lidar_devices[:self.max_lidars]
                
                for i, lidar_info in enumerate(lidar_devices):
                    self._setup_lidar_device(lidar_info.name, lidar_info.port, lidar_info.capabilities)
            else:
                self.get_logger().warning('No LiDARs found via auto-discovery, using fallback')
                self._setup_fallback_lidar()
        else:
            self.get_logger().info('Auto-discovery disabled, using fallback LiDAR')
            self._setup_fallback_lidar()
    
    def _setup_lidar_device(self, name: str, port: str, capabilities: Dict):
        """Setup a LiDAR device with detected capabilities."""
        try:
            # Extract model from capabilities
            model = capabilities.get('model', 'RPLIDAR')
            
            self.get_logger().info(f'Setting up LiDAR {name}: {model} on {port}')
            
            # Create LiDAR device
            lidar_device = LiDARDevice(
                name=name,
                port=port,
                baud_rate=self.baud_rate,
                model=model
            )
            
            # Update parameters based on capabilities
            if 'range_min' in capabilities:
                self.range_min = capabilities['range_min']
            if 'range_max' in capabilities:
                self.range_max = capabilities['range_max']
            if 'scan_frequency' in capabilities:
                self.scan_frequency = capabilities['scan_frequency']
            
            # Register with device manager
            self.device_manager.register_device(lidar_device)
            
            # Add status callback
            lidar_device.add_status_callback(
                lambda status, lidar_name=name: self._on_lidar_status_change(lidar_name, status)
            )
            
            # Connect to LiDAR
            if lidar_device.connect():
                self.lidar_devices[name] = lidar_device
                self._setup_publisher(name)
                
                # Initialize scan data tracking
                self.scan_data[name] = {}
                self.last_scan_time[name] = time.time()
                
                # Start scanning
                lidar_device.write({'start_scan': True})
                
                self.get_logger().info(f'Successfully initialized LiDAR: {name}')
            else:
                self.get_logger().error(f'Failed to connect to LiDAR: {name}')
                
        except Exception as e:
            self.get_logger().error(f'Error setting up LiDAR {name}: {e}')
    
    def _setup_fallback_lidar(self):
        """Setup fallback LiDAR with default configuration."""
        name = "lidar_fallback"
        
        lidar_device = LiDARDevice(
            name=name,
            port=self.fallback_port,
            baud_rate=self.baud_rate,
            model=self.fallback_model
        )
        
        # Register with device manager
        self.device_manager.register_device(lidar_device)
        
        # Add status callback
        lidar_device.add_status_callback(
            lambda status: self._on_lidar_status_change(name, status)
        )
        
        # Connect to LiDAR
        if lidar_device.connect():
            self.lidar_devices[name] = lidar_device
            self._setup_publisher(name)
            
            # Initialize scan data tracking
            self.scan_data[name] = {}
            self.last_scan_time[name] = time.time()
            
            # Start scanning
            lidar_device.write({'start_scan': True})
            
            self.get_logger().info(f'Fallback LiDAR initialized: {name}')
        else:
            self.get_logger().error(f'Failed to initialize fallback LiDAR: {name}')
    
    def _setup_publisher(self, lidar_name: str):
        """Setup ROS publisher for a LiDAR."""
        # Create unique topic names for multiple LiDARs
        if len(self.lidar_devices) > 1:
            topic_name = f'/scan_{lidar_name}'
        else:
            topic_name = '/scan'
        
        publisher = self.create_publisher(LaserScan, topic_name, 10)
        self.publishers[lidar_name] = publisher
        
        self.get_logger().info(f'Created publisher for {lidar_name}: {topic_name}')
    
    def _on_lidar_status_change(self, lidar_name: str, status: DeviceStatus):
        """Handle LiDAR device status changes."""
        if status == DeviceStatus.CONNECTED:
            self.get_logger().info(f'LiDAR {lidar_name} reconnected')
            # Restart scanning
            if lidar_name in self.lidar_devices:
                self.lidar_devices[lidar_name].write({'start_scan': True})
        elif status == DeviceStatus.DISCONNECTED or status == DeviceStatus.ERROR:
            self.get_logger().warning(f'LiDAR {lidar_name} connection lost: {status.value}')
        elif status == DeviceStatus.RECONNECTING:
            self.get_logger().info(f'LiDAR {lidar_name} attempting reconnection...')
    
    def process_scans(self):
        """Process scan data from all LiDARs and publish LaserScan messages."""
        current_time = self.get_clock().now()
        
        for lidar_name, lidar_device in self.lidar_devices.items():
            try:
                # Read scan data from LiDAR
                data = lidar_device.read()
                
                if data and 'scan_data' in data:
                    scan_info = data['scan_data']
                    
                    # Create LaserScan message
                    scan_msg = self._create_laser_scan_message(lidar_name, scan_info, current_time)
                    
                    if scan_msg:
                        # Publish scan
                        if lidar_name in self.publishers:
                            self.publishers[lidar_name].publish(scan_msg)
                        
                        # Update scan data for safety monitoring
                        self.scan_data[lidar_name] = scan_info
                        self.last_scan_time[lidar_name] = time.time()
                    
            except Exception as e:
                self.get_logger().error(f'Error processing scan from LiDAR {lidar_name}: {e}')
    
    def _create_laser_scan_message(self, lidar_name: str, scan_info: Dict, timestamp) -> Optional[LaserScan]:
        """Create LaserScan message from scan data."""
        try:
            ranges = scan_info.get('ranges', [])
            angles = scan_info.get('angles', [])
            intensities = scan_info.get('intensities', [])
            
            if not ranges or not angles:
                return None
            
            # Create LaserScan message
            scan_msg = LaserScan()
            scan_msg.header.stamp = timestamp.to_msg()
            scan_msg.header.frame_id = self.frame_id
            
            # Set scan parameters
            scan_msg.angle_min = self.angle_min
            scan_msg.angle_max = self.angle_max
            scan_msg.angle_increment = (self.angle_max - self.angle_min) / len(ranges) if ranges else 0.0
            scan_msg.time_increment = 0.0  # Assume instantaneous scan
            scan_msg.scan_time = scan_info.get('scan_time', 0.1)
            scan_msg.range_min = self.range_min
            scan_msg.range_max = self.range_max
            
            # Process ranges
            processed_ranges = []
            for i, range_val in enumerate(ranges):
                # Apply range limits
                if range_val < self.range_min or range_val > self.range_max:
                    processed_ranges.append(float('inf'))
                else:
                    processed_ranges.append(float(range_val))
            
            scan_msg.ranges = processed_ranges
            
            # Add intensities if available and requested
            if self.publish_intensity and intensities:
                scan_msg.intensities = [float(intensity) for intensity in intensities]
            
            return scan_msg
            
        except Exception as e:
            self.get_logger().error(f'Error creating LaserScan message: {e}')
            return None
    
    def monitor_safety(self):
        """Monitor scan data for safety conditions."""
        try:
            min_distance = float('inf')
            obstacle_detected = False
            
            current_time = time.time()
            
            for lidar_name, scan_data in self.scan_data.items():
                # Check if scan data is recent
                if lidar_name in self.last_scan_time:
                    time_since_scan = current_time - self.last_scan_time[lidar_name]
                    if time_since_scan > 1.0:  # 1 second timeout
                        continue
                
                # Check ranges for obstacles
                ranges = scan_data.get('ranges', [])
                for range_val in ranges:
                    if self.range_min <= range_val <= self.range_max:
                        min_distance = min(min_distance, range_val)
                        
                        # Check for close obstacles
                        if range_val < 0.5:  # 50cm safety threshold
                            obstacle_detected = True
            
            # Update safety status
            self.obstacle_detected = obstacle_detected
            self.min_obstacle_distance = min_distance if min_distance != float('inf') else 0.0
            
            # Log safety warnings
            if obstacle_detected:
                self.get_logger().warning(f'Obstacle detected at {min_distance:.2f}m')
            
        except Exception as e:
            self.get_logger().error(f'Error in safety monitoring: {e}')
    
    def get_lidar_capabilities(self, lidar_name: str) -> Optional[Dict]:
        """Get capabilities of a specific LiDAR."""
        if lidar_name not in self.lidar_devices:
            return None
        
        lidar_device = self.lidar_devices[lidar_name]
        return {name: cap.value for name, cap in lidar_device.capabilities.items()}
    
    def list_lidars(self) -> List[str]:
        """Get list of available LiDAR names."""
        return list(self.lidar_devices.keys())
    
    def start_scanning(self, lidar_name: Optional[str] = None) -> bool:
        """Start scanning for specific LiDAR or all LiDARs."""
        if lidar_name:
            if lidar_name in self.lidar_devices:
                return self.lidar_devices[lidar_name].write({'start_scan': True})
            return False
        else:
            # Start all LiDARs
            results = []
            for device in self.lidar_devices.values():
                results.append(device.write({'start_scan': True}))
            return all(results)
    
    def stop_scanning(self, lidar_name: Optional[str] = None) -> bool:
        """Stop scanning for specific LiDAR or all LiDARs."""
        if lidar_name:
            if lidar_name in self.lidar_devices:
                return self.lidar_devices[lidar_name].write({'stop_scan': True})
            return False
        else:
            # Stop all LiDARs
            results = []
            for device in self.lidar_devices.values():
                results.append(device.write({'stop_scan': True}))
            return all(results)
    
    def is_obstacle_detected(self) -> bool:
        """Check if any obstacles are detected."""
        return self.obstacle_detected
    
    def get_min_obstacle_distance(self) -> float:
        """Get minimum obstacle distance from all LiDARs."""
        return self.min_obstacle_distance
    
    def emergency_stop(self):
        """Emergency stop all LiDARs."""
        self.get_logger().warning('Emergency stop triggered for all LiDARs')
        self.stop_scanning()
    
    def destroy_node(self):
        """Clean shutdown of LiDAR driver."""
        try:
            # Stop scanning on all LiDARs
            self.stop_scanning()
            
            # Disconnect all LiDARs
            for lidar_device in self.lidar_devices.values():
                lidar_device.disconnect()
            
            # Cleanup device manager
            if self.device_manager:
                self.device_manager.destroy_node()
            
            # Cleanup hardware discovery
            if self.hardware_discovery:
                self.hardware_discovery.destroy_node()
                
        except Exception as e:
            self.get_logger().error(f'Error during LiDAR driver cleanup: {e}')
        
        super().destroy_node()

    def emergency_stop_callback(self, msg: EmergencyStop) -> None:
        """Handle emergency stop messages from safety system"""
        self.emergency_stop_active = msg.active
        
        if msg.active:
            # Continue LiDAR operation during emergency stop for safety monitoring
            # LiDAR data is crucial for obstacle detection even during emergency stop
            
            # Acknowledge emergency stop
            ack_msg = String()
            ack_msg.data = "lidar_driver"
            self.emergency_stop_ack_pub.publish(ack_msg)
            
            self.get_logger().warn(f"Emergency stop activated: {msg.reason} - LiDAR continues for safety")
        else:
            # Signal ready for recovery
            recovery_msg = String()
            recovery_msg.data = "lidar_driver"
            self.recovery_ready_pub.publish(recovery_msg)
            
            self.get_logger().info("Emergency stop cleared - LiDAR driver ready")
    
    def send_heartbeat(self) -> None:
        """Send heartbeat to watchdog system"""
        try:
            heartbeat_msg = String()
            heartbeat_msg.data = "lidar_driver"
            self.component_heartbeat_pub.publish(heartbeat_msg)
            self.last_heartbeat_time = self.get_clock().now()
        except Exception as e:
            self.get_logger().error(f"Failed to send heartbeat: {e}")

def main(args=None):
    """Main entry point for LiDAR driver."""
    rclpy.init(args=args)
    
    try:
        lidar_driver = LiDARDriver()
        rclpy.spin(lidar_driver)
    except KeyboardInterrupt:
        pass
    finally:
        if 'lidar_driver' in locals():
            lidar_driver.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()