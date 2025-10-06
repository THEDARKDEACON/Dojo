#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32, Int16
import math

class CmdVelToMotors(Node):
    """
    Convert geometry_msgs/Twist to motor speed commands for differential drive robot.
    
    Subscribes:
        /cmd_vel - Target twist (linear and angular velocity)
        
    Publishes:
        /left_motor/speed - Left motor speed command
        /right_motor/speed - Right motor speed command
    """
    def __init__(self):
        super().__init__('cmd_vel_to_motors')
        
        # Parameters
        self.declare_parameters(
            namespace='',
            parameters=[
                ('wheel_separation', 0.3),  # Distance between wheels (meters)
                ('wheel_radius', 0.05),     # Wheel radius (meters)
                ('max_linear_speed', 0.5),  # Max linear speed (m/s)
                ('max_angular_speed', 1.0), # Max angular speed (rad/s)
                ('max_motor_speed', 255),   # Max motor speed (PWM value)
                ('min_motor_speed', 50),    # Min motor speed to overcome friction
                ('invert_left_motor', False),  # Invert left motor direction
                ('invert_right_motor', False), # Invert right motor direction
            ]
        )
        
        # Get parameters
        self.wheel_separation = self.get_parameter('wheel_separation').value
        self.wheel_radius = self.get_parameter('wheel_radius').value
        self.max_linear_speed = self.get_parameter('max_linear_speed').value
        self.max_angular_speed = self.get_parameter('max_angular_speed').value
        self.max_motor_speed = self.get_parameter('max_motor_speed').value
        self.min_motor_speed = self.get_parameter('min_motor_speed').value
        self.invert_left_motor = self.get_parameter('invert_left_motor').value
        self.invert_right_motor = self.get_parameter('invert_right_motor').value
        
        # Calculate max wheel speed (rad/s)
        self.max_wheel_speed = self.max_linear_speed / self.wheel_radius
        
        # Publishers
        self.left_motor_pub = self.create_publisher(Int16, 'left_motor/speed', 10)
        self.right_motor_pub = self.create_publisher(Int16, 'right_motor/speed', 10)
        
        # Subscriber
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            'cmd_vel_teleop',
            self.cmd_vel_callback,
            10
        )
        self.safety_sub = self.create_subscription(
            Twist,
            'cmd_vel_safety',
            self.safety_callback,
            10
        )
        self.get_logger().info('cmd_vel_to_motors node started')
    
    def cmd_vel_callback(self, msg):
        """Convert twist message to motor speeds."""
        # Get linear and angular velocities
        linear_x = msg.linear.x
        angular_z = msg.angular.z
        
        # Limit velocities to max values
        linear_x = max(-self.max_linear_speed, min(linear_x, self.max_linear_speed))
        angular_z = max(-self.max_angular_speed, min(angular_z, self.max_angular_speed))
        
        # Calculate wheel speeds (rad/s)
        left_speed = (linear_x - angular_z * self.wheel_separation / 2.0) / self.wheel_radius
        right_speed = (linear_x + angular_z * self.wheel_separation / 2.0) / self.wheel_radius
        
        # Normalize wheel speeds to [-1.0, 1.0]
        left_normalized = left_speed / self.max_wheel_speed
        right_normalized = right_speed / self.max_wheel_speed
        
        # Scale to motor speed range
        left_motor = int(left_normalized * self.max_motor_speed)
        right_motor = int(right_normalized * self.max_motor_speed)
        
        # Apply motor inversion
        if self.invert_left_motor:
            left_motor *= -1
        if self.invert_right_motor:
            right_motor *= -1
        
        # Apply minimum speed (deadband)
        left_motor = self.apply_deadband(left_motor)
        right_motor = self.apply_deadband(right_motor)
        
        # Publish motor commands
        left_msg = Int16()
        left_msg.data = left_motor
        self.left_motor_pub.publish(left_msg)
        
        right_msg = Int16()
        right_msg.data = right_motor
        self.right_motor_pub.publish(right_msg)
        
        # Debug output
        self.get_logger().debug(
            f'Linear: {linear_x:.2f} m/s, Angular: {angular_z:.2f} rad/s -> '
            f'Left: {left_motor}, Right: {right_motor}'
        )
    
    def safety_callback(self, msg):
        """Handle safety stop commands."""
        # When a safety message is received, immediately stop the robot
        stop_msg = Int16()
        stop_msg.data = 0
        self.left_motor_pub.publish(stop_msg)
        self.right_motor_pub.publish(stop_msg)
        self.get_logger().warn('SAFETY STOP ACTIVATED')

    def apply_deadband(self, motor_speed):
        """Apply deadband to motor speed to overcome friction."""
        if abs(motor_speed) < self.min_motor_speed:
            return 0
        
        # Scale the remaining range
        sign = 1 if motor_speed > 0 else -1
        scaled = (abs(motor_speed) - self.min_motor_speed) / (self.max_motor_speed - self.min_motor_speed)
        return int(sign * (self.min_motor_speed + scaled * (self.max_motor_speed - self.min_motor_speed)))

def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = CmdVelToMotors()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
