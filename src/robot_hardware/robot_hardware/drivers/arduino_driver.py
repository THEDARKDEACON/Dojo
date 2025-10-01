#!/usr/bin/env python3
"""
Unified Arduino Driver for Dojo Robot
Consolidates functionality from arduino_bridge, ros2arduino_bridge, and robot_control
"""

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
try:
    from rclpy.impl.rcutils_logger import RcutilsLoggingError as RCLError
except ImportError:
    from rclpy.impl.rcutils_logger import RCLError
import serial
import serial.tools.list_ports
import time
import threading
import json

from std_msgs.msg import Int32, Float32, String
from sensor_msgs.msg import Imu, Range
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster

class ArduinoDriver(Node):
    """Unified Arduino communication driver"""
    
    def __init__(self):
        super().__init__('arduino_driver')
        
        # Declare parameters with defaults
        self._declare_parameters()
        
        # ROSArduinoBridge protocol state
        self.encoder_left = 0
        self.encoder_right = 0
        self.last_encoder_left = 0
        self.last_encoder_right = 0
        
        # Initialize hardware connection
        self.serial_conn = None
        self.connected = False
        self.connection_lock = threading.Lock()
        
        # Initialize data storage
        self._init_data_storage()
        
        # Setup ROS interfaces
        self._setup_publishers()
        self._setup_subscribers()
        
        # Start connection and communication threads
        self._start_communication()
        
        self.get_logger().info('Arduino Driver initialized')
    
    def _declare_parameters(self):
        """Declare all ROS parameters"""
        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('baud_rate', 57600)  # ROSArduinoBridge uses 57600
        self.declare_parameter('timeout', 1.0)
        self.declare_parameter('write_timeout', 1.0)
        self.declare_parameter('debug', True)
        self.declare_parameter('reconnect_interval', 5.0)
        # ROSArduinoBridge protocol - always uses single-letter commands
        self.declare_parameter('use_rosarduino_bridge', True)
        
        # Motor parameters
        self.declare_parameter('motor_max', 255)
        self.declare_parameter('motor_min', 0)
        self.declare_parameter('wheel_base', 0.2)
        self.declare_parameter('wheel_radius', 0.033)
        
        # Encoder parameters  
        self.declare_parameter('encoder_ticks_per_rev', 20)
        self.declare_parameter('wheel_circumference', 0.314)
        
        # ROSArduinoBridge PID parameters
        self.declare_parameter('pid_kp', 20)
        self.declare_parameter('pid_kd', 12)
        self.declare_parameter('pid_ki', 0)
        self.declare_parameter('pid_ko', 50) 
   
    def _init_data_storage(self):
        """Initialize data storage variables"""
        self.motor_commands = {'left': 0, 'right': 0}
        self.encoder_data = {'left': 0, 'right': 0}
        self.sensor_data = {}
        self.last_encoder_time = time.time()
        
    def _setup_publishers(self):
        """Setup ROS publishers"""
        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        self.imu_pub = self.create_publisher(Imu, 'imu/data', 10)
        self.range_pub = self.create_publisher(Range, 'ultrasonic', 10)
        self.status_pub = self.create_publisher(String, 'arduino_status', 10)
        
        # TF broadcaster for odometry
        self.tf_broadcaster = TransformBroadcaster(self)
        
    def _setup_subscribers(self):
        """Setup ROS subscribers"""
        self.cmd_vel_sub = self.create_subscription(
            Twist, 'cmd_vel', self._cmd_vel_callback, 10)
        
    def _start_communication(self):
        """Start communication threads"""
        # Connection management thread
        self.connection_thread = threading.Thread(target=self._manage_connection)
        self.connection_thread.daemon = True
        self.connection_thread.start()
        
        # Data reading thread for ROSArduinoBridge
        self.read_thread = threading.Thread(target=self._rosarduino_read_loop)
        self.read_thread.daemon = True
        self.read_thread.start()
        
        # Encoder polling thread for ROSArduinoBridge
        self.encoder_thread = threading.Thread(target=self._encoder_polling_loop)
        self.encoder_thread.daemon = True
        self.encoder_thread.start()
        
    def _manage_connection(self):
        """Manage Arduino connection with auto-reconnect"""
        while rclpy.ok():
            if not self.connected:
                self._attempt_connection()
            time.sleep(self.get_parameter('reconnect_interval').value)
    
    def _attempt_connection(self):
        """Attempt to connect to Arduino"""
        try:
            port = self.get_parameter('port').value
            baud_rate = self.get_parameter('baud_rate').value
            timeout = self.get_parameter('timeout').value
            
            with self.connection_lock:
                if self.serial_conn:
                    self.serial_conn.close()
                
                self.serial_conn = serial.Serial(
                    port=port,
                    baudrate=baud_rate,
                    timeout=timeout,
                    write_timeout=self.get_parameter('write_timeout').value
                )
                
                self.connected = True
                self.get_logger().info(f'Connected to Arduino on {port}')
                self._publish_status('CONNECTED')
                
        except Exception as e:
            self.connected = False
            self.get_logger().warn(f'Failed to connect to Arduino: {e}')
            self._publish_status('DISCONNECTED')  
  
    def _rosarduino_read_loop(self):
        """Read responses from ROSArduinoBridge"""
        while rclpy.ok():
            if self.connected and self.serial_conn:
                try:
                    if self.serial_conn.in_waiting:
                        raw = self.serial_conn.readline()
                        line = raw.decode('utf-8', errors='ignore').strip()
                        if line and self.get_parameter('debug').value:
                            self.get_logger().debug(f'Arduino response: {line}')
                except Exception as e:
                    self.get_logger().error(f'Error reading Arduino: {e}')
                    self.connected = False
            time.sleep(0.01)
    
    def _encoder_polling_loop(self):
        """Poll encoders from ROSArduinoBridge at regular intervals"""
        while rclpy.ok():
            if self.connected:
                try:
                    self._read_encoders()
                except Exception as e:
                    self.get_logger().error(f'Error reading encoders: {e}')
                    self.connected = False
            time.sleep(0.05)  # 20Hz encoder polling
    
    def _send_command(self, command):
        """Send command to ROSArduinoBridge and get response"""
        if not self.connected or not self.serial_conn:
            return ""
            
        try:
            with self.connection_lock:
                self.serial_conn.write(command.encode('utf-8'))
                time.sleep(0.01)  # Small delay for Arduino processing
                response = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                return response
        except Exception as e:
            self.get_logger().error(f'Command failed: {e}')
            self.connected = False
            return ""
    
    def _read_encoders(self):
        """Read encoder values using ROSArduinoBridge 'e' command"""
        response = self._send_command("e\r")
        if response:
            try:
                parts = response.split(' ')
                if len(parts) >= 2:
                    left_ticks = int(parts[0])
                    right_ticks = int(parts[1])
                    
                    # Calculate velocities and publish odometry
                    current_time = time.time()
                    dt = current_time - self.last_encoder_time
                    
                    if dt > 0 and hasattr(self, 'last_encoder_time'):
                        # Calculate wheel velocities
                        ticks_per_rev = self.get_parameter('encoder_ticks_per_rev').value
                        wheel_circumference = self.get_parameter('wheel_circumference').value
                        
                        left_delta = left_ticks - self.encoder_left
                        right_delta = right_ticks - self.encoder_right
                        
                        left_velocity = (left_delta / ticks_per_rev) * wheel_circumference / dt
                        right_velocity = (right_delta / ticks_per_rev) * wheel_circumference / dt
                        
                        # Publish odometry
                        self._publish_odometry(left_velocity, right_velocity, current_time)
                    
                    # Update stored values
                    self.encoder_left = left_ticks
                    self.encoder_right = right_ticks
                    self.last_encoder_time = current_time
                    
            except (ValueError, IndexError) as e:
                self.get_logger().debug(f'Encoder parsing error: {e}')
    
    def get_baud_rate(self):
        """Get Arduino baud rate"""
        response = self._send_command("b\r")
        try:
            return int(response)
        except ValueError:
            return None
    
    def read_analog_pin(self, pin):
        """Read analog pin value"""
        response = self._send_command(f"a {pin}\r")
        try:
            return int(response)
        except ValueError:
            return None
    
    def read_digital_pin(self, pin):
        """Read digital pin value"""
        response = self._send_command(f"d {pin}\r")
        try:
            return int(response)
        except ValueError:
            return None 
   
    def _publish_odometry(self, left_vel, right_vel, timestamp):
        """Publish odometry data"""
        # Calculate robot velocities
        wheel_base = self.get_parameter('wheel_base').value
        linear_vel = (left_vel + right_vel) / 2.0
        angular_vel = (right_vel - left_vel) / wheel_base
        
        # Create odometry message
        odom_msg = Odometry()
        odom_msg.header.stamp = self.get_clock().now().to_msg()
        odom_msg.header.frame_id = 'odom'
        odom_msg.child_frame_id = 'base_link'
        
        # Set velocities
        odom_msg.twist.twist.linear.x = linear_vel
        odom_msg.twist.twist.angular.z = angular_vel
        
        self.odom_pub.publish(odom_msg)
    
    def _publish_ultrasonic(self, distance):
        """Publish ultrasonic sensor data"""
        range_msg = Range()
        range_msg.header.stamp = self.get_clock().now().to_msg()
        range_msg.header.frame_id = 'ultrasonic_link'
        range_msg.radiation_type = Range.ULTRASOUND
        range_msg.field_of_view = 0.26  # ~15 degrees
        range_msg.min_range = 0.02
        range_msg.max_range = 4.0
        range_msg.range = distance / 100.0  # Convert cm to meters
        
        self.range_pub.publish(range_msg)
    
    def _parse_imu_data(self, imu_fields):
        """Parse and publish IMU data if available"""
        # Placeholder for IMU data parsing
        # Implement based on your Arduino's IMU output format
        pass
    
    def _publish_status(self, status):
        """Publish Arduino connection status"""
        status_msg = String()
        status_msg.data = status
        self.status_pub.publish(status_msg)
    
    def _cmd_vel_callback(self, msg):
        """Handle cmd_vel messages and send to Arduino"""
        if not self.connected:
            return
            
        # Convert twist to motor commands
        linear = msg.linear.x
        angular = msg.angular.z
        wheel_base = self.get_parameter('wheel_base').value
        wheel_radius = self.get_parameter('wheel_radius').value

        # Calculate per-wheel linear velocities (m/s)
        left_lin = linear - (angular * wheel_base / 2.0)
        right_lin = linear + (angular * wheel_base / 2.0)

        # Convert to ticks per frame for ROSArduinoBridge
        # ROSArduinoBridge PID runs at 30Hz, so frame = 1/30 second
        ticks_per_rev = self.get_parameter('encoder_ticks_per_rev').value
        wheel_circumference = self.get_parameter('wheel_circumference').value
        
        # Convert linear velocity to ticks per frame
        left_ticks_per_frame = int((left_lin / wheel_circumference) * ticks_per_rev / 30.0)
        right_ticks_per_frame = int((right_lin / wheel_circumference) * ticks_per_rev / 30.0)
        
        self._send_motor_commands(left_ticks_per_frame, right_ticks_per_frame)

    def _send_motor_commands(self, left_ticks, right_ticks):
        """Send motor commands to ROSArduinoBridge using 'm' command"""
        if not self.connected or not self.serial_conn:
            return
            
        try:
            # ROSArduinoBridge expects: "m <left_ticks> <right_ticks>\r"
            command = f"m {left_ticks} {right_ticks}\r"
            
            with self.connection_lock:
                self.serial_conn.write(command.encode('utf-8'))
                
            if self.get_parameter('debug').value:
                self.get_logger().debug(f'Sent: {command.strip()}')
                
        except Exception as e:
            self.get_logger().error(f'Failed to send motor commands: {e}')
            self.connected = False
    
    def reset_encoders(self):
        """Reset encoder counts to zero"""
        response = self._send_command("r\r")
        if "OK" in response:
            self.encoder_left = 0
            self.encoder_right = 0
            self.get_logger().info("Encoders reset")
    
    def set_pid_parameters(self, kp=None, kd=None, ki=None, ko=None):
        """Update PID parameters on Arduino"""
        if kp is None:
            kp = self.get_parameter('pid_kp').value
        if kd is None:
            kd = self.get_parameter('pid_kd').value
        if ki is None:
            ki = self.get_parameter('pid_ki').value
        if ko is None:
            ko = self.get_parameter('pid_ko').value
            
        command = f"u {kp}:{kd}:{ki}:{ko}\r"
        response = self._send_command(command)
        if "OK" in response:
            self.get_logger().info(f"PID updated: Kp={kp}, Kd={kd}, Ki={ki}, Ko={ko}")
        else:
            self.get_logger().warn("Failed to update PID parameters")
    
    def cleanup(self):
        """Cleanup resources"""
        self.connected = False
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except:
                pass

def main(args=None):
    rclpy.init(args=args)
    
    try:
        arduino_driver = ArduinoDriver()
        rclpy.spin(arduino_driver)
    except KeyboardInterrupt:
        pass
    finally:
        if 'arduino_driver' in locals():
            arduino_driver.cleanup()
        try:
            rclpy.shutdown()
        except RCLError:
            pass

if __name__ == '__main__':
    main()