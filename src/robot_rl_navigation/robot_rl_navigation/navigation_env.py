#!/usr/bin/env python3
"""
NavigationEnv: Gymnasium environment for robot navigation training

This environment provides a standardized interface for training RL agents
to navigate in Gazebo simulation. It integrates with ROS2 to receive sensor
data and send control commands.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist, PoseStamped, Point
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool
import math
from typing import Tuple, Dict, Any, Optional


class NavigationEnv(gym.Env):
    """
    Gymnasium environment for robot navigation training.
    
    Observation Space:
        - LiDAR readings (64 rays, normalized distances)
        - Goal position relative to robot (x, y, distance, angle)
        - Current velocity (linear, angular)
        Total: 68 dimensions
    
    Action Space:
        - Linear velocity: [-1.0, 1.0] m/s
        - Angular velocity: [-1.0, 1.0] rad/s
    
    Reward Function:
        - Progress reward: Distance reduction to goal
        - Safety reward: Collision avoidance
        - Efficiency reward: Energy consumption
        - Smoothness reward: Path quality
    """
    
    metadata = {'render_modes': ['human']}
    
    def __init__(
        self,
        max_episode_steps: int = 1000,
        goal_threshold: float = 0.5,
        collision_threshold: float = 0.3,
        max_linear_vel: float = 1.0,
        max_angular_vel: float = 1.0,
        lidar_rays: int = 64,
        render_mode: Optional[str] = None
    ):
        """
        Initialize the navigation environment.
        
        Args:
            max_episode_steps: Maximum steps per episode
            goal_threshold: Distance to goal for success (meters)
            collision_threshold: Minimum distance to obstacle (meters)
            max_linear_vel: Maximum linear velocity (m/s)
            max_angular_vel: Maximum angular velocity (rad/s)
            lidar_rays: Number of LiDAR rays to use
            render_mode: Rendering mode (not implemented)
        """
        super().__init__()
        
        # Environment parameters
        self.max_episode_steps = max_episode_steps
        self.goal_threshold = goal_threshold
        self.collision_threshold = collision_threshold
        self.max_linear_vel = max_linear_vel
        self.max_angular_vel = max_angular_vel
        self.lidar_rays = lidar_rays
        self.render_mode = render_mode
        
        # Define observation space
        # LiDAR (64) + goal (4: x, y, distance, angle) + velocity (2)
        obs_dim = lidar_rays + 4 + 2
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(obs_dim,),
            dtype=np.float32
        )
        
        # Define action space: [linear_vel, angular_vel]
        self.action_space = spaces.Box(
            low=np.array([-1.0, -1.0]),
            high=np.array([1.0, 1.0]),
            dtype=np.float32
        )
        
        # Episode state
        self.current_step = 0
        self.episode_reward = 0.0
        self.previous_distance_to_goal = 0.0
        self.previous_action = np.zeros(2)
        
        # Robot state
        self.robot_pose = None
        self.robot_velocity = None
        self.lidar_data = None
        self.goal_position = None
        self.collision_detected = False
        
        # ROS2 node (will be initialized when needed)
        self.ros_node = None
        
    def _init_ros_node(self):
        """Initialize ROS2 node and subscribers/publishers."""
        if self.ros_node is None:
            if not rclpy.ok():
                rclpy.init()
            
            self.ros_node = Node('navigation_env')
            
            # Subscribers
            self.ros_node.create_subscription(
                LaserScan,
                '/scan',
                self._lidar_callback,
                10
            )
            
            self.ros_node.create_subscription(
                Odometry,
                '/odom',
                self._odom_callback,
                10
            )
            
            # Publishers
            self.cmd_vel_pub = self.ros_node.create_publisher(
                Twist,
                '/cmd_vel',
                10
            )
            
            self.goal_pub = self.ros_node.create_publisher(
                PoseStamped,
                '/rl_goal',
                10
            )
            
    def _lidar_callback(self, msg: LaserScan):
        """Process LiDAR scan data."""
        # Downsample to fixed number of rays
        ranges = np.array(msg.ranges)
        ranges = np.nan_to_num(ranges, nan=msg.range_max, posinf=msg.range_max)
        
        # Downsample to lidar_rays
        indices = np.linspace(0, len(ranges) - 1, self.lidar_rays, dtype=int)
        self.lidar_data = ranges[indices]
        
        # Check for collision
        min_distance = np.min(self.lidar_data)
        self.collision_detected = min_distance < self.collision_threshold
        
    def _odom_callback(self, msg: Odometry):
        """Process odometry data."""
        self.robot_pose = msg.pose.pose
        self.robot_velocity = msg.twist.twist
        
    def _get_observation(self) -> np.ndarray:
        """
        Construct observation vector from current state.
        
        Returns:
            Observation array of shape (obs_dim,)
        """
        # Wait for data if not available
        if self.lidar_data is None or self.robot_pose is None:
            return np.zeros(self.observation_space.shape[0], dtype=np.float32)
        
        # Normalize LiDAR data (0-10m range)
        lidar_normalized = np.clip(self.lidar_data / 10.0, 0.0, 1.0)
        
        # Calculate goal relative to robot
        if self.goal_position is not None:
            dx = self.goal_position.x - self.robot_pose.position.x
            dy = self.goal_position.y - self.robot_pose.position.y
            distance = math.sqrt(dx**2 + dy**2)
            angle = math.atan2(dy, dx)
            
            # Get robot orientation
            robot_yaw = self._get_yaw_from_quaternion(self.robot_pose.orientation)
            relative_angle = self._normalize_angle(angle - robot_yaw)
            
            goal_info = np.array([
                dx / 10.0,  # Normalize to ~10m range
                dy / 10.0,
                distance / 10.0,
                relative_angle / math.pi  # Normalize to [-1, 1]
            ], dtype=np.float32)
        else:
            goal_info = np.zeros(4, dtype=np.float32)
        
        # Current velocity
        velocity_info = np.array([
            self.robot_velocity.linear.x / self.max_linear_vel,
            self.robot_velocity.angular.z / self.max_angular_vel
        ], dtype=np.float32)
        
        # Concatenate all observations
        observation = np.concatenate([
            lidar_normalized,
            goal_info,
            velocity_info
        ])
        
        return observation.astype(np.float32)
    
    def _get_yaw_from_quaternion(self, q) -> float:
        """Extract yaw angle from quaternion."""
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny_cosp, cosy_cosp)
    
    def _normalize_angle(self, angle: float) -> float:
        """Normalize angle to [-pi, pi]."""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle
    
    def _calculate_reward(self, action: np.ndarray) -> float:
        """
        Calculate reward based on current state and action.
        
        Reward components:
        1. Progress reward: Reduction in distance to goal
        2. Safety reward: Penalty for being close to obstacles
        3. Efficiency reward: Penalty for high energy consumption
        4. Smoothness reward: Penalty for jerky movements
        
        Args:
            action: Action taken [linear_vel, angular_vel]
            
        Returns:
            Total reward value
        """
        reward = 0.0
        
        if self.goal_position is None or self.robot_pose is None:
            return reward
        
        # Calculate current distance to goal
        dx = self.goal_position.x - self.robot_pose.position.x
        dy = self.goal_position.y - self.robot_pose.position.y
        current_distance = math.sqrt(dx**2 + dy**2)
        
        # 1. Progress reward (weight: 1.0)
        if self.previous_distance_to_goal > 0:
            progress = self.previous_distance_to_goal - current_distance
            reward += progress * 1.0
        
        self.previous_distance_to_goal = current_distance
        
        # 2. Safety reward (weight: 2.0)
        if self.lidar_data is not None:
            min_distance = np.min(self.lidar_data)
            
            if self.collision_detected:
                reward -= 10.0  # Large penalty for collision
            elif min_distance < 0.5:
                # Penalty for being too close to obstacles
                reward -= (0.5 - min_distance) * 2.0
        
        # 3. Efficiency reward (weight: 0.5)
        # Penalize high velocities (energy consumption)
        energy_cost = (abs(action[0]) + abs(action[1])) * 0.5
        reward -= energy_cost * 0.5
        
        # 4. Smoothness reward (weight: 0.3)
        # Penalize sudden changes in action
        action_change = np.linalg.norm(action - self.previous_action)
        reward -= action_change * 0.3
        
        self.previous_action = action.copy()
        
        # 5. Goal reached bonus
        if current_distance < self.goal_threshold:
            reward += 50.0
        
        return reward
    
    def _is_done(self) -> Tuple[bool, bool]:
        """
        Check if episode is done.
        
        Returns:
            Tuple of (done, success)
        """
        # Check for collision
        if self.collision_detected:
            return True, False
        
        # Check if goal reached
        if self.goal_position is not None and self.robot_pose is not None:
            dx = self.goal_position.x - self.robot_pose.position.x
            dy = self.goal_position.y - self.robot_pose.position.y
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance < self.goal_threshold:
                return True, True
        
        # Check max steps
        if self.current_step >= self.max_episode_steps:
            return True, False
        
        return False, False
    
    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Reset the environment to initial state.
        
        Args:
            seed: Random seed
            options: Additional options
            
        Returns:
            Tuple of (observation, info)
        """
        super().reset(seed=seed)
        
        # Initialize ROS node if needed
        self._init_ros_node()
        
        # Reset episode state
        self.current_step = 0
        self.episode_reward = 0.0
        self.previous_distance_to_goal = 0.0
        self.previous_action = np.zeros(2)
        self.collision_detected = False
        
        # Generate random goal position
        # Goal within 5-10m radius
        angle = self.np_random.uniform(0, 2 * math.pi)
        distance = self.np_random.uniform(5.0, 10.0)
        
        self.goal_position = Point()
        self.goal_position.x = distance * math.cos(angle)
        self.goal_position.y = distance * math.sin(angle)
        self.goal_position.z = 0.0
        
        # Publish goal for visualization
        if self.goal_pub is not None:
            goal_msg = PoseStamped()
            goal_msg.header.stamp = self.ros_node.get_clock().now().to_msg()
            goal_msg.header.frame_id = 'odom'
            goal_msg.pose.position = self.goal_position
            goal_msg.pose.orientation.w = 1.0
            self.goal_pub.publish(goal_msg)
        
        # Wait for initial sensor data
        timeout = 5.0
        start_time = self.ros_node.get_clock().now()
        while (self.lidar_data is None or self.robot_pose is None):
            rclpy.spin_once(self.ros_node, timeout_sec=0.1)
            if (self.ros_node.get_clock().now() - start_time).nanoseconds / 1e9 > timeout:
                break
        
        observation = self._get_observation()
        info = {'goal': self.goal_position}
        
        return observation, info
    
    def step(
        self,
        action: np.ndarray
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Execute one step in the environment.
        
        Args:
            action: Action to execute [linear_vel, angular_vel]
            
        Returns:
            Tuple of (observation, reward, terminated, truncated, info)
        """
        # Clip action to valid range
        action = np.clip(action, self.action_space.low, self.action_space.high)
        
        # Scale action to actual velocities
        linear_vel = action[0] * self.max_linear_vel
        angular_vel = action[1] * self.max_angular_vel
        
        # Publish velocity command
        cmd_msg = Twist()
        cmd_msg.linear.x = float(linear_vel)
        cmd_msg.angular.z = float(angular_vel)
        self.cmd_vel_pub.publish(cmd_msg)
        
        # Wait for simulation step (100ms)
        rclpy.spin_once(self.ros_node, timeout_sec=0.1)
        
        # Get new observation
        observation = self._get_observation()
        
        # Calculate reward
        reward = self._calculate_reward(action)
        self.episode_reward += reward
        
        # Check if done
        done, success = self._is_done()
        
        # Update step counter
        self.current_step += 1
        
        # Prepare info dict
        info = {
            'success': success,
            'episode_reward': self.episode_reward,
            'steps': self.current_step,
            'collision': self.collision_detected
        }
        
        # Gymnasium API: terminated (goal/collision), truncated (timeout)
        terminated = done and (success or self.collision_detected)
        truncated = done and not terminated
        
        return observation, reward, terminated, truncated, info
    
    def render(self):
        """Render the environment (not implemented)."""
        pass
    
    def close(self):
        """Clean up resources."""
        if self.ros_node is not None:
            # Stop robot
            cmd_msg = Twist()
            self.cmd_vel_pub.publish(cmd_msg)
            
            self.ros_node.destroy_node()
            self.ros_node = None


def main():
    """Test the navigation environment."""
    import time
    
    # Create environment
    env = NavigationEnv()
    
    print("Testing NavigationEnv...")
    print(f"Observation space: {env.observation_space}")
    print(f"Action space: {env.action_space}")
    
    # Reset environment
    obs, info = env.reset()
    print(f"\nInitial observation shape: {obs.shape}")
    print(f"Goal position: ({info['goal'].x:.2f}, {info['goal'].y:.2f})")
    
    # Run a few random steps
    for i in range(10):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        
        print(f"\nStep {i+1}:")
        print(f"  Action: [{action[0]:.2f}, {action[1]:.2f}]")
        print(f"  Reward: {reward:.3f}")
        print(f"  Done: {terminated or truncated}")
        
        if terminated or truncated:
            print(f"  Success: {info['success']}")
            break
        
        time.sleep(0.1)
    
    env.close()
    print("\nTest complete!")


if __name__ == '__main__':
    main()
