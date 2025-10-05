#!/usr/bin/env python3
"""
Device-specific implementations for Dojo Robot hardware

This module provides concrete implementations of the HardwareDevice interface
for Arduino controllers, cameras, and LiDAR sensors.
"""

import time
import serial
import cv2
import subprocess
from typing import Dict, Any, Optional, Tuple
import logging

from .device_abstraction import (
    HardwareDevice, ConnectionInfo, ConnectionType, DeviceStatus
)


class ArduinoDevice(HardwareDevice):
    """
    Arduino device implementation with ROS Arduino Bridge protocol
    """
    
    def __init__(self, name: str, port: str, baud_rate: int = 115200, timeout: float = 1.0):
        connection_info = ConnectionInfo(
            connection_type=ConnectionType.SERIAL,
            address=port,
            parameters={
                'baud_rate': baud_rate,
                'timeout': timeout
            }
        )
        
        super().__init__(name, connection_info)
        
        self.baud_rate = baud_rate
        self.timeout = timeout
        self._serial_connection = None
        
        # Arduino-specific capabilities
        self.add_capability('motor_control', True, "Motor control capability")
        self.add_capability('encoder_reading', True, "Encoder reading capability")
        self.add_capability('sensor_reading', True, "Sensor reading capability")
        self.add_capability('max_rpm', 100, "Maximum motor RPM")
        
        # Command tracking
        self._last_command_time = time.time()
        self._command_timeout = 1.0  # seconds
    
    def _establish_connection(self) -> bool:
        """Establish serial connection to Arduino"""
        try:
            self._serial_connection = serial.Serial(
                port=self.connection_info.address,
                baudrate=self.baud_rate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            
            # Wait for Arduino to initialize
            time.sleep(2.0)
            
            # Clear any pending data
            self._serial_connection.flushInput()
            self._serial_connection.flushOutput()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to establish Arduino connection: {e}")
            return False
    
    def _close_connection(self):
        """Close serial connection"""
        if self._serial_connection and self._serial_connection.is_open:
            try:
                # Send stop command before closing
                self._send_command("m 0 0")
                self._serial_connection.close()
            except Exception as e:
                self.logger.error(f"Error closing Arduino connection: {e}")
        
        self._serial_connection = None
    
    def _test_communication(self) -> bool:
        """Test communication with Arduino"""
        try:
            if not self._serial_connection or not self._serial_connection.is_open:
                return False
            
            # Send ping command
            response = self._send_command("?")
            return response is not None and len(response) > 0
            
        except Exception as e:
            self.logger.debug(f"Arduino communication test failed: {e}")
            return False
    
    def _read_data(self) -> Optional[Dict[str, Any]]:
        """Read sensor data from Arduino"""
        try:
            if not self._serial_connection or not self._serial_connection.is_open:
                return None
            
            # Read encoder values
            encoder_response = self._send_command("e")
            if encoder_response:
                try:
                    # Parse encoder response: "left_encoder right_encoder"
                    parts = encoder_response.strip().split()
                    if len(parts) >= 2:
                        left_encoder = int(parts[0])
                        right_encoder = int(parts[1])
                        
                        return {
                            'encoders': {
                                'left': left_encoder,
                                'right': right_encoder
                            },
                            'timestamp': time.time()
                        }
                except (ValueError, IndexError) as e:
                    self.logger.debug(f"Error parsing encoder data: {e}")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error reading Arduino data: {e}")
            return None
    
    def _write_data(self, data: Dict[str, Any]) -> bool:
        """Write motor commands to Arduino"""
        try:
            if not self._serial_connection or not self._serial_connection.is_open:
                return False
            
            # Handle motor commands
            if 'motor_speeds' in data:
                left_speed = data['motor_speeds'].get('left', 0)
                right_speed = data['motor_speeds'].get('right', 0)
                
                # Send motor command
                command = f"m {left_speed} {right_speed}"
                response = self._send_command(command)
                
                self._last_command_time = time.time()
                return response is not None
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing Arduino data: {e}")
            return False
    
    def _send_command(self, command: str) -> Optional[str]:
        """Send command to Arduino and get response"""
        try:
            if not self._serial_connection or not self._serial_connection.is_open:
                return None
            
            # Send command
            self._serial_connection.write(f"{command}\n".encode())
            self._serial_connection.flush()
            
            # Read response
            response = self._serial_connection.readline().decode('utf-8', errors='ignore').strip()
            return response
            
        except Exception as e:
            self.logger.debug(f"Error sending Arduino command '{command}': {e}")
            return None
    
    def emergency_stop(self) -> bool:
        """Send emergency stop command to Arduino"""
        return self._write_data({'motor_speeds': {'left': 0, 'right': 0}})
    
    def is_command_timeout(self) -> bool:
        """Check if command timeout has occurred"""
        return (time.time() - self._last_command_time) > self._command_timeout


class CameraDevice(HardwareDevice):
    """
    Camera device implementation using OpenCV
    """
    
    def __init__(self, name: str, device_path: str, resolution: Tuple[int, int] = (640, 480), fps: float = 30.0):
        connection_info = ConnectionInfo(
            connection_type=ConnectionType.USB,
            address=device_path,
            parameters={
                'resolution': resolution,
                'fps': fps
            }
        )
        
        super().__init__(name, connection_info)
        
        self.device_path = device_path
        self.resolution = resolution
        self.fps = fps
        self._camera = None
        
        # Camera-specific capabilities
        self.add_capability('resolution', resolution, "Camera resolution")
        self.add_capability('fps', fps, "Frames per second")
        self.add_capability('formats', ['BGR', 'RGB', 'GRAY'], "Supported pixel formats")
        
        # Auto-detect additional capabilities
        self._detect_capabilities()
    
    def _detect_capabilities(self):
        """Detect camera capabilities using v4l2-ctl"""
        try:
            result = subprocess.run(
                ['v4l2-ctl', '--device', self.device_path, '--list-formats-ext'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse capabilities from v4l2-ctl output
                formats = []
                resolutions = []
                
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Pixel Format:' in line and "'" in line:
                        format_name = line.split("'")[1]
                        formats.append(format_name)
                    elif 'Size:' in line and 'x' in line:
                        try:
                            size_part = line.split('Size:')[1].strip().split()[0]
                            width, height = map(int, size_part.split('x'))
                            resolutions.append((width, height))
                        except:
                            pass
                
                if formats:
                    self.add_capability('hardware_formats', formats, "Hardware supported formats")
                if resolutions:
                    self.add_capability('supported_resolutions', resolutions, "Supported resolutions")
                    
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # v4l2-ctl not available, use defaults
            pass
        except Exception as e:
            self.logger.debug(f"Error detecting camera capabilities: {e}")
    
    def _establish_connection(self) -> bool:
        """Establish connection to camera"""
        try:
            # Extract device number from path
            device_num = int(self.device_path.split('video')[-1])
            
            self._camera = cv2.VideoCapture(device_num)
            
            if not self._camera.isOpened():
                return False
            
            # Configure camera
            self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self._camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Test frame capture
            ret, frame = self._camera.read()
            if not ret or frame is None:
                self._camera.release()
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to establish camera connection: {e}")
            return False
    
    def _close_connection(self):
        """Close camera connection"""
        if self._camera:
            try:
                self._camera.release()
            except Exception as e:
                self.logger.error(f"Error closing camera connection: {e}")
        
        self._camera = None
    
    def _test_communication(self) -> bool:
        """Test camera communication by capturing a frame"""
        try:
            if not self._camera or not self._camera.isOpened():
                return False
            
            ret, frame = self._camera.read()
            return ret and frame is not None
            
        except Exception as e:
            self.logger.debug(f"Camera communication test failed: {e}")
            return False
    
    def _read_data(self) -> Optional[Dict[str, Any]]:
        """Capture frame from camera"""
        try:
            if not self._camera or not self._camera.isOpened():
                return None
            
            ret, frame = self._camera.read()
            if ret and frame is not None:
                return {
                    'frame': frame,
                    'timestamp': time.time(),
                    'resolution': frame.shape[:2][::-1],  # (width, height)
                    'channels': frame.shape[2] if len(frame.shape) > 2 else 1
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error reading camera data: {e}")
            return None
    
    def _write_data(self, data: Dict[str, Any]) -> bool:
        """Configure camera parameters"""
        try:
            if not self._camera or not self._camera.isOpened():
                return False
            
            # Handle configuration changes
            if 'resolution' in data:
                width, height = data['resolution']
                self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                self.resolution = (width, height)
            
            if 'fps' in data:
                self._camera.set(cv2.CAP_PROP_FPS, data['fps'])
                self.fps = data['fps']
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error configuring camera: {e}")
            return False
    
    def get_current_resolution(self) -> Tuple[int, int]:
        """Get current camera resolution"""
        if self._camera and self._camera.isOpened():
            width = int(self._camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self._camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return (width, height)
        return self.resolution


class LiDARDevice(HardwareDevice):
    """
    LiDAR device implementation for RPLIDAR and compatible sensors
    """
    
    def __init__(self, name: str, port: str, baud_rate: int = 115200, model: str = "RPLIDAR"):
        connection_info = ConnectionInfo(
            connection_type=ConnectionType.SERIAL,
            address=port,
            parameters={
                'baud_rate': baud_rate,
                'model': model
            }
        )
        
        super().__init__(name, connection_info)
        
        self.baud_rate = baud_rate
        self.model = model
        self._serial_connection = None
        self._scanning = False
        
        # LiDAR-specific capabilities based on model
        if model.upper() == "RPLIDAR":
            self.add_capability('scan_frequency', 10.0, "Scan frequency in Hz")
            self.add_capability('range_min', 0.15, "Minimum range in meters")
            self.add_capability('range_max', 12.0, "Maximum range in meters")
            self.add_capability('angle_resolution', 0.5, "Angular resolution in degrees")
        
        self.add_capability('model', model, "LiDAR model", configurable=False)
    
    def _establish_connection(self) -> bool:
        """Establish serial connection to LiDAR"""
        try:
            self._serial_connection = serial.Serial(
                port=self.connection_info.address,
                baudrate=self.baud_rate,
                timeout=1.0
            )
            
            # Wait for device initialization
            time.sleep(1.0)
            
            # Clear buffers
            self._serial_connection.flushInput()
            self._serial_connection.flushOutput()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to establish LiDAR connection: {e}")
            return False
    
    def _close_connection(self):
        """Close LiDAR connection"""
        if self._serial_connection and self._serial_connection.is_open:
            try:
                # Stop scanning if active
                self._stop_scan()
                self._serial_connection.close()
            except Exception as e:
                self.logger.error(f"Error closing LiDAR connection: {e}")
        
        self._serial_connection = None
    
    def _test_communication(self) -> bool:
        """Test LiDAR communication"""
        try:
            if not self._serial_connection or not self._serial_connection.is_open:
                return False
            
            # Send device info request for RPLIDAR
            if self.model.upper() == "RPLIDAR":
                # RPLIDAR get device info command
                self._serial_connection.write(b'\xA5\x50\x00\x00\x00\x00\x02')
                time.sleep(0.1)
                
                # Check for response
                if self._serial_connection.in_waiting > 0:
                    response = self._serial_connection.read(self._serial_connection.in_waiting)
                    return len(response) > 0
            
            return True  # Assume OK if no specific test available
            
        except Exception as e:
            self.logger.debug(f"LiDAR communication test failed: {e}")
            return False
    
    def _read_data(self) -> Optional[Dict[str, Any]]:
        """Read scan data from LiDAR"""
        try:
            if not self._serial_connection or not self._serial_connection.is_open:
                return None
            
            # This is a simplified implementation
            # Real LiDAR drivers would parse the specific protocol
            if self._serial_connection.in_waiting > 0:
                raw_data = self._serial_connection.read(self._serial_connection.in_waiting)
                
                # For demonstration, return mock scan data
                # Real implementation would parse the actual LiDAR protocol
                return {
                    'scan_data': {
                        'ranges': [],  # Would contain actual range measurements
                        'angles': [],  # Would contain corresponding angles
                        'intensities': []  # Would contain signal intensities
                    },
                    'timestamp': time.time(),
                    'scan_time': 0.1,  # Time to complete one scan
                    'range_min': self.get_capability('range_min').value,
                    'range_max': self.get_capability('range_max').value
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error reading LiDAR data: {e}")
            return None
    
    def _write_data(self, data: Dict[str, Any]) -> bool:
        """Send commands to LiDAR"""
        try:
            if not self._serial_connection or not self._serial_connection.is_open:
                return False
            
            # Handle scan control commands
            if 'start_scan' in data and data['start_scan']:
                return self._start_scan()
            elif 'stop_scan' in data and data['stop_scan']:
                return self._stop_scan()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing LiDAR data: {e}")
            return False
    
    def _start_scan(self) -> bool:
        """Start LiDAR scanning"""
        try:
            if self.model.upper() == "RPLIDAR":
                # RPLIDAR start scan command
                self._serial_connection.write(b'\xA5\x20\x00\x00\x00\x00\x02')
                self._scanning = True
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error starting LiDAR scan: {e}")
            return False
    
    def _stop_scan(self) -> bool:
        """Stop LiDAR scanning"""
        try:
            if self.model.upper() == "RPLIDAR":
                # RPLIDAR stop scan command
                self._serial_connection.write(b'\xA5\x25\x00\x00\x00\x00\x02')
                self._scanning = False
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error stopping LiDAR scan: {e}")
            return False
    
    def is_scanning(self) -> bool:
        """Check if LiDAR is currently scanning"""
        return self._scanning