"""Sensor Fusion Node - Integrates multiple sensors using Extended Kalman Filter."""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import numpy as np
from typing import Optional
import time

from sensor_msgs.msg import LaserScan, Imu
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, TwistStamped
from std_msgs.msg import String
import tf2_ros
from tf2_ros import TransformException

from .extended_kalman_filter import ExtendedKalmanFilter


class SensorFusionNode(Node):
    """
    ROS2 node for multi-sensor fusion using Extended Kalman Filter.
    
    Fuses data from:
    - LiDAR (via SLAM pose estimates)
    - Camera (via visual odometry)
    - IMU (orientation and angular velocity)
    - Wheel odometry (velocity estimates)
    """
    
    def __init__(self):
        super().__init__('sensor_fusion_node')
        
        # Initialize Extended Kalman Filter
        self.ekf = ExtendedKalmanFilter()
        
        # Sensor timeout thresholds (seconds)
        self.declare_parameter('lidar_timeout', 1.0)
        self.declare_parameter('camera_timeout', 1.0)
        self.declare_parameter('imu_timeout', 0.5)
        self.declare_parameter('odom_timeout', 0.5)
        
        # Update rate
        self.declare_parameter('update_rate', 50.0)  # Hz
        
        # Sensor availability flags
        self.sensor_available = {
            'lidar': False,
            'camera': False,
            'imu': False,
            'odometry': False
        }
        
        # Last sensor update times
        self.last_sensor_time = {
            'lidar': 0.0,
            'camera': 0.0,
            'imu': 0.0,
            'odometry': 0.0
        }
        
        # QoS profile for sensor data
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Subscribers
        self.lidar_sub = self.create_subscription(
            PoseStamped,
            '/slam_pose',  # From SLAM system
            self.lidar_callback,
            10
        )
        
        self.camera_sub = self.create_subscription(
            PoseStamped,
            '/visual_odometry/pose',  # From visual odometry
            self.camera_callback,
            10
        )
        
        self.imu_sub = self.create_subscription(
            Imu,
            '/imu',
            self.imu_callback,
            sensor_qos
        )
        
        self.odom_sub = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            sensor_qos
        )
        
        # Publishers
        self.fused_pose_pub = self.create_publisher(
            PoseWithCovarianceStamped,
            '/fused_pose',
            10
        )
        
        self.fused_velocity_pub = self.create_publisher(
            TwistStamped,
            '/fused_velocity',
            10
        )
        
        self.status_pub = self.create_publisher(
            String,
            '/sensor_fusion/status',
            10
        )
        
        # TF broadcaster
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        
        # Timer for prediction and publishing
        update_rate = self.get_parameter('update_rate').value
        self.timer = self.create_timer(1.0 / update_rate, self.update_callback)
        
        # Last update time for dt calculation
        self.last_update_time = self.get_clock().now()
        
        self.get_logger().info('Sensor Fusion Node initialized')
        self.get_logger().info('Waiting for sensor data...')
        
    def lidar_callback(self, msg: PoseStamped):
        """Process LiDAR SLAM pose estimate."""
        # Extract position and orientation
        x = msg.pose.position.x
        y = msg.pose.position.y
        
        # Convert quaternion to euler angle (yaw)
        quat = msg.pose.orientation
        theta = np.arctan2(
            2.0 * (quat.w * quat.z + quat.x * quat.y),
            1.0 - 2.0 * (quat.y * quat.y + quat.z * quat.z)
        )
        
        # Update EKF with LiDAR measurement
        measurement = np.array([x, y, theta])
        self.ekf.update_lidar(measurement)
        
        # Update sensor status
        self.sensor_available['lidar'] = True
        self.last_sensor_time['lidar'] = time.time()
        
    def camera_callback(self, msg: PoseStamped):
        """Process camera visual odometry estimate."""
        # Extract position and orientation
        x = msg.pose.position.x
        y = msg.pose.position.y
        
        # Convert quaternion to euler angle (yaw)
        quat = msg.pose.orientation
        theta = np.arctan2(
            2.0 * (quat.w * quat.z + quat.x * quat.y),
            1.0 - 2.0 * (quat.y * quat.y + quat.z * quat.z)
        )
        
        # Update EKF with camera measurement
        measurement = np.array([x, y, theta])
        self.ekf.update_camera(measurement)
        
        # Update sensor status
        self.sensor_available['camera'] = True
        self.last_sensor_time['camera'] = time.time()
        
    def imu_callback(self, msg: Imu):
        """Process IMU measurement."""
        # Extract orientation (yaw)
        quat = msg.orientation
        theta = np.arctan2(
            2.0 * (quat.w * quat.z + quat.x * quat.y),
            1.0 - 2.0 * (quat.y * quat.y + quat.z * quat.z)
        )
        
        # Extract angular velocity
        omega = msg.angular_velocity.z
        
        # Update EKF with IMU measurement
        measurement = np.array([theta, omega])
        self.ekf.update_imu(measurement)
        
        # Update sensor status
        self.sensor_available['imu'] = True
        self.last_sensor_time['imu'] = time.time()
        
    def odom_callback(self, msg: Odometry):
        """Process wheel odometry measurement."""
        # Extract velocities
        vx = msg.twist.twist.linear.x
        vy = msg.twist.twist.linear.y
        omega = msg.twist.twist.angular.z
        
        # Update EKF with odometry measurement
        measurement = np.array([vx, vy, omega])
        self.ekf.update_odometry(measurement)
        
        # Update sensor status
        self.sensor_available['odometry'] = True
        self.last_sensor_time['odometry'] = time.time()
        
    def check_sensor_timeouts(self):
        """Check for sensor timeouts and adjust reliability."""
        current_time = time.time()
        
        timeouts = {
            'lidar': self.get_parameter('lidar_timeout').value,
            'camera': self.get_parameter('camera_timeout').value,
            'imu': self.get_parameter('imu_timeout').value,
            'odometry': self.get_parameter('odom_timeout').value
        }
        
        for sensor, timeout in timeouts.items():
            time_since_update = current_time - self.last_sensor_time[sensor]
            
            if time_since_update > timeout:
                if self.sensor_available[sensor]:
                    self.get_logger().warn(f'{sensor.upper()} sensor timeout detected')
                    self.sensor_available[sensor] = False
                    # Reduce reliability to near zero
                    self.ekf.set_reliability(sensor, 0.1)
            else:
                if not self.sensor_available[sensor] and time_since_update < timeout:
                    self.get_logger().info(f'{sensor.upper()} sensor recovered')
                    self.sensor_available[sensor] = True
                    # Restore default reliability
                    default_reliability = {
                        'lidar': 0.9,
                        'camera': 0.7,
                        'imu': 0.8,
                        'odometry': 0.6
                    }
                    self.ekf.set_reliability(sensor, default_reliability[sensor])
                    
    def update_callback(self):
        """Main update loop - prediction and publishing."""
        # Calculate dt
        current_time = self.get_clock().now()
        dt = (current_time - self.last_update_time).nanoseconds / 1e9
        self.last_update_time = current_time
        
        # Check for sensor timeouts
        self.check_sensor_timeouts()
        
        # Prediction step (no control input for now)
        self.ekf.predict(None, dt)
        
        # Get fused state
        state, covariance = self.ekf.get_state()
        x, y, theta, vx, vy, omega = state
        
        # Publish fused pose
        pose_msg = PoseWithCovarianceStamped()
        pose_msg.header.stamp = current_time.to_msg()
        pose_msg.header.frame_id = 'map'
        
        pose_msg.pose.pose.position.x = x
        pose_msg.pose.pose.position.y = y
        pose_msg.pose.pose.position.z = 0.0
        
        # Convert yaw to quaternion
        pose_msg.pose.pose.orientation.x = 0.0
        pose_msg.pose.pose.orientation.y = 0.0
        pose_msg.pose.pose.orientation.z = np.sin(theta / 2.0)
        pose_msg.pose.pose.orientation.w = np.cos(theta / 2.0)
        
        # Set covariance (6x6, but we only use position and orientation)
        pose_cov = np.zeros((6, 6))
        pose_cov[:3, :3] = covariance[:3, :3]
        pose_msg.pose.covariance = pose_cov.flatten().tolist()
        
        self.fused_pose_pub.publish(pose_msg)
        
        # Publish fused velocity
        vel_msg = TwistStamped()
        vel_msg.header.stamp = current_time.to_msg()
        vel_msg.header.frame_id = 'base_link'
        
        vel_msg.twist.linear.x = vx
        vel_msg.twist.linear.y = vy
        vel_msg.twist.angular.z = omega
        
        self.fused_velocity_pub.publish(vel_msg)
        
        # Publish status
        active_sensors = [s for s, available in self.sensor_available.items() if available]
        status_msg = String()
        status_msg.data = f"Active sensors: {', '.join(active_sensors) if active_sensors else 'None'}"
        self.status_pub.publish(status_msg)


def main(args=None):
    """Main entry point."""
    rclpy.init(args=args)
    node = SensorFusionNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
