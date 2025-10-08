#!/usr/bin/env python3
"""
Direct Arduino Driver for Bypass Mode

This driver provides simplified Arduino communication bypassing the complex
safety and hardware management systems. It uses the ROSArduinoBridge protocol
directly for basic motion control.
"""

import rclpy
from rclpy.node import Node
import serial
import serial.tools.list_ports
import time
import threading
from typing import Optional, Tuple, Dict, Any
from math import sin, cos, pi

from std_msgs.msg import Int32, String
from geometry_msgs.msg import Twist, Quaternion, TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster


class DirectArduinoDriver(Node):
    """
    Direct Arduino communication driver for bypass mode.
    
    This class provides simplified Arduino communication using the ROSArduinoBridge
    protocol without safety system interference. It's designed to match the
    robosync system behavior for basic motion control.
    """
    
    def __init__(self, node_name: str = 'direct_arduino_driver'):
        super().__init__(node_name)
        
        # Robosync-compatible parameters (from requirements)
        self.wheel_base = 0.19  # meters (robosync value)
        self.wheel_radius = 0.035  # meters (robosync value)
        self.encoder_ticks_per_rev = 20  # robosync value
        self.max_motor_speed = 255  # PWM range
        
        # PID parameters (robosync values from requirements)
        self.pid_kp = 20.0
        self.pid_kd = 12.0
        self.pid_ki = 0.0
        self.pid_ko = 50
        
        # Communication parameters
        self.baud_rate = 115200  # robosync compatibility
        self.timeout = 1.0
        self.reconnect_interval = 5.0
        self.command_timeout = 0.5
        self.max_retries = 3
        
        # Connection management
        self.serial_connection: Optional[serial.Serial] = None
        self.connected = False
        self.connection_lock = threading.Lock()
        self.last_connection_attempt = 0
        
        # Auto-detection ports (in order of preference)
        self.port_candidates = ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0', '/dev/ttyUSB1']
        self.current_port = None
        
        # Encoder data
        self.left_encoder_ticks = 0
        self.right_encoder_ticks = 0
        self.last_encoder_left = 0
        self.last_encoder_right = 0
        self.last_encoder_time = self.get_clock().now()
        
        # Odometry
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.last_odom_update = self.get_clock().now()
        
        # Publishers
        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        self.left_encoder_pub = self.create_publisher(Int32, 'encoder/left', 10)
        self.right_encoder_pub = self.create_publisher(Int32, 'encoder/right', 10)
        self.status_pub = self.create_publisher(String, 'arduino_status', 10)
        
        # TF broadcaster
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # Timers
        self.encoder_timer = self.create_timer(0.05, self.read_encoders_callback)  # 20Hz
        self.status_timer = self.create_timer(1.0, self.publish_status)  # 1Hz
        
        # Initialize connection
        self.get_logger().info('DirectArduinoDriver initialized - attempting Arduino connection...')
        self.connect_arduino()
    
    def connect_arduino(self) -> bool:
        """
        Attempt to connect to Arduino with auto-detection and fallback.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        with self.connection_lock:
            current_time = time.time()
            
            # Rate limit connection attempts
            if current_time - self.last_connection_attempt < self.reconnect_interval:
                return self.connected
            
            self.last_connection_attempt = current_time
            
            # Close existing connection if any
            if self.serial_connection and self.serial_connection.is_open:
                try:
                    self.serial_connection.close()
                except Exception as e:
                    self.get_logger().debug(f'Error closing existing connection: {e}')
            
            # Try auto-detection first
            detected_port = self._auto_detect_arduino()
            if detected_port:
                self.port_candidates.insert(0, detected_port)  # Prioritize detected port
            
            # Try each port candidate
            for port in self.port_candidates:
                if self._try_connect_port(port):
                    self.current_port = port
                    self.connected = True
                    self.get_logger().info(f'Successfully connected to Arduino on {port}')
                    
                    # Send initial configuration
                    self._send_initial_config()
                    return True
            
            self.connected = False
            self.get_logger().warning('Failed to connect to Arduino on any port')
            return False
    
    def _auto_detect_arduino(self) -> Optional[str]:
        """
        Auto-detect Arduino port by scanning available serial ports.
        
        Returns:
            Optional[str]: Detected port path or None if not found
        """
        try:
            ports = serial.tools.list_ports.comports()
            for port in ports:
                # Look for Arduino-like devices
                if any(keyword in port.description.lower() for keyword in ['arduino', 'ch340', 'cp210', 'ftdi']):
                    self.get_logger().info(f'Detected potential Arduino device: {port.device} - {port.description}')
                    return port.device
        except Exception as e:
            self.get_logger().debug(f'Error during auto-detection: {e}')
        
        return None
    
    def _try_connect_port(self, port: str) -> bool:
        """
        Try to connect to a specific port.
        
        Args:
            port: Serial port path to try
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.get_logger().debug(f'Trying to connect to {port}...')
            
            # Create serial connection
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            
            # Wait for Arduino to initialize
            time.sleep(2.0)
            
            # Test connection with a simple command
            if self._test_connection():
                return True
            else:
                self.serial_connection.close()
                return False
                
        except Exception as e:
            self.get_logger().debug(f'Failed to connect to {port}: {e}')
            return False
    
    def _test_connection(self) -> bool:
        """
        Test Arduino connection by sending a simple command.
        
        Returns:
            bool: True if Arduino responds correctly, False otherwise
        """
        try:
            # Clear any pending data
            if self.serial_connection.in_waiting > 0:
                self.serial_connection.read_all()
            
            # Send encoder read command to test
            response = self._send_command('e')
            if response and response != 'Invalid Command':
                self.get_logger().debug(f'Arduino connection test successful: {response}')
                return True
            else:
                self.get_logger().debug(f'Arduino connection test failed: {response}')
                return False
                
        except Exception as e:
            self.get_logger().debug(f'Connection test error: {e}')
            return False
    
    def _send_command(self, command: str, retries: int = None) -> Optional[str]:
        """
        Send a command to Arduino using ROSArduinoBridge protocol.
        
        Args:
            command: Command string to send
            retries: Number of retries (uses self.max_retries if None)
            
        Returns:
            Optional[str]: Response from Arduino or None if failed
        """
        if not self.connected or not self.serial_connection:
            return None
        
        if retries is None:
            retries = self.max_retries
        
        for attempt in range(retries + 1):
            try:
                with self.connection_lock:
                    if not self.serial_connection.is_open:
                        return None
                    
                    # Clear input buffer
                    if self.serial_connection.in_waiting > 0:
                        self.serial_connection.read_all()
                    
                    # Send command with newline
                    cmd_bytes = f'{command}\r'.encode('utf-8')
                    self.serial_connection.write(cmd_bytes)
                    self.serial_connection.flush()
                    
                    # Read response with timeout
                    start_time = time.time()
                    response_bytes = b''
                    
                    while time.time() - start_time < self.command_timeout:
                        if self.serial_connection.in_waiting > 0:
                            byte = self.serial_connection.read(1)
                            response_bytes += byte
                            
                            # Check for end of response (newline or carriage return)
                            if byte in [b'\n', b'\r']:
                                break
                    
                    if response_bytes:
                        response = response_bytes.decode('utf-8').strip()
                        self.get_logger().debug(f'Arduino command "{command}" -> "{response}"')
                        return response
                    else:
                        self.get_logger().debug(f'Arduino command "{command}" -> timeout')
                        
            except Exception as e:
                self.get_logger().debug(f'Command send error (attempt {attempt + 1}): {e}')
                
                # On communication error, mark as disconnected and try to reconnect
                if attempt == retries:  # Last attempt
                    self.connected = False
                    self.get_logger().warning('Arduino communication lost - will attempt reconnection')
        
        return None
    
    def _send_initial_config(self):
        """Send initial configuration to Arduino."""
        try:
            # Set PID parameters using robosync values
            pid_command = f'u {self.pid_kp}:{self.pid_kd}:{self.pid_ki}:{self.pid_ko}'
            response = self._send_command(pid_command)
            
            if response and 'OK' in response:
                self.get_logger().info(f'PID parameters configured: Kp={self.pid_kp}, Kd={self.pid_kd}, Ki={self.pid_ki}, Ko={self.pid_ko}')
            else:
                self.get_logger().warning(f'Failed to set PID parameters: {response}')
                
        except Exception as e:
            self.get_logger().error(f'Error sending initial configuration: {e}')
    
    def send_motor_command(self, left_speed: float, right_speed: float) -> bool:
        """
        Send motor command to Arduino using 'm' command format.
        
        Args:
            left_speed: Left motor speed (-1.0 to 1.0)
            right_speed: Right motor speed (-1.0 to 1.0)
            
        Returns:
            bool: True if command sent successfully, False otherwise
        """
        if not self.connected:
            # Try to reconnect
            if not self.connect_arduino():
                return False
        
        try:
            # Convert speeds to motor ticks per frame using robosync parameters
            # This conversion matches the robosync system behavior
            left_ticks = int(left_speed * self.max_motor_speed)
            right_ticks = int(right_speed * self.max_motor_speed)
            
            # Clamp values to valid PWM range
            left_ticks = max(-self.max_motor_speed, min(self.max_motor_speed, left_ticks))
            right_ticks = max(-self.max_motor_speed, min(self.max_motor_speed, right_ticks))
            
            # Send motor command using ROSArduinoBridge 'm' format
            motor_command = f'm {left_ticks} {right_ticks}'
            response = self._send_command(motor_command, retries=self.max_retries)
            
            if response and ('OK' in response or response.strip() == ''):
                self.get_logger().debug(f'Motor command sent: left={left_ticks}, right={right_ticks}')
                return True
            else:
                self.get_logger().warning(f'Motor command failed: {response}')
                return False
                
        except Exception as e:
            self.get_logger().error(f'Error sending motor command: {e}')
            return False
    
    def send_velocity_command(self, linear_vel: float, angular_vel: float) -> bool:
        """
        Convert cmd_vel to motor commands using robosync-compatible kinematics.
        
        Args:
            linear_vel: Linear velocity in m/s
            angular_vel: Angular velocity in rad/s
            
        Returns:
            bool: True if command sent successfully, False otherwise
        """
        try:
            # Convert twist to wheel speeds using differential drive kinematics
            # Using robosync parameters: wheel_base=0.19m, wheel_radius=0.035m
            
            # Calculate wheel speeds (m/s)
            left_wheel_speed = linear_vel - (angular_vel * self.wheel_base / 2.0)
            right_wheel_speed = linear_vel + (angular_vel * self.wheel_base / 2.0)
            
            # Convert wheel speeds to motor speeds (normalized -1.0 to 1.0)
            # Maximum wheel speed in m/s (adjust based on motor capabilities)
            max_wheel_speed = 1.0  # m/s - robosync compatible limit
            
            left_motor_speed = left_wheel_speed / max_wheel_speed
            right_motor_speed = right_wheel_speed / max_wheel_speed
            
            # Clamp to valid range
            left_motor_speed = max(-1.0, min(1.0, left_motor_speed))
            right_motor_speed = max(-1.0, min(1.0, right_motor_speed))
            
            # Send motor commands
            return self.send_motor_command(left_motor_speed, right_motor_speed)
            
        except Exception as e:
            self.get_logger().error(f'Error converting velocity command: {e}')
            return False
    
    def read_encoders(self) -> Optional[Tuple[int, int]]:
        """
        Read encoder values from Arduino using 'e' command format.
        
        Returns:
            Optional[Tuple[int, int]]: (left_ticks, right_ticks) or None if failed
        """
        if not self.connected:
            return None
        
        try:
            response = self._send_command('e')
            
            if response:
                # Parse encoder response: "left_ticks right_ticks"
                parts = response.strip().split()
                if len(parts) >= 2:
                    left_ticks = int(parts[0])
                    right_ticks = int(parts[1])
                    
                    self.left_encoder_ticks = left_ticks
                    self.right_encoder_ticks = right_ticks
                    
                    return (left_ticks, right_ticks)
                else:
                    self.get_logger().debug(f'Invalid encoder response format: {response}')
            
        except Exception as e:
            self.get_logger().debug(f'Error reading encoders: {e}')
        
        return None
    
    def set_pid_parameters(self, kp: float, kd: float, ki: float, ko: int) -> bool:
        """
        Set PID parameters using 'u' command format.
        
        Args:
            kp: Proportional gain
            kd: Derivative gain  
            ki: Integral gain
            ko: Output scaling factor
            
        Returns:
            bool: True if parameters set successfully, False otherwise
        """
        if not self.connected:
            return False
        
        try:
            # Validate parameters
            if kp < 0 or kd < 0 or ki < 0 or ko <= 0:
                self.get_logger().error('Invalid PID parameters: all values must be non-negative, ko must be positive')
                return False
            
            # Send PID command using ROSArduinoBridge 'u' format
            pid_command = f'u {kp}:{kd}:{ki}:{ko}'
            response = self._send_command(pid_command)
            
            if response and 'OK' in response:
                self.pid_kp = kp
                self.pid_kd = kd
                self.pid_ki = ki
                self.pid_ko = ko
                self.get_logger().info(f'PID parameters updated: Kp={kp}, Kd={kd}, Ki={ki}, Ko={ko}')
                return True
            else:
                self.get_logger().warning(f'Failed to set PID parameters: {response}')
                return False
                
        except Exception as e:
            self.get_logger().error(f'Error setting PID parameters: {e}')
            return False
    
    def read_encoders_callback(self):
        """Timer callback to read encoders and update odometry."""
        encoder_data = self.read_encoders()
        
        if encoder_data:
            left_ticks, right_ticks = encoder_data
            
            # Publish encoder values
            left_msg = Int32()
            left_msg.data = left_ticks
            self.left_encoder_pub.publish(left_msg)
            
            right_msg = Int32()
            right_msg.data = right_ticks
            self.right_encoder_pub.publish(right_msg)
            
            # Update odometry
            self._update_odometry(left_ticks, right_ticks)
    
    def _update_odometry(self, left_ticks: int, right_ticks: int):
        """
        Update robot odometry based on encoder ticks using robosync parameters.
        
        Args:
            left_ticks: Current left encoder ticks
            right_ticks: Current right encoder ticks
        """
        current_time = self.get_clock().now()
        dt = (current_time - self.last_odom_update).nanoseconds / 1e9
        
        if dt <= 0:
            return
        
        # Calculate distance traveled by each wheel
        wheel_circumference = 2.0 * pi * self.wheel_radius
        distance_per_tick = wheel_circumference / self.encoder_ticks_per_rev
        
        # Calculate wheel distances
        left_delta_ticks = left_ticks - self.last_encoder_left
        right_delta_ticks = right_ticks - self.last_encoder_right
        
        left_distance = left_delta_ticks * distance_per_tick
        right_distance = right_delta_ticks * distance_per_tick
        
        # Calculate robot motion
        distance = (left_distance + right_distance) / 2.0
        delta_theta = (right_distance - left_distance) / self.wheel_base
        
        # Update robot pose
        self.x += distance * cos(self.theta + delta_theta / 2.0)
        self.y += distance * sin(self.theta + delta_theta / 2.0)
        self.theta += delta_theta
        
        # Calculate velocities
        linear_velocity = distance / dt
        angular_velocity = delta_theta / dt
        
        # Update last values
        self.last_encoder_left = left_ticks
        self.last_encoder_right = right_ticks
        self.last_odom_update = current_time
        
        # Publish odometry
        self._publish_odometry(current_time, linear_velocity, angular_velocity)
    
    def _publish_odometry(self, timestamp, linear_vel: float, angular_vel: float):
        """
        Publish odometry message and transform.
        
        Args:
            timestamp: Current timestamp
            linear_vel: Linear velocity (m/s)
            angular_vel: Angular velocity (rad/s)
        """
        # Create odometry message
        odom_msg = Odometry()
        odom_msg.header.stamp = timestamp.to_msg()
        odom_msg.header.frame_id = 'odom'
        odom_msg.child_frame_id = 'base_footprint'
        
        # Set position
        odom_msg.pose.pose.position.x = self.x
        odom_msg.pose.pose.position.y = self.y
        odom_msg.pose.pose.position.z = 0.0
        
        # Set orientation (quaternion from yaw)
        odom_msg.pose.pose.orientation = Quaternion(
            x=0.0,
            y=0.0,
            z=sin(self.theta / 2.0),
            w=cos(self.theta / 2.0)
        )
        
        # Set velocities
        odom_msg.twist.twist.linear.x = linear_vel
        odom_msg.twist.twist.linear.y = 0.0
        odom_msg.twist.twist.angular.z = angular_vel
        
        # Publish odometry
        self.odom_pub.publish(odom_msg)
        
        # Publish transform
        t = TransformStamped()
        t.header.stamp = timestamp.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_footprint'
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation = odom_msg.pose.pose.orientation
        
        self.tf_broadcaster.sendTransform(t)
    
    def publish_status(self):
        """Publish Arduino connection status."""
        status_msg = String()
        if self.connected:
            status_msg.data = f'Connected to Arduino on {self.current_port}'
        else:
            status_msg.data = 'Arduino disconnected - attempting reconnection'
        
        self.status_pub.publish(status_msg)
    
    def destroy_node(self):
        """Clean shutdown of the driver."""
        try:
            # Stop motors
            if self.connected:
                self.send_motor_command(0.0, 0.0)
            
            # Close serial connection
            with self.connection_lock:
                if self.serial_connection and self.serial_connection.is_open:
                    self.serial_connection.close()
                    
        except Exception as e:
            self.get_logger().error(f'Error during cleanup: {e}')
        
        super().destroy_node()


def main(args=None):
    """Main entry point for the direct Arduino driver."""
    rclpy.init(args=args)
    
    try:
        driver = DirectArduinoDriver()
        rclpy.spin(driver)
    except KeyboardInterrupt:
        pass
    finally:
        if 'driver' in locals():
            driver.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()