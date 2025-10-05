#!/usr/bin/env python3
"""
Device Abstraction Layer for Dojo Robot

This module provides a unified interface for hardware devices with automatic
reconnection logic and capability management.
"""

import time
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import String
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue


class DeviceStatus(Enum):
    """Device status enumeration"""
    UNKNOWN = "unknown"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class ConnectionType(Enum):
    """Connection type enumeration"""
    SERIAL = "serial"
    USB = "usb"
    NETWORK = "network"
    VIRTUAL = "virtual"


@dataclass
class DeviceCapability:
    """Represents a device capability"""
    name: str
    value: Any
    description: str = ""
    configurable: bool = True


@dataclass
class ConnectionInfo:
    """Connection information for a device"""
    connection_type: ConnectionType
    address: str  # Port, IP, etc.
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceHealth:
    """Device health information"""
    status: DeviceStatus
    last_communication: datetime
    error_count: int = 0
    last_error: Optional[str] = None
    uptime: timedelta = field(default_factory=lambda: timedelta(0))
    reconnect_attempts: int = 0


class HardwareDevice(ABC):
    """
    Abstract base class for all hardware devices
    
    Provides common functionality for device management, health monitoring,
    and automatic reconnection.
    """
    
    def __init__(self, name: str, connection_info: ConnectionInfo, logger: Optional[logging.Logger] = None):
        self.name = name
        self.connection_info = connection_info
        self.logger = logger or logging.getLogger(f"device.{name}")
        
        # Device state
        self.health = DeviceHealth(
            status=DeviceStatus.UNKNOWN,
            last_communication=datetime.now()
        )
        self.capabilities: Dict[str, DeviceCapability] = {}
        self.configuration: Dict[str, Any] = {}
        
        # Connection management
        self._connection = None
        self._connection_lock = threading.Lock()
        self._reconnect_thread = None
        self._should_reconnect = True
        self._reconnect_interval = 5.0  # seconds
        self._max_reconnect_attempts = 10
        
        # Callbacks
        self._status_callbacks: List[Callable[[DeviceStatus], None]] = []
        self._data_callbacks: List[Callable[[str, Any], None]] = []
        
        # Monitoring
        self._monitor_thread = None
        self._monitoring_active = False
        self._monitor_interval = 1.0  # seconds
        
        self.logger.info(f"Initialized device: {self.name}")
    
    @abstractmethod
    def _establish_connection(self) -> bool:
        """
        Establish connection to the device
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def _close_connection(self):
        """Close the device connection"""
        pass
    
    @abstractmethod
    def _test_communication(self) -> bool:
        """
        Test communication with the device
        
        Returns:
            True if communication successful, False otherwise
        """
        pass
    
    @abstractmethod
    def _read_data(self) -> Optional[Dict[str, Any]]:
        """
        Read data from the device
        
        Returns:
            Dictionary of data read from device, None if no data
        """
        pass
    
    @abstractmethod
    def _write_data(self, data: Dict[str, Any]) -> bool:
        """
        Write data to the device
        
        Args:
            data: Dictionary of data to write
            
        Returns:
            True if write successful, False otherwise
        """
        pass
    
    def connect(self) -> bool:
        """
        Connect to the device with automatic reconnection
        
        Returns:
            True if connection successful, False otherwise
        """
        with self._connection_lock:
            if self.health.status == DeviceStatus.CONNECTED:
                return True
            
            self._update_status(DeviceStatus.CONNECTING)
            
            try:
                if self._establish_connection():
                    self._update_status(DeviceStatus.CONNECTED)
                    self.health.reconnect_attempts = 0
                    self.health.error_count = 0
                    self.health.last_error = None
                    
                    # Start monitoring
                    self._start_monitoring()
                    
                    self.logger.info(f"Successfully connected to {self.name}")
                    return True
                else:
                    self._update_status(DeviceStatus.ERROR)
                    self.health.error_count += 1
                    self.health.last_error = "Connection failed"
                    return False
                    
            except Exception as e:
                self._update_status(DeviceStatus.ERROR)
                self.health.error_count += 1
                self.health.last_error = str(e)
                self.logger.error(f"Connection error for {self.name}: {e}")
                return False
    
    def disconnect(self):
        """Disconnect from the device"""
        with self._connection_lock:
            self._should_reconnect = False
            self._stop_monitoring()
            self._stop_reconnection()
            
            try:
                self._close_connection()
                self._update_status(DeviceStatus.DISCONNECTED)
                self.logger.info(f"Disconnected from {self.name}")
            except Exception as e:
                self.logger.error(f"Error disconnecting from {self.name}: {e}")
    
    def read(self) -> Optional[Dict[str, Any]]:
        """
        Read data from the device
        
        Returns:
            Dictionary of data read from device, None if no data or error
        """
        if self.health.status != DeviceStatus.CONNECTED:
            return None
        
        try:
            data = self._read_data()
            if data is not None:
                self.health.last_communication = datetime.now()
                
                # Notify data callbacks
                for callback in self._data_callbacks:
                    try:
                        callback(self.name, data)
                    except Exception as e:
                        self.logger.error(f"Error in data callback: {e}")
            
            return data
            
        except Exception as e:
            self.health.error_count += 1
            self.health.last_error = str(e)
            self.logger.error(f"Read error for {self.name}: {e}")
            self._handle_communication_error()
            return None
    
    def write(self, data: Dict[str, Any]) -> bool:
        """
        Write data to the device
        
        Args:
            data: Dictionary of data to write
            
        Returns:
            True if write successful, False otherwise
        """
        if self.health.status != DeviceStatus.CONNECTED:
            return False
        
        try:
            success = self._write_data(data)
            if success:
                self.health.last_communication = datetime.now()
            else:
                self.health.error_count += 1
                self.health.last_error = "Write operation failed"
            
            return success
            
        except Exception as e:
            self.health.error_count += 1
            self.health.last_error = str(e)
            self.logger.error(f"Write error for {self.name}: {e}")
            self._handle_communication_error()
            return False
    
    def add_capability(self, name: str, value: Any, description: str = "", configurable: bool = True):
        """Add a device capability"""
        self.capabilities[name] = DeviceCapability(
            name=name,
            value=value,
            description=description,
            configurable=configurable
        )
    
    def get_capability(self, name: str) -> Optional[DeviceCapability]:
        """Get a device capability by name"""
        return self.capabilities.get(name)
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configure the device
        
        Args:
            config: Configuration parameters
            
        Returns:
            True if configuration successful, False otherwise
        """
        try:
            # Validate configuration against capabilities
            for key, value in config.items():
                capability = self.get_capability(key)
                if capability and not capability.configurable:
                    self.logger.warning(f"Capability {key} is not configurable")
                    continue
                
                self.configuration[key] = value
            
            # Apply configuration (subclasses should override this)
            return self._apply_configuration(config)
            
        except Exception as e:
            self.logger.error(f"Configuration error for {self.name}: {e}")
            return False
    
    def _apply_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Apply configuration to the device (override in subclasses)
        
        Args:
            config: Configuration parameters
            
        Returns:
            True if configuration successful, False otherwise
        """
        return True
    
    def add_status_callback(self, callback: Callable[[DeviceStatus], None]):
        """Add a status change callback"""
        self._status_callbacks.append(callback)
    
    def add_data_callback(self, callback: Callable[[str, Any], None]):
        """Add a data received callback"""
        self._data_callbacks.append(callback)
    
    def _update_status(self, status: DeviceStatus):
        """Update device status and notify callbacks"""
        old_status = self.health.status
        self.health.status = status
        
        if old_status != status:
            self.logger.debug(f"Device {self.name} status changed: {old_status} -> {status}")
            
            # Notify status callbacks
            for callback in self._status_callbacks:
                try:
                    callback(status)
                except Exception as e:
                    self.logger.error(f"Error in status callback: {e}")
    
    def _handle_communication_error(self):
        """Handle communication errors and trigger reconnection if needed"""
        if self.health.status == DeviceStatus.CONNECTED:
            self._update_status(DeviceStatus.ERROR)
            
            # Start reconnection if enabled
            if self._should_reconnect and self.health.reconnect_attempts < self._max_reconnect_attempts:
                self._start_reconnection()
    
    def _start_reconnection(self):
        """Start automatic reconnection"""
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return
        
        self._reconnect_thread = threading.Thread(target=self._reconnection_loop, daemon=True)
        self._reconnect_thread.start()
    
    def _stop_reconnection(self):
        """Stop automatic reconnection"""
        self._should_reconnect = False
        if self._reconnect_thread:
            self._reconnect_thread.join(timeout=2.0)
    
    def _reconnection_loop(self):
        """Automatic reconnection loop"""
        while (self._should_reconnect and 
               self.health.status != DeviceStatus.CONNECTED and
               self.health.reconnect_attempts < self._max_reconnect_attempts):
            
            self.health.reconnect_attempts += 1
            self._update_status(DeviceStatus.RECONNECTING)
            
            self.logger.info(f"Attempting reconnection {self.health.reconnect_attempts}/{self._max_reconnect_attempts} for {self.name}")
            
            try:
                with self._connection_lock:
                    self._close_connection()
                    time.sleep(self._reconnect_interval)
                    
                    if self._establish_connection():
                        self._update_status(DeviceStatus.CONNECTED)
                        self.health.reconnect_attempts = 0
                        self.health.error_count = 0
                        self.health.last_error = None
                        self.logger.info(f"Reconnection successful for {self.name}")
                        return
                    
            except Exception as e:
                self.logger.error(f"Reconnection attempt failed for {self.name}: {e}")
            
            time.sleep(self._reconnect_interval)
        
        if self.health.reconnect_attempts >= self._max_reconnect_attempts:
            self.logger.error(f"Max reconnection attempts reached for {self.name}")
            self._update_status(DeviceStatus.ERROR)
    
    def _start_monitoring(self):
        """Start device health monitoring"""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
    
    def _stop_monitoring(self):
        """Stop device health monitoring"""
        self._monitoring_active = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
    
    def _monitoring_loop(self):
        """Device health monitoring loop"""
        while self._monitoring_active and self.health.status == DeviceStatus.CONNECTED:
            try:
                # Test communication periodically
                if not self._test_communication():
                    self.logger.warning(f"Communication test failed for {self.name}")
                    self._handle_communication_error()
                    break
                
                time.sleep(self._monitor_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop for {self.name}: {e}")
                break
    
    def get_diagnostics(self) -> DiagnosticStatus:
        """Get device diagnostics"""
        status = DiagnosticStatus()
        status.name = f"device/{self.name}"
        status.hardware_id = self.connection_info.address
        
        # Set status level
        if self.health.status == DeviceStatus.CONNECTED:
            status.level = DiagnosticStatus.OK
            status.message = "Device connected and operational"
        elif self.health.status == DeviceStatus.RECONNECTING:
            status.level = DiagnosticStatus.WARN
            status.message = f"Reconnecting (attempt {self.health.reconnect_attempts})"
        else:
            status.level = DiagnosticStatus.ERROR
            status.message = f"Device {self.health.status.value}"
        
        # Add key-value pairs
        status.values.append(KeyValue(key="status", value=self.health.status.value))
        status.values.append(KeyValue(key="connection_type", value=self.connection_info.connection_type.value))
        status.values.append(KeyValue(key="address", value=self.connection_info.address))
        status.values.append(KeyValue(key="error_count", value=str(self.health.error_count)))
        status.values.append(KeyValue(key="reconnect_attempts", value=str(self.health.reconnect_attempts)))
        
        if self.health.last_error:
            status.values.append(KeyValue(key="last_error", value=self.health.last_error))
        
        # Add capabilities
        for name, capability in self.capabilities.items():
            status.values.append(KeyValue(key=f"capability_{name}", value=str(capability.value)))
        
        return status
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.disconnect()
        except:
            pass


class DeviceManager(Node):
    """
    Device Manager for coordinating multiple hardware devices
    
    Provides centralized management of device lifecycle, health monitoring,
    and configuration.
    """
    
    def __init__(self):
        super().__init__('device_manager')
        
        self.logger = self.get_logger()
        self.devices: Dict[str, HardwareDevice] = {}
        
        # Publishers
        self.diagnostics_pub = self.create_publisher(
            DiagnosticArray,
            '/diagnostics/devices',
            10
        )
        
        # Timer for diagnostics publishing
        self.diagnostics_timer = self.create_timer(2.0, self._publish_diagnostics)
        
        self.logger.info("Device Manager initialized")
    
    def register_device(self, device: HardwareDevice) -> bool:
        """
        Register a device with the manager
        
        Args:
            device: Device to register
            
        Returns:
            True if registration successful, False otherwise
        """
        if device.name in self.devices:
            self.logger.warning(f"Device {device.name} already registered")
            return False
        
        self.devices[device.name] = device
        
        # Add status callback to monitor device
        device.add_status_callback(lambda status: self._on_device_status_change(device.name, status))
        
        self.logger.info(f"Registered device: {device.name}")
        return True
    
    def unregister_device(self, name: str) -> bool:
        """
        Unregister a device from the manager
        
        Args:
            name: Name of device to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        if name not in self.devices:
            self.logger.warning(f"Device {name} not registered")
            return False
        
        device = self.devices[name]
        device.disconnect()
        del self.devices[name]
        
        self.logger.info(f"Unregistered device: {name}")
        return True
    
    def get_device(self, name: str) -> Optional[HardwareDevice]:
        """Get a device by name"""
        return self.devices.get(name)
    
    def get_devices_by_type(self, device_type: str) -> List[HardwareDevice]:
        """Get all devices of a specific type"""
        # This would require adding device_type to HardwareDevice
        # For now, return empty list
        return []
    
    def connect_all_devices(self) -> Dict[str, bool]:
        """
        Connect all registered devices
        
        Returns:
            Dictionary mapping device names to connection success
        """
        results = {}
        for name, device in self.devices.items():
            results[name] = device.connect()
        
        return results
    
    def disconnect_all_devices(self):
        """Disconnect all registered devices"""
        for device in self.devices.values():
            device.disconnect()
    
    def _on_device_status_change(self, device_name: str, status: DeviceStatus):
        """Handle device status changes"""
        self.logger.debug(f"Device {device_name} status changed to {status.value}")
    
    def _publish_diagnostics(self):
        """Publish device diagnostics"""
        msg = DiagnosticArray()
        msg.header.stamp = self.get_clock().now().to_msg()
        
        for device in self.devices.values():
            msg.status.append(device.get_diagnostics())
        
        self.diagnostics_pub.publish(msg)
    
    def destroy_node(self):
        """Clean shutdown"""
        self.disconnect_all_devices()
        super().destroy_node()


def main(args=None):
    """Main entry point for device manager"""
    rclpy.init(args=args)
    
    try:
        device_manager = DeviceManager()
        rclpy.spin(device_manager)
    except KeyboardInterrupt:
        pass
    finally:
        if 'device_manager' in locals():
            device_manager.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()