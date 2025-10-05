#!/usr/bin/env python3
"""
Enhanced Camera Driver with Auto-Discovery and Capability Detection

This module provides an advanced camera driver that automatically discovers
camera devices, detects their capabilities, and provides adaptive configuration.
"""

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import Image, CameraInfo
from std_msgs.msg import Header, String
from robot_interfaces.msg import EmergencyStop
from cv_bridge import CvBridge
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import time

from .hardware_discovery import HardwareDiscovery
from .device_abstraction import DeviceManager, DeviceStatus
from .device_implementations import CameraDevice


class CameraDriver(Node):
    """
    Enhanced Camera Driver with auto-discovery and capability detection
    
    Features:
    - Automatic camera device discovery
    - Capability detection (resolution, formats, fps)
    - Adaptive configuration based on capabilities
    - Multiple camera support
    - Automatic reconnection
    """
    
    def __init__(self):
        super().__init__('camera_driver')
        
        # Declare parameters
        self.declare_parameter('auto_discover', True)
        self.declare_parameter('fallback_device', '/dev/video0')
        self.declare_parameter('preferred_resolution', [640, 480])
        self.declare_parameter('preferred_fps', 30.0)
        self.declare_parameter('frame_id', 'camera_link')
        self.declare_parameter('camera_name', 'camera')
        self.declare_parameter('publish_camera_info', True)
        self.declare_parameter('adaptive_quality', True)
        self.declare_parameter('max_cameras', 4)
        
        # Get parameters
        self.auto_discover = self.get_parameter('auto_discover').value
        self.fallback_device = self.get_parameter('fallback_device').value
        self.preferred_resolution = self.get_parameter('preferred_resolution').value
        self.preferred_fps = self.get_parameter('preferred_fps').value
        self.frame_id = self.get_parameter('frame_id').value
        self.camera_name = self.get_parameter('camera_name').value
        self.publish_camera_info = self.get_parameter('publish_camera_info').value
        self.adaptive_quality = self.get_parameter('adaptive_quality').value
        self.max_cameras = self.get_parameter('max_cameras').value
        
        # Initialize components
        self.bridge = CvBridge()
        self.hardware_discovery = None
        self.device_manager = DeviceManager()
        
        # Camera management
        self.camera_devices: Dict[str, CameraDevice] = {}
        self.publishers: Dict[str, Dict] = {}
        
        # Performance monitoring
        self.frame_counts: Dict[str, int] = {}
        self.last_fps_check: Dict[str, float] = {}
        self.actual_fps: Dict[str, float] = {}
        
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
        
        # Discover and initialize cameras
        self.initialize_cameras()
        
        # Timer for publishing frames
        self.timer = self.create_timer(0.033, self.capture_and_publish)  # ~30 FPS
        
        # Timer for performance monitoring
        self.perf_timer = self.create_timer(5.0, self.monitor_performance)
        
        # Safety system heartbeat timer
        self.heartbeat_timer = self.create_timer(1.0, self.send_heartbeat)
        
        self.get_logger().info(f'Camera driver initialized with {len(self.camera_devices)} cameras')
    
    def initialize_cameras(self):
        """Initialize camera devices using auto-discovery or fallback."""
        if self.auto_discover and self.hardware_discovery:
            self.get_logger().info('Discovering camera devices...')
            
            # Discover all devices
            devices = self.hardware_discovery.discover_all_devices()
            camera_devices = [dev for dev in devices.values() 
                            if dev.device_type == 'camera' and dev.status == 'available']
            
            if camera_devices:
                # Limit number of cameras
                camera_devices = camera_devices[:self.max_cameras]
                
                for i, camera_info in enumerate(camera_devices):
                    self._setup_camera_device(camera_info.name, camera_info.port, camera_info.capabilities)
            else:
                self.get_logger().warning('No cameras found via auto-discovery, using fallback')
                self._setup_fallback_camera()
        else:
            self.get_logger().info('Auto-discovery disabled, using fallback camera')
            self._setup_fallback_camera()
    
    def _setup_camera_device(self, name: str, device_path: str, capabilities: Dict):
        """Setup a camera device with detected capabilities."""
        try:
            # Determine optimal resolution
            resolution = self._select_optimal_resolution(capabilities)
            fps = self._select_optimal_fps(capabilities)
            
            self.get_logger().info(f'Setting up camera {name}: {resolution[0]}x{resolution[1]} @ {fps} FPS')
            
            # Create camera device
            camera_device = CameraDevice(
                name=name,
                device_path=device_path,
                resolution=tuple(resolution),
                fps=fps
            )
            
            # Register with device manager
            self.device_manager.register_device(camera_device)
            
            # Add status callback
            camera_device.add_status_callback(
                lambda status, cam_name=name: self._on_camera_status_change(cam_name, status)
            )
            
            # Connect to camera
            if camera_device.connect():
                self.camera_devices[name] = camera_device
                self._setup_publishers(name)
                
                # Initialize performance tracking
                self.frame_counts[name] = 0
                self.last_fps_check[name] = time.time()
                self.actual_fps[name] = 0.0
                
                self.get_logger().info(f'Successfully initialized camera: {name}')
            else:
                self.get_logger().error(f'Failed to connect to camera: {name}')
                
        except Exception as e:
            self.get_logger().error(f'Error setting up camera {name}: {e}')
    
    def _setup_fallback_camera(self):
        """Setup fallback camera with default configuration."""
        name = f"{self.camera_name}_fallback"
        
        camera_device = CameraDevice(
            name=name,
            device_path=self.fallback_device,
            resolution=tuple(self.preferred_resolution),
            fps=self.preferred_fps
        )
        
        # Register with device manager
        self.device_manager.register_device(camera_device)
        
        # Add status callback
        camera_device.add_status_callback(
            lambda status: self._on_camera_status_change(name, status)
        )
        
        # Connect to camera
        if camera_device.connect():
            self.camera_devices[name] = camera_device
            self._setup_publishers(name)
            
            # Initialize performance tracking
            self.frame_counts[name] = 0
            self.last_fps_check[name] = time.time()
            self.actual_fps[name] = 0.0
            
            self.get_logger().info(f'Fallback camera initialized: {name}')
        else:
            self.get_logger().error(f'Failed to initialize fallback camera: {name}')
    
    def _setup_publishers(self, camera_name: str):
        """Setup ROS publishers for a camera."""
        # Create unique topic names for multiple cameras
        if len(self.camera_devices) > 1:
            topic_prefix = f'/{camera_name}'
        else:
            topic_prefix = f'/{self.camera_name}'
        
        # Image publisher
        image_pub = self.create_publisher(
            Image,
            f'{topic_prefix}/image_raw',
            10
        )
        
        # Camera info publisher (if enabled)
        camera_info_pub = None
        if self.publish_camera_info:
            camera_info_pub = self.create_publisher(
                CameraInfo,
                f'{topic_prefix}/camera_info',
                10
            )
        
        self.publishers[camera_name] = {
            'image': image_pub,
            'camera_info': camera_info_pub,
            'topic_prefix': topic_prefix
        }
    
    def _select_optimal_resolution(self, capabilities: Dict) -> List[int]:
        """Select optimal resolution based on capabilities and preferences."""
        if 'supported_resolutions' in capabilities:
            available_resolutions = capabilities['supported_resolutions']
            
            # Try to find preferred resolution
            preferred = tuple(self.preferred_resolution)
            if preferred in available_resolutions:
                return list(preferred)
            
            # Find closest resolution
            target_pixels = preferred[0] * preferred[1]
            best_resolution = min(available_resolutions, 
                                key=lambda res: abs(res[0] * res[1] - target_pixels))
            return list(best_resolution)
        
        # Use preferred resolution as fallback
        return self.preferred_resolution
    
    def _select_optimal_fps(self, capabilities: Dict) -> float:
        """Select optimal FPS based on capabilities and preferences."""
        # For now, use preferred FPS
        # In a full implementation, you would check supported frame rates
        return self.preferred_fps
    
    def _on_camera_status_change(self, camera_name: str, status: DeviceStatus):
        """Handle camera device status changes."""
        if status == DeviceStatus.CONNECTED:
            self.get_logger().info(f'Camera {camera_name} reconnected')
        elif status == DeviceStatus.DISCONNECTED or status == DeviceStatus.ERROR:
            self.get_logger().warning(f'Camera {camera_name} connection lost: {status.value}')
        elif status == DeviceStatus.RECONNECTING:
            self.get_logger().info(f'Camera {camera_name} attempting reconnection...')
    
    def capture_and_publish(self):
        """Capture frames from all cameras and publish them."""
        current_time = self.get_clock().now()
        
        for camera_name, camera_device in self.camera_devices.items():
            try:
                # Read frame from camera
                data = camera_device.read()
                
                if data and 'frame' in data:
                    frame = data['frame']
                    
                    # Apply adaptive quality if enabled
                    if self.adaptive_quality:
                        frame = self._apply_adaptive_quality(camera_name, frame)
                    
                    # Convert to ROS Image message
                    image_msg = self.bridge.cv2_to_imgmsg(frame, 'bgr8')
                    image_msg.header.stamp = current_time.to_msg()
                    image_msg.header.frame_id = self.frame_id
                    
                    # Publish image
                    if camera_name in self.publishers:
                        self.publishers[camera_name]['image'].publish(image_msg)
                        
                        # Publish camera info if enabled
                        if self.publishers[camera_name]['camera_info']:
                            camera_info_msg = self._create_camera_info(camera_name, data, current_time)
                            self.publishers[camera_name]['camera_info'].publish(camera_info_msg)
                    
                    # Update frame count for performance monitoring
                    self.frame_counts[camera_name] += 1
                    
            except Exception as e:
                self.get_logger().error(f'Error capturing from camera {camera_name}: {e}')
    
    def _apply_adaptive_quality(self, camera_name: str, frame: np.ndarray) -> np.ndarray:
        """Apply adaptive quality adjustments based on performance."""
        # Simple adaptive quality: reduce resolution if FPS is too low
        if camera_name in self.actual_fps:
            current_fps = self.actual_fps[camera_name]
            target_fps = self.preferred_fps
            
            if current_fps < target_fps * 0.8:  # If FPS is 20% below target
                # Reduce resolution by 25%
                height, width = frame.shape[:2]
                new_width = int(width * 0.75)
                new_height = int(height * 0.75)
                frame = cv2.resize(frame, (new_width, new_height))
                
                self.get_logger().debug(f'Applied quality reduction for {camera_name}: {width}x{height} -> {new_width}x{new_height}')
        
        return frame
    
    def _create_camera_info(self, camera_name: str, frame_data: Dict, timestamp) -> CameraInfo:
        """Create camera info message."""
        camera_info = CameraInfo()
        camera_info.header.stamp = timestamp.to_msg()
        camera_info.header.frame_id = self.frame_id
        
        # Get current resolution from frame data
        if 'resolution' in frame_data:
            width, height = frame_data['resolution']
        else:
            height, width = frame_data['frame'].shape[:2]
        
        camera_info.width = width
        camera_info.height = height
        
        # Simple camera model (you should calibrate for real applications)
        camera_info.distortion_model = "plumb_bob"
        camera_info.d = [0.0, 0.0, 0.0, 0.0, 0.0]  # No distortion
        
        # Camera matrix (simplified)
        fx = fy = width  # Focal length approximation
        cx = width / 2.0
        cy = height / 2.0
        
        camera_info.k = [fx, 0.0, cx,
                        0.0, fy, cy,
                        0.0, 0.0, 1.0]
        
        camera_info.r = [1.0, 0.0, 0.0,
                        0.0, 1.0, 0.0,
                        0.0, 0.0, 1.0]
        
        camera_info.p = [fx, 0.0, cx, 0.0,
                        0.0, fy, cy, 0.0,
                        0.0, 0.0, 1.0, 0.0]
        
        return camera_info
    
    def monitor_performance(self):
        """Monitor camera performance and log statistics."""
        current_time = time.time()
        
        for camera_name in self.camera_devices.keys():
            if camera_name in self.frame_counts and camera_name in self.last_fps_check:
                time_diff = current_time - self.last_fps_check[camera_name]
                
                if time_diff > 0:
                    fps = self.frame_counts[camera_name] / time_diff
                    self.actual_fps[camera_name] = fps
                    
                    self.get_logger().info(f'Camera {camera_name} performance: {fps:.1f} FPS')
                    
                    # Reset counters
                    self.frame_counts[camera_name] = 0
                    self.last_fps_check[camera_name] = current_time
    
    def reconfigure_camera(self, camera_name: str, resolution: Tuple[int, int], fps: float) -> bool:
        """Dynamically reconfigure a camera."""
        if camera_name not in self.camera_devices:
            self.get_logger().error(f'Camera {camera_name} not found')
            return False
        
        camera_device = self.camera_devices[camera_name]
        
        config_data = {
            'resolution': resolution,
            'fps': fps
        }
        
        success = camera_device.write(config_data)
        if success:
            self.get_logger().info(f'Reconfigured camera {camera_name}: {resolution[0]}x{resolution[1]} @ {fps} FPS')
        else:
            self.get_logger().error(f'Failed to reconfigure camera {camera_name}')
        
        return success
    
    def get_camera_capabilities(self, camera_name: str) -> Optional[Dict]:
        """Get capabilities of a specific camera."""
        if camera_name not in self.camera_devices:
            return None
        
        camera_device = self.camera_devices[camera_name]
        return {name: cap.value for name, cap in camera_device.capabilities.items()}
    
    def list_cameras(self) -> List[str]:
        """Get list of available camera names."""
        return list(self.camera_devices.keys())
    
    def destroy_node(self):
        """Clean shutdown of camera driver."""
        try:
            # Disconnect all cameras
            for camera_device in self.camera_devices.values():
                camera_device.disconnect()
            
            # Cleanup device manager
            if self.device_manager:
                self.device_manager.destroy_node()
            
            # Cleanup hardware discovery
            if self.hardware_discovery:
                self.hardware_discovery.destroy_node()
                
        except Exception as e:
            self.get_logger().error(f'Error during camera driver cleanup: {e}')
        
        super().destroy_node()

    def emergency_stop_callback(self, msg: EmergencyStop) -> None:
        """Handle emergency stop messages from safety system"""
        self.emergency_stop_active = msg.active
        
        if msg.active:
            # Pause camera capture during emergency stop to reduce system load
            for camera_name, camera_device in self.camera_devices.items():
                if camera_device.is_connected():
                    self.get_logger().info(f"Pausing camera {camera_name} due to emergency stop")
            
            # Acknowledge emergency stop
            ack_msg = String()
            ack_msg.data = "camera_driver"
            self.emergency_stop_ack_pub.publish(ack_msg)
            
            self.get_logger().warn(f"Emergency stop activated: {msg.reason}")
        else:
            # Resume camera operations
            for camera_name, camera_device in self.camera_devices.items():
                if camera_device.is_connected():
                    self.get_logger().info(f"Resuming camera {camera_name} after emergency stop")
            
            # Signal ready for recovery
            recovery_msg = String()
            recovery_msg.data = "camera_driver"
            self.recovery_ready_pub.publish(recovery_msg)
            
            self.get_logger().info("Emergency stop cleared - Camera driver ready")
    
    def send_heartbeat(self) -> None:
        """Send heartbeat to watchdog system"""
        try:
            heartbeat_msg = String()
            heartbeat_msg.data = "camera_driver"
            self.component_heartbeat_pub.publish(heartbeat_msg)
            self.last_heartbeat_time = self.get_clock().now()
        except Exception as e:
            self.get_logger().error(f"Failed to send heartbeat: {e}")

def main(args=None):
    """Main entry point for camera driver."""
    rclpy.init(args=args)
    
    try:
        camera_driver = CameraDriver()
        rclpy.spin(camera_driver)
    except KeyboardInterrupt:
        pass
    finally:
        if 'camera_driver' in locals():
            camera_driver.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()