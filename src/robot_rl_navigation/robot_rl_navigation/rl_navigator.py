#!/usr/bin/env python3
"""
RLNavigator: ROS2 node for RL-based navigation

This node uses a trained RL policy to navigate the robot. It includes:
- Policy loading and inference
- Confidence scoring for policy decisions
- Nav2 fallback mechanism
- Real-time navigation control
"""

import os
import numpy as np
import math
from typing import Optional, Tuple

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from geometry_msgs.msg import Twist, PoseStamped, Point
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry, Path
from std_msgs.msg import String, Float32
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient

# RL libraries
try:
    from stable_baselines3 import PPO, SAC
    from stable_baselines3.common.vec_env import VecNormalize, DummyVecEnv
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False


class RLNavigator(Node):
    """
    ROS2 node for RL-based navigation.
    
    Features:
    - Load trained RL policy
    - Compute actions from observations
    - Confidence-based Nav2 fallback
    - Real-time navigation control
    """
    
    def __init__(self):
        super().__init__('rl_navigator')
        
        # Declare parameters
        self.declare_parameter('model_path', '')
        self.declare_parameter('algorithm', 'ppo')  # 'ppo' or 'sac'
        self.declare_parameter('confidence_threshold', 0.7)
        self.declare_parameter('use_nav2_fallback', True)
        self.declare_parameter('max_linear_vel', 1.0)
        self.declare_parameter('max_angular_vel', 1.0)
        self.declare_parameter('lidar_rays', 64)
        self.declare_parameter('control_rate', 10.0)  # Hz
        
        # Get parameters
        self.model_path = self.get_parameter('model_path').value
        self.algorithm = self.get_parameter('algorithm').value
        self.confidence_threshold = self.get_parameter('confidence_threshold').value
        self.use_nav2_fallback = self.get_parameter('use_nav2_fallback').value
        self.max_linear_vel = self.get_parameter('max_linear_vel').value
        self.max_angular_vel = self.get_parameter('max_angular_vel').value
        self.lidar_rays = self.get_parameter('lidar_rays').value
        self.control_rate = self.get_parameter('control_rate').value
        
        # Robot state
        self.robot_pose = None
        self.robot_velocity = None
        self.lidar_data = None
        self.goal_position = None
        self.current_confidence = 0.0
        self.using_nav2 = False
        
        # RL policy
        self.policy = None
        self.vec_normalize = None
        self.load_policy()
        
        # QoS profile for sensors
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Subscribers
        self.lidar_sub = self.create_subscription(
            LaserScan,
            '/scan',
            self.lidar_callback,
            sensor_qos
        )
        
        self.odom_sub = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10
        )
        
        self.goal_sub = self.create_subscription(
            PoseStamped,
            '/rl_goal',
            self.goal_callback,
            10
        )
        
        # Publishers
        self.cmd_vel_pub = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )
        
        self.confidence_pub = self.create_publisher(
            Float32,
            '/rl_confidence',
            10
        )
        
        self.status_pub = self.create_publisher(
            String,
            '/rl_status',
            10
        )
        
        # Nav2 action client (for fallback)
        if self.use_nav2_fallback:
            self.nav2_client = ActionClient(
                self,
                NavigateToPose,
                'navigate_to_pose'
            )
        
        # Control timer
        self.control_timer = self.create_timer(
            1.0 / self.control_rate,
            self.control_loop
        )
        
        self.get_logger().info('RLNavigator initialized')
        if self.policy is not None:
            self.get_logger().info(f'Loaded {self.algorithm.upper()} policy from {self.model_path}')
        else:
            self.get_logger().warn('No policy loaded - will use Nav2 fallback only')
    
    def load_policy(self):
        """Load trained RL policy from checkpoint."""
        if not SB3_AVAILABLE:
            self.get_logger().error('stable-baselines3 not available')
            return
        
        if not self.model_path or not os.path.exists(self.model_path + '.zip'):
            self.get_logger().warn(f'Model path not found: {self.model_path}')
            return
        
        try:
            # Load model
            if self.algorithm == 'ppo':
                self.policy = PPO.load(self.model_path)
            elif self.algorithm == 'sac':
                self.policy = SAC.load(self.model_path)
            else:
                self.get_logger().error(f'Unknown algorithm: {self.algorithm}')
                return
            
            # Load normalization stats if available
            vec_normalize_path = os.path.join(
                os.path.dirname(self.model_path),
                'vec_normalize.pkl'
            )
            if os.path.exists(vec_normalize_path):
                self.vec_normalize = VecNormalize.load(
                    vec_normalize_path,
                    DummyVecEnv([lambda: None])
                )
                self.vec_normalize.training = False
                self.vec_normalize.norm_reward = False
            
            self.get_logger().info('Policy loaded successfully')
            
        except Exception as e:
            self.get_logger().error(f'Failed to load policy: {e}')
            self.policy = None
    
    def lidar_callback(self, msg: LaserScan):
        """Process LiDAR scan data."""
        # Downsample to fixed number of rays
        ranges = np.array(msg.ranges)
        ranges = np.nan_to_num(ranges, nan=msg.range_max, posinf=msg.range_max)
        
        # Downsample to lidar_rays
        indices = np.linspace(0, len(ranges) - 1, self.lidar_rays, dtype=int)
        self.lidar_data = ranges[indices]
    
    def odom_callback(self, msg: Odometry):
        """Process odometry data."""
        self.robot_pose = msg.pose.pose
        self.robot_velocity = msg.twist.twist
    
    def goal_callback(self, msg: PoseStamped):
        """Process goal position."""
        self.goal_position = msg.pose.position
        self.get_logger().info(
            f'New goal received: ({self.goal_position.x:.2f}, {self.goal_position.y:.2f})'
        )
        
        # Reset Nav2 fallback
        self.using_nav2 = False
    
    def get_observation(self) -> Optional[np.ndarray]:
        """
        Construct observation vector from current state.
        
        Returns:
            Observation array or None if data not available
        """
        if self.lidar_data is None or self.robot_pose is None:
            return None
        
        # Normalize LiDAR data (0-10m range)
        lidar_normalized = np.clip(self.lidar_data / 10.0, 0.0, 1.0)
        
        # Calculate goal relative to robot
        if self.goal_position is not None:
            dx = self.goal_position.x - self.robot_pose.position.x
            dy = self.goal_position.y - self.robot_pose.position.y
            distance = math.sqrt(dx**2 + dy**2)
            angle = math.atan2(dy, dx)
            
            # Get robot orientation
            robot_yaw = self.get_yaw_from_quaternion(self.robot_pose.orientation)
            relative_angle = self.normalize_angle(angle - robot_yaw)
            
            goal_info = np.array([
                dx / 10.0,
                dy / 10.0,
                distance / 10.0,
                relative_angle / math.pi
            ], dtype=np.float32)
        else:
            goal_info = np.zeros(4, dtype=np.float32)
        
        # Current velocity
        if self.robot_velocity is not None:
            velocity_info = np.array([
                self.robot_velocity.linear.x / self.max_linear_vel,
                self.robot_velocity.angular.z / self.max_angular_vel
            ], dtype=np.float32)
        else:
            velocity_info = np.zeros(2, dtype=np.float32)
        
        # Concatenate all observations
        observation = np.concatenate([
            lidar_normalized,
            goal_info,
            velocity_info
        ])
        
        return observation.astype(np.float32)
    
    def get_yaw_from_quaternion(self, q) -> float:
        """Extract yaw angle from quaternion."""
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny_cosp, cosy_cosp)
    
    def normalize_angle(self, angle: float) -> float:
        """Normalize angle to [-pi, pi]."""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle
    
    def compute_action(self, observation: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Compute action from observation using RL policy.
        
        Args:
            observation: Current observation
            
        Returns:
            Tuple of (action, confidence)
        """
        if self.policy is None:
            return np.zeros(2), 0.0
        
        try:
            # Normalize observation if needed
            if self.vec_normalize is not None:
                observation = self.vec_normalize.normalize_obs(observation)
            
            # Get action from policy
            action, _states = self.policy.predict(observation, deterministic=True)
            
            # Compute confidence score
            # For PPO/SAC, we can use the action probability or value estimate
            # Here we use a simple heuristic based on observation quality
            confidence = self.compute_confidence(observation)
            
            return action, confidence
            
        except Exception as e:
            self.get_logger().error(f'Error computing action: {e}')
            return np.zeros(2), 0.0
    
    def compute_confidence(self, observation: np.ndarray) -> float:
        """
        Compute confidence score for the current observation.
        
        Confidence is based on:
        - Minimum obstacle distance (higher is better)
        - Goal visibility (closer goals are easier)
        - Observation quality
        
        Args:
            observation: Current observation
            
        Returns:
            Confidence score [0, 1]
        """
        # Extract LiDAR data (first lidar_rays elements)
        lidar_data = observation[:self.lidar_rays]
        
        # Minimum obstacle distance (normalized)
        min_distance = np.min(lidar_data)
        distance_confidence = min_distance  # Already normalized [0, 1]
        
        # Goal distance (next 4 elements include goal info)
        goal_distance = observation[self.lidar_rays + 2]  # Normalized distance
        goal_confidence = 1.0 - min(goal_distance, 1.0)  # Closer is better
        
        # Combined confidence
        confidence = 0.7 * distance_confidence + 0.3 * goal_confidence
        
        return float(np.clip(confidence, 0.0, 1.0))
    
    def fallback_to_nav2(self):
        """Fallback to Nav2 navigation."""
        if not self.use_nav2_fallback or self.goal_position is None:
            return
        
        if not self.using_nav2:
            self.get_logger().info('Falling back to Nav2 navigation')
            self.using_nav2 = True
            
            # Send goal to Nav2
            goal_msg = NavigateToPose.Goal()
            goal_msg.pose.header.frame_id = 'map'
            goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
            goal_msg.pose.pose.position = self.goal_position
            goal_msg.pose.pose.orientation.w = 1.0
            
            if self.nav2_client.wait_for_server(timeout_sec=1.0):
                self.nav2_client.send_goal_async(goal_msg)
            else:
                self.get_logger().warn('Nav2 action server not available')
    
    def control_loop(self):
        """Main control loop - called at control_rate Hz."""
        # Check if we have a goal
        if self.goal_position is None:
            return
        
        # Check if goal reached
        if self.robot_pose is not None:
            dx = self.goal_position.x - self.robot_pose.position.x
            dy = self.goal_position.y - self.robot_pose.position.y
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance < 0.5:  # Goal threshold
                self.get_logger().info('Goal reached!')
                self.goal_position = None
                self.stop_robot()
                return
        
        # Get observation
        observation = self.get_observation()
        if observation is None:
            return
        
        # Compute action using RL policy
        action, confidence = self.compute_action(observation)
        self.current_confidence = confidence
        
        # Publish confidence
        confidence_msg = Float32()
        confidence_msg.data = confidence
        self.confidence_pub.publish(confidence_msg)
        
        # Check if we should use Nav2 fallback
        if confidence < self.confidence_threshold:
            self.fallback_to_nav2()
            status_msg = String()
            status_msg.data = f'Using Nav2 (confidence: {confidence:.2f})'
            self.status_pub.publish(status_msg)
            return
        
        # Use RL policy
        if self.using_nav2:
            self.get_logger().info('Switching back to RL navigation')
            self.using_nav2 = False
        
        # Scale action to actual velocities
        linear_vel = float(action[0]) * self.max_linear_vel
        angular_vel = float(action[1]) * self.max_angular_vel
        
        # Publish velocity command
        cmd_msg = Twist()
        cmd_msg.linear.x = linear_vel
        cmd_msg.angular.z = angular_vel
        self.cmd_vel_pub.publish(cmd_msg)
        
        # Publish status
        status_msg = String()
        status_msg.data = f'RL navigation (confidence: {confidence:.2f})'
        self.status_pub.publish(status_msg)
    
    def stop_robot(self):
        """Stop the robot."""
        cmd_msg = Twist()
        self.cmd_vel_pub.publish(cmd_msg)


def main(args=None):
    """Main function."""
    rclpy.init(args=args)
    
    try:
        node = RLNavigator()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if 'node' in locals():
            node.stop_robot()
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
