#!/usr/bin/env python3
"""
Hardware Discovery Service for Dojo Robot

This module provides automatic detection and configuration of hardware devices
including Arduino controllers, cameras, and LiDAR sensors.
"""

import os
import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import serial
import serial.tools.list_ports
import subprocess
import glob
import logging

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import String
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue


@dataclass
class DeviceInfo:
    """Information about a discovered hardware device"""
    name: str
    device_type: str
    port: str
    vendor_id: Optional[str] = None
    product_id: Optional[str] = None
    description: str = ""
    capabilities: Dict = field(default_factory=dict)
    status: str = "unknown"
    last_seen: datetime = field(default_factory=datetime.now)


@dataclass
class SerialDeviceInfo(DeviceInfo):
    """Information about a serial device (Arduino, LiDAR)"""
    baud_rate: int = 115200
    timeout: float = 1.0
    
    
@dataclass
class CameraDeviceInfo(DeviceInfo):
    """Information about a camera device"""
    resolution: Tuple[int, int] = (640, 480)
    fps: float = 30.0
    formats: List[str] = field(default_factory=list)


class HardwareDiscovery(Node):
    """
    Hardware Discovery Service
    
    Automatically detects and configures Arduino devices, cameras, and LiDAR sensors.
    Provides continuous monitoring and reconnection capabilities.
    """
    
    def __init__(self):
        super().__init__('hardware_discovery')
        
        # Initialize logging
        self.logger = self.get_logger()
        
        # Device storage
        self.discovered_devices: Dict[str, DeviceInfo] = {}
        self.monitoring_active = False
        self.monitor_thread = None
        
        # Publishers
        self.device_status_pub = self.create_publisher(
            DiagnosticArray, 
            '/diagnostics/hardware_discovery', 
            10
        )
        
        # Parameters
        self.declare_parameter('scan_interval', 5.0)
        self.declare_parameter('arduino_vendor_ids', ['2341', '1a86', '0403'])  # Arduino, CH340, FTDI
        self.declare_parameter('lidar_vendor_ids', ['10c4', '0483'])  # SiLabs, STM
        self.declare_parameter('enable_monitoring', True)
        
        self.scan_interval = self.get_parameter('scan_interval').value
        self.arduino_vendor_ids = self.get_parameter('arduino_vendor_ids').value
        self.lidar_vendor_ids = self.get_parameter('lidar_vendor_ids').value
        self.enable_monitoring = self.get_parameter('enable_monitoring').value
        
        # Start initial discovery
        self.logger.info("Starting hardware discovery service...")
        self.discover_all_devices()
        
        # Start monitoring if enabled
        if self.enable_monitoring:
            self.start_monitoring()
    
    def discover_all_devices(self) -> Dict[str, DeviceInfo]:
        """
        Discover all hardware devices
        
        Returns:
            Dictionary of discovered devices keyed by device identifier
        """
        self.logger.info("Starting comprehensive hardware discovery...")
        
        # Clear previous discoveries
        self.discovered_devices.clear()
        
        # Discover different device types
        arduino_devices = self.scan_serial_devices()
        camera_devices = self.detect_cameras()
        lidar_devices = self.find_lidar_devices()
        
        # Combine all discoveries
        all_devices = {}
        all_devices.update({f"arduino_{i}": dev for i, dev in enumerate(arduino_devices)})
        all_devices.update({f"camera_{i}": dev for i, dev in enumerate(camera_devices)})
        all_devices.update({f"lidar_{i}": dev for i, dev in enumerate(lidar_devices)})
        
        self.discovered_devices = all_devices
        
        # Log discovery results
        self.logger.info(f"Hardware discovery complete. Found {len(all_devices)} devices:")
        for device_id, device in all_devices.items():
            self.logger.info(f"  {device_id}: {device.device_type} on {device.port}")
        
        # Publish diagnostics
        self._publish_diagnostics()
        
        return all_devices
    
    def scan_serial_devices(self) -> List[SerialDeviceInfo]:
        """
        Scan for Arduino devices on serial ports
        
        Returns:
            List of discovered Arduino devices
        """
        arduino_devices = []
        
        try:
            # Get all available serial ports
            ports = serial.tools.list_ports.comports()
            
            for port in ports:
                # Check if this looks like an Arduino
                if self._is_arduino_device(port):
                    device = SerialDeviceInfo(
                        name=f"Arduino_{port.device.split('/')[-1]}",
                        device_type="arduino",
                        port=port.device,
                        vendor_id=port.vid,
                        product_id=port.pid,
                        description=port.description or "Arduino Compatible Device"
                    )
                    
                    # Test communication
                    if self._test_arduino_communication(device):
                        device.status = "available"
                        arduino_devices.append(device)
                        self.logger.info(f"Found Arduino device: {device.port}")
                    else:
                        device.status = "communication_failed"
                        arduino_devices.append(device)
                        self.logger.warning(f"Arduino found but communication failed: {device.port}")
                        
        except Exception as e:
            self.logger.error(f"Error scanning for Arduino devices: {e}")
        
        return arduino_devices
    
    def detect_cameras(self) -> List[CameraDeviceInfo]:
        """
        Detect camera devices and their capabilities
        
        Returns:
            List of discovered camera devices
        """
        camera_devices = []
        
        try:
            # Check for video devices
            video_devices = glob.glob('/dev/video*')
            
            for device_path in video_devices:
                device_num = device_path.split('video')[-1]
                
                # Get camera capabilities
                capabilities = self._get_camera_capabilities(device_path)
                
                if capabilities:
                    device = CameraDeviceInfo(
                        name=f"Camera_{device_num}",
                        device_type="camera",
                        port=device_path,
                        description=f"Video device {device_num}",
                        capabilities=capabilities,
                        resolution=capabilities.get('resolution', (640, 480)),
                        fps=capabilities.get('fps', 30.0),
                        formats=capabilities.get('formats', [])
                    )
                    device.status = "available"
                    camera_devices.append(device)
                    self.logger.info(f"Found camera device: {device_path}")
                    
        except Exception as e:
            self.logger.error(f"Error detecting camera devices: {e}")
        
        return camera_devices
    
    def find_lidar_devices(self) -> List[SerialDeviceInfo]:
        """
        Find and identify LiDAR devices
        
        Returns:
            List of discovered LiDAR devices
        """
        lidar_devices = []
        
        try:
            # Get all available serial ports
            ports = serial.tools.list_ports.comports()
            
            for port in ports:
                # Check if this looks like a LiDAR device
                if self._is_lidar_device(port):
                    device = SerialDeviceInfo(
                        name=f"LiDAR_{port.device.split('/')[-1]}",
                        device_type="lidar",
                        port=port.device,
                        vendor_id=port.vid,
                        product_id=port.pid,
                        description=port.description or "LiDAR Device"
                    )
                    
                    # Identify LiDAR model
                    model_info = self._identify_lidar_model(device)
                    if model_info:
                        device.capabilities = model_info
                        device.status = "available"
                        lidar_devices.append(device)
                        self.logger.info(f"Found LiDAR device: {device.port} ({model_info.get('model', 'Unknown')})")
                    else:
                        device.status = "identification_failed"
                        lidar_devices.append(device)
                        self.logger.warning(f"LiDAR found but model identification failed: {device.port}")
                        
        except Exception as e:
            self.logger.error(f"Error scanning for LiDAR devices: {e}")
        
        return lidar_devices
    
    def _is_arduino_device(self, port) -> bool:
        """Check if a serial port device is likely an Arduino"""
        if not port.vid:
            return False
            
        # Check vendor ID
        vid_hex = f"{port.vid:04x}"
        return vid_hex in self.arduino_vendor_ids
    
    def _is_lidar_device(self, port) -> bool:
        """Check if a serial port device is likely a LiDAR"""
        if not port.vid:
            return False
            
        # Check vendor ID
        vid_hex = f"{port.vid:04x}"
        return vid_hex in self.lidar_vendor_ids
    
    def _test_arduino_communication(self, device: SerialDeviceInfo) -> bool:
        """Test communication with an Arduino device"""
        try:
            with serial.Serial(device.port, device.baud_rate, timeout=device.timeout) as ser:
                # Send a simple test command
                ser.write(b'?\n')
                time.sleep(0.1)
                
                # Try to read response
                response = ser.readline().decode('utf-8', errors='ignore').strip()
                
                # Arduino bridge typically responds with version or command list
                return len(response) > 0
                
        except Exception as e:
            self.logger.debug(f"Arduino communication test failed for {device.port}: {e}")
            return False
    
    def _get_camera_capabilities(self, device_path: str) -> Optional[Dict]:
        """Get camera device capabilities using v4l2-ctl"""
        try:
            # Use v4l2-ctl to get device capabilities
            result = subprocess.run(
                ['v4l2-ctl', '--device', device_path, '--list-formats-ext'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                capabilities = self._parse_v4l2_output(result.stdout)
                return capabilities
            else:
                # Fallback: basic capability detection
                return {
                    'resolution': (640, 480),
                    'fps': 30.0,
                    'formats': ['YUYV', 'MJPG']
                }
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # v4l2-ctl not available or timeout
            return {
                'resolution': (640, 480),
                'fps': 30.0,
                'formats': ['YUYV']
            }
        except Exception as e:
            self.logger.debug(f"Error getting camera capabilities for {device_path}: {e}")
            return None
    
    def _parse_v4l2_output(self, output: str) -> Dict:
        """Parse v4l2-ctl output to extract capabilities"""
        capabilities = {
            'formats': [],
            'resolutions': [],
            'fps': 30.0
        }
        
        lines = output.split('\n')
        current_format = None
        
        for line in lines:
            line = line.strip()
            
            # Extract pixel formats
            if 'Pixel Format:' in line:
                format_match = line.split("'")[1] if "'" in line else None
                if format_match:
                    current_format = format_match
                    capabilities['formats'].append(current_format)
            
            # Extract resolutions
            elif 'Size:' in line and 'x' in line:
                try:
                    size_part = line.split('Size:')[1].strip()
                    width, height = map(int, size_part.split('x'))
                    capabilities['resolutions'].append((width, height))
                except:
                    pass
        
        # Set default resolution to largest available
        if capabilities['resolutions']:
            capabilities['resolution'] = max(capabilities['resolutions'], key=lambda x: x[0] * x[1])
        else:
            capabilities['resolution'] = (640, 480)
        
        return capabilities
    
    def _identify_lidar_model(self, device: SerialDeviceInfo) -> Optional[Dict]:
        """Identify LiDAR model by attempting communication"""
        try:
            with serial.Serial(device.port, device.baud_rate, timeout=device.timeout) as ser:
                # Try common LiDAR identification commands
                
                # RPLIDAR identification
                ser.write(b'\xA5\x50\x00\x00\x00\x00\x02')  # Get device info command
                time.sleep(0.1)
                response = ser.read(100)
                
                if len(response) > 0:
                    return {
                        'model': 'RPLIDAR',
                        'scan_frequency': 10.0,
                        'range_min': 0.15,
                        'range_max': 12.0,
                        'angle_min': 0.0,
                        'angle_max': 6.28318530718
                    }
                
                # Add other LiDAR identification protocols here
                
        except Exception as e:
            self.logger.debug(f"LiDAR identification failed for {device.port}: {e}")
        
        return None
    
    def start_monitoring(self):
        """Start continuous device monitoring"""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Started hardware monitoring")
    
    def stop_monitoring(self):
        """Stop continuous device monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        self.logger.info("Stopped hardware monitoring")
    
    def _monitoring_loop(self):
        """Continuous monitoring loop"""
        while self.monitoring_active:
            try:
                # Re-discover devices
                current_devices = self.discover_all_devices()
                
                # Check for changes
                self._check_device_changes(current_devices)
                
                # Wait for next scan
                time.sleep(self.scan_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.scan_interval)
    
    def _check_device_changes(self, current_devices: Dict[str, DeviceInfo]):
        """Check for device additions/removals"""
        # This is a simplified implementation
        # In a full implementation, you would track device changes
        # and publish appropriate notifications
        pass
    
    def _publish_diagnostics(self):
        """Publish hardware discovery diagnostics"""
        msg = DiagnosticArray()
        msg.header.stamp = self.get_clock().now().to_msg()
        
        for device_id, device in self.discovered_devices.items():
            status = DiagnosticStatus()
            status.name = f"hardware_discovery/{device_id}"
            status.hardware_id = device.port
            
            if device.status == "available":
                status.level = DiagnosticStatus.OK
                status.message = f"{device.device_type} available"
            else:
                status.level = DiagnosticStatus.WARN
                status.message = f"{device.device_type} {device.status}"
            
            # Add key-value pairs
            status.values.append(KeyValue(key="device_type", value=device.device_type))
            status.values.append(KeyValue(key="port", value=device.port))
            status.values.append(KeyValue(key="status", value=device.status))
            
            if device.vendor_id:
                status.values.append(KeyValue(key="vendor_id", value=f"{device.vendor_id:04x}"))
            if device.product_id:
                status.values.append(KeyValue(key="product_id", value=f"{device.product_id:04x}"))
            
            msg.status.append(status)
        
        self.device_status_pub.publish(msg)
    
    def get_devices_by_type(self, device_type: str) -> List[DeviceInfo]:
        """Get all discovered devices of a specific type"""
        return [device for device in self.discovered_devices.values() 
                if device.device_type == device_type]
    
    def get_device_by_name(self, name: str) -> Optional[DeviceInfo]:
        """Get a specific device by name"""
        for device in self.discovered_devices.values():
            if device.name == name:
                return device
        return None
    
    def destroy_node(self):
        """Clean shutdown"""
        self.stop_monitoring()
        super().destroy_node()


def main(args=None):
    """Main entry point for hardware discovery service"""
    rclpy.init(args=args)
    
    try:
        discovery_service = HardwareDiscovery()
        rclpy.spin(discovery_service)
    except KeyboardInterrupt:
        pass
    finally:
        if 'discovery_service' in locals():
            discovery_service.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()