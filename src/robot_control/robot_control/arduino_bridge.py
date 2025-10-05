#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
import serial
import serial.tools.list_ports
import time
import yaml
import os

from std_msgs.msg import Int32, Float32, Bool, String
from sensor_msgs.msg import Imu, Range
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster
from robot_interfaces.msg import EmergencyStop

from .hardware_discovery import HardwareDiscovery
from .device_abstraction import DeviceManager, DeviceStatus
from .device_implementations import ArduinoDevice

class ArduinoBridge(Node):
    def __init__(self):
        super().__init__('arduino_bridge')
        
        # Declare parameters
        self.declare_parameter('auto_discover', True)
        self.declare_parameter('fallback_port', '/dev/ttyACM0')
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('timeout', 1.0)
        self.declare_parameter('write_timeout', 1.0)
        self.declare_parameter('start_delimiter', '<')
        self.declare_parameter('end_delimiter', '>')
        self.declare_parameter('field_separator', ',')
        self.declare_parameter('debug', True)
        self.declare_parameter('reconnect_interval', 5.0)
        
        # Get parameters
        self.auto_discover = self.get_parameter('auto_discover').value
        self.fallback_port = self.get_parameter('fallback_port').value
        self.baud_rate = self.get_parameter('baud_rate').value
        self.timeout = self.get_parameter('timeout').value
        self.write_timeout = self.get_parameter('write_timeout').value
        self.start_delimiter = self.get_parameter('start_delimiter').value
        self.end_delimiter = self.get_parameter('end_delimiter').value
        self.field_separator = self.get_parameter('field_separator').value
        self.debug = self.get_parameter('debug').value
        self.reconnect_interval = self.get_parameter('reconnect_interval').value
        
        # Hardware discovery and device management
        self.hardware_discovery = None
        self.device_manager = DeviceManager()
        self.arduino_device = None
        self.connected = False
        
        # Motor commands
        self.left_motor_cmd = 0
        self.right_motor_cmd = 0
        
        # Safety system integration
        self.emergency_stop_active = False
        self.last_heartbeat_time = self.get_clock().now()
        
        # Encoder data
        self.left_encoder = 0
        self.right_encoder = 0
        self.last_encoder_left = 0
        self.last_encoder_right = 0
        self.last_encoder_time = self.get_clock().now()
        
        # Odometry
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.last_odom_update = self.get_clock().now()
        
        # Setup publishers
        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        self.left_encoder_pub = self.create_publisher(Int32, 'encoder/left', 10)
        self.right_encoder_pub = self.create_publisher(Int32, 'encoder/right', 10)
        
        # Setup subscribers
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            '/cmd_vel_limited',  # Subscribe to filtered commands from safety system
            self.cmd_vel_callback,
            10
        )
        
        # Safety system integration
        self.emergency_stop_sub = self.create_subscription(
            EmergencyStop,
            '/emergency_stop',
            self.emergency_stop_callback,
            10
        )
        
        # Publishers for safety system
        self.component_heartbeat_pub = self.create_publisher(
            String, '/component_heartbeat', 10)
        self.emergency_stop_ack_pub = self.create_publisher(
            String, '/emergency_stop_ack', 10)
        self.recovery_ready_pub = self.create_publisher(
            String, '/recovery_ready', 10)
        
        # TF broadcaster
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # Timer for reading from serial
        self.serial_timer = self.create_timer(0.01, self.serial_read_callback)  # 100Hz
        
        # Safety system heartbeat timer
        self.heartbeat_timer = self.create_timer(1.0, self.send_heartbeat)  # 1Hz
        
        # Initialize hardware discovery if enabled
        if self.auto_discover:
            self.hardware_discovery = HardwareDiscovery()
            
        # Connect to Arduino using auto-discovery or fallback
        self.connect_arduino()
        
        self.get_logger().info('Arduino bridge node started with auto-discovery enabled' if self.auto_discover else 'Arduino bridge node started with manual configuration')
    
    def connect_arduino(self):
        """Attempt to connect to Arduino using auto-discovery or fallback."""
        if self.auto_discover and self.hardware_discovery:
            self.get_logger().info('Using hardware discovery to find Arduino...')
            
            # Discover Arduino devices
            devices = self.hardware_discovery.discover_all_devices()
            arduino_devices = [dev for dev in devices.values() if dev.device_type == 'arduino' and dev.status == 'available']
            
            if arduino_devices:
                # Use the first available Arduino
                arduino_info = arduino_devices[0]
                self.get_logger().info(f'Found Arduino: {arduino_info.name} on {arduino_info.port}')
                
                # Create Arduino device instance
                self.arduino_device = ArduinoDevice(
                    name=arduino_info.name,
                    port=arduino_info.port,
                    baud_rate=self.baud_rate,
                    timeout=self.timeout
                )
                
                # Register device with manager
                self.device_manager.register_device(self.arduino_device)
                
                # Add status callback
                self.arduino_device.add_status_callback(self._on_arduino_status_change)
                
                # Connect to device
                if self.arduino_device.connect():
                    self.connected = True
                    self.get_logger().info(f'Successfully connected to Arduino via auto-discovery')
                    self.send_config()
                else:
                    self.get_logger().error('Failed to connect to discovered Arduino')
                    self.connected = False
            else:
                self.get_logger().warning('No Arduino devices found via auto-discovery, using fallback')
                self._connect_fallback()
        else:
            self.get_logger().info('Auto-discovery disabled, using fallback port')
            self._connect_fallback()
    
    def _connect_fallback(self):
        """Connect using fallback port configuration."""
        self.get_logger().info(f'Connecting to Arduino on fallback port {self.fallback_port}...')
        
        # Create Arduino device with fallback port
        self.arduino_device = ArduinoDevice(
            name="Arduino_Fallback",
            port=self.fallback_port,
            baud_rate=self.baud_rate,
            timeout=self.timeout
        )
        
        # Register device with manager
        self.device_manager.register_device(self.arduino_device)
        
        # Add status callback
        self.arduino_device.add_status_callback(self._on_arduino_status_change)
        
        # Connect to device
        if self.arduino_device.connect():
            self.connected = True
            self.get_logger().info(f'Connected to Arduino on fallback port {self.fallback_port}')
            self.send_config()
        else:
            self.get_logger().error(f'Failed to connect to Arduino on fallback port {self.fallback_port}')
            self.connected = False
    
    def _on_arduino_status_change(self, status: DeviceStatus):
        """Handle Arduino device status changes."""
        if status == DeviceStatus.CONNECTED:
            self.connected = True
            self.get_logger().info('Arduino reconnected successfully')
            self.send_config()
        elif status == DeviceStatus.DISCONNECTED or status == DeviceStatus.ERROR:
            self.connected = False
            self.get_logger().warning(f'Arduino connection lost: {status.value}')
        elif status == DeviceStatus.RECONNECTING:
            self.get_logger().info('Arduino attempting reconnection...')
    

    
    def cmd_vel_callback(self, msg):
        """Handle incoming cmd_vel messages."""
        # Check emergency stop status
        if self.emergency_stop_active:
            # Force zero commands during emergency stop
            self.left_motor_cmd = 0
            self.right_motor_cmd = 0
            self.send_motor_commands()
            return
        
        # Convert twist to motor commands (differential drive)
        # This is a simple implementation - you might want to use the cmd_vel_to_motors node instead
        linear = msg.linear.x
        angular = msg.angular.z
        
        # Simple differential drive model
        wheel_sep = 0.3  # meters
        wheel_radius = 0.05  # meters
        
        # Convert to wheel speeds (rad/s)
        left_speed = (linear - angular * wheel_sep / 2.0) / wheel_radius
        right_speed = (linear + angular * wheel_sep / 2.0) / wheel_radius
        
        # Convert to PWM values (simplified)
        max_pwm = 255
        max_speed = 6.28  # rad/s (adjust based on your motor)
        
        self.left_motor_cmd = int((left_speed / max_speed) * max_pwm)
        self.right_motor_cmd = int((right_speed / max_speed) * max_pwm)
        
        # Clamp values
        self.left_motor_cmd = max(-max_pwm, min(max_pwm, self.left_motor_cmd))
        self.right_motor_cmd = max(-max_pwm, min(max_pwm, self.right_motor_cmd))
        
        # Send motor commands to Arduino
        self.send_motor_commands()
    
    def send_motor_commands(self):
        """Send motor commands to Arduino."""
        if not self.connected or not self.arduino_device:
            return
            
        # Use device abstraction layer to send motor commands
        motor_data = {
            'motor_speeds': {
                'left': self.left_motor_cmd,
                'right': self.right_motor_cmd
            }
        }
        
        success = self.arduino_device.write(motor_data)
        if not success:
            self.get_logger().warning('Failed to send motor commands to Arduino')
    
    def send_config(self):
        """Send configuration to Arduino."""
        if not self.connected or not self.arduino_device:
            return
            
        # Send configuration through device abstraction layer
        config_data = {
            'config': {
                'pid_kp': 1.0,
                'pid_ki': 0.1,
                'pid_kd': 0.05
            }
        }
        
        success = self.arduino_device.write(config_data)
        if success:
            self.get_logger().info('Configuration sent to Arduino')
        else:
            self.get_logger().warning('Failed to send configuration to Arduino')
    
    def serial_read_callback(self):
        """Read and process data from Arduino using device abstraction layer."""
        if not self.connected or not self.arduino_device:
            return
            
        try:
            # Read data through device abstraction layer
            data = self.arduino_device.read()
            
            if data:
                # Process encoder data
                if 'encoders' in data:
                    encoder_data = data['encoders']
                    self.process_encoder_data([str(encoder_data['left']), str(encoder_data['right'])])
                
                # Debug output
                if self.debug:
                    self.get_logger().debug(f'Received data from Arduino: {data}')
                        
        except Exception as e:
            self.get_logger().error(f'Error reading Arduino data: {e}')
    
    def process_encoder_data(self, data):
        """Process encoder data from Arduino."""
        if len(data) < 2:
            return
            
        try:
            # Parse encoder values
            left_ticks = int(data[0])
            right_ticks = int(data[1])
            
            # Update encoder values
            self.left_encoder = left_ticks
            self.right_encoder = right_ticks
            
            # Publish encoder values
            left_msg = Int32()
            left_msg.data = left_ticks
            self.left_encoder_pub.publish(left_msg)
            
            right_msg = Int32()
            right_msg.data = right_ticks
            self.right_encoder_pub.publish(right_msg)
            
            # Update odometry
            self.update_odometry(left_ticks, right_ticks)
            
        except (ValueError, IndexError) as e:
            self.get_logger().warn(f'Failed to parse encoder data: {data}, error: {str(e)}')
    
    def update_odometry(self, left_ticks, right_ticks):
        """Update robot odometry based on encoder ticks."""
        # Get current time
        current_time = self.get_clock().now()
        dt = (current_time - self.last_odom_update).nanoseconds / 1e9  # Convert to seconds
        
        if dt <= 0:
            return
            
        # Calculate distance traveled by each wheel
        # ticks_per_rev = 20  # Update this based on your encoder
        # wheel_circumference = 0.314  # meters (2 * pi * radius)
        # distance_per_tick = wheel_circumference / ticks_per_rev
        
        # For now, just use the difference in ticks
        left_delta = left_ticks - self.last_encoder_left
        right_delta = right_ticks - self.last_encoder_right
        
        # Update last encoder values
        self.last_encoder_left = left_ticks
        self.last_encoder_right = right_ticks
        self.last_odom_update = current_time
        
        # Simple odometry calculation (improve with proper model)
        # This is a placeholder - you should implement proper odometry calculation
        # based on your robot's kinematics and encoder resolution
        
        # Publish odometry message
        odom_msg = Odometry()
        odom_msg.header.stamp = current_time.to_msg()
        odom_msg.header.frame_id = 'odom'
        odom_msg.child_frame_id = 'base_footprint'
        
        # Set position (placeholder values)
        odom_msg.pose.pose.position.x = self.x
        odom_msg.pose.pose.position.y = self.y
        odom_msg.pose.pose.position.z = 0.0
        
        # Set orientation (quaternion from yaw)
        from math import sin, cos
        from geometry_msgs.msg import Quaternion
        odom_msg.pose.pose.orientation = Quaternion(
            x=0.0,
            y=0.0,
            z=sin(self.theta / 2.0),
            w=cos(self.theta / 2.0)
        )
        
        # Set twist (placeholder values)
        odom_msg.twist.twist.linear.x = 0.0
        odom_msg.twist.twist.linear.y = 0.0
        odom_msg.twist.twist.angular.z = 0.0
        
        # Publish the odometry message
        self.odom_pub.publish(odom_msg)
        
        # Publish transform
        t = TransformStamped()
        t.header.stamp = current_time.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_footprint'
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation = odom_msg.pose.pose.orientation
        
        # Send the transform
        self.tf_broadcaster.sendTransform(t)
    
    def process_imu_data(self, data):
        """Process IMU data from Arduino (if available)."""
        # Implement IMU data processing if your Arduino has an IMU
        pass
    
    def destroy_node(self):
        """Clean shutdown of the Arduino bridge."""
        try:
            # Stop motors before exiting
            self.left_motor_cmd = 0
            self.right_motor_cmd = 0
            self.send_motor_commands()
            
            # Disconnect Arduino device
            if self.arduino_device:
                self.arduino_device.disconnect()
            
            # Cleanup device manager
            if self.device_manager:
                self.device_manager.destroy_node()
                
            # Cleanup hardware discovery
            if self.hardware_discovery:
                self.hardware_discovery.destroy_node()
                
        except Exception as e:
            self.get_logger().error(f'Error during cleanup: {e}')
        
        super().destroy_node()
    
    def emergency_stop_callback(self, msg: EmergencyStop) -> None:
        """Handle emergency stop messages from safety system"""
        self.emergency_stop_active = msg.active
        
        if msg.active:
            # Immediately stop motors
            self.left_motor_cmd = 0
            self.right_motor_cmd = 0
            self.send_motor_commands()
            
            # Acknowledge emergency stop
            ack_msg = String()
            ack_msg.data = "arduino_bridge"
            self.emergency_stop_ack_pub.publish(ack_msg)
            
            self.get_logger().warn(f"Emergency stop activated: {msg.reason}")
        else:
            # Signal ready for recovery
            recovery_msg = String()
            recovery_msg.data = "arduino_bridge"
            self.recovery_ready_pub.publish(recovery_msg)
            
            self.get_logger().info("Emergency stop cleared - Arduino bridge ready")
    
    def send_heartbeat(self) -> None:
        """Send heartbeat to watchdog system"""
        try:
            heartbeat_msg = String()
            heartbeat_msg.data = "arduino_bridge"
            self.component_heartbeat_pub.publish(heartbeat_msg)
            self.last_heartbeat_time = self.get_clock().now()
        except Exception as e:
            self.get_logger().error(f"Failed to send heartbeat: {e}")

def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = ArduinoBridge()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
