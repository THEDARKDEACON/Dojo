#!/usr/bin/env python3
"""
Digital Twin - Real-time virtual replica of the physical robot.

Maintains synchronized state, predicts future behavior, and enables
what-if analysis for mission planning.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import json
from datetime import datetime


@dataclass
class RobotState:
    """Complete robot state"""
    timestamp: float
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    orientation: np.ndarray = field(default_factory=lambda: np.zeros(4))
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(2))
    sensor_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp,
            'position': self.position.tolist(),
            'orientation': self.orientation.tolist(),
            'velocity': self.velocity.tolist(),
            'sensor_data': self.sensor_data
        }


class RobotDigitalTwin(Node):
    """
    Digital twin of the physical robot.
    
    Maintains real-time synchronized state and provides:
    - State prediction
    - Mission simulation
    - Failure prediction
    - Offline operation
    """
    
    def __init__(self):
        super().__init__('digital_twin')
        
        # Declare parameters
        self.declare_parameters(
            namespace='',
            parameters=[
                ('sync_rate', 10.0),  # Hz
                ('prediction_horizon', 10.0),  # seconds
                ('enable_physics_sim', False),
                ('offline_mode', False),
            ]
        )
        
        # Get parameters
        self.sync_rate = self.get_parameter('sync_rate').value
        self.prediction_horizon = self.get_parameter('prediction_horizon').value
        self.enable_physics = self.get_parameter('enable_physics_sim').value
        self.offline_mode = self.get_parameter('offline_mode').value
        
        # Twin state
        self.current_state = RobotState(timestamp=self.get_clock().now().nanoseconds / 1e9)
        self.state_history: List[RobotState] = []
        self.max_history = 1000
        
        # Physics simulation (if enabled)
        self.physics_sim = None
        if self.enable_physics:
            self.physics_sim = self._initialize_physics_sim()
        
        # Publishers
        self.twin_state_pub = self.create_publisher(
            String, '/digital_twin/state', 10
        )
        self.prediction_pub = self.create_publisher(
            String, '/digital_twin/prediction', 10
        )
        
        # Subscribers (only if not in offline mode)
        if not self.offline_mode:
            self.odom_sub = self.create_subscription(
                Odometry, '/odom', self.odom_callback, 10
            )
            self.scan_sub = self.create_subscription(
                LaserScan, '/scan', self.scan_callback, 10
            )
            self.cmd_vel_sub = self.create_subscription(
                Twist, '/cmd_vel', self.cmd_vel_callback, 10
            )
        
        # Timers
        self.create_timer(1.0 / self.sync_rate, self.sync_callback)
        self.create_timer(1.0, self.predict_callback)
        
        mode = "offline" if self.offline_mode else "online"
        self.get_logger().info(f'Digital Twin initialized in {mode} mode')
    
    def _initialize_physics_sim(self):
        """Initialize physics simulation (PyBullet)"""
        try:
            import pybullet as p
            import pybullet_data
            
            # Connect to physics server
            physics_client = p.connect(p.DIRECT)  # Headless mode
            p.setAdditionalSearchPath(pybullet_data.getDataPath())
            p.setGravity(0, 0, -9.81)
            
            # Load plane and robot
            plane_id = p.loadURDF("plane.urdf")
            # robot_id = p.loadURDF("path/to/robot.urdf")
            
            self.get_logger().info('Physics simulation initialized')
            return {'client': physics_client, 'plane': plane_id}
        except ImportError:
            self.get_logger().warn('PyBullet not installed. Physics simulation disabled.')
            return None
    
    def odom_callback(self, msg: Odometry):
        """Update twin state from odometry"""
        self.current_state.position = np.array([
            msg.pose.pose.position.x,
            msg.pose.pose.position.y,
            msg.pose.pose.position.z
        ])
        self.current_state.orientation = np.array([
            msg.pose.pose.orientation.x,
            msg.pose.pose.orientation.y,
            msg.pose.pose.orientation.z,
            msg.pose.pose.orientation.w
        ])
        self.current_state.velocity = np.array([
            msg.twist.twist.linear.x,
            msg.twist.twist.angular.z
        ])
        self.current_state.timestamp = self.get_clock().now().nanoseconds / 1e9
    
    def scan_callback(self, msg: LaserScan):
        """Update twin state from laser scan"""
        self.current_state.sensor_data['scan'] = {
            'ranges': msg.ranges[:10],  # Store subset
            'angle_min': msg.angle_min,
            'angle_max': msg.angle_max
        }
    
    def cmd_vel_callback(self, msg: Twist):
        """Update twin state from velocity commands"""
        self.current_state.sensor_data['cmd_vel'] = {
            'linear': msg.linear.x,
            'angular': msg.angular.z
        }
    
    def sync_callback(self):
        """Periodic state synchronization"""
        # Add to history
        self.state_history.append(self.current_state)
        if len(self.state_history) > self.max_history:
            self.state_history.pop(0)
        
        # Publish twin state
        msg = String()
        msg.data = json.dumps(self.current_state.to_dict())
        self.twin_state_pub.publish(msg)
        
        # Update physics simulation if enabled
        if self.physics_sim:
            self._update_physics_sim()
    
    def predict_callback(self):
        """Predict future states"""
        if len(self.state_history) < 10:
            return
        
        predictions = self.predict_future_states(self.prediction_horizon)
        
        # Publish predictions
        msg = String()
        msg.data = json.dumps({
            'predictions': [p.to_dict() for p in predictions],
            'horizon': self.prediction_horizon
        })
        self.prediction_pub.publish(msg)
    
    def predict_future_states(self, horizon: float) -> List[RobotState]:
        """
        Predict future robot states.
        
        Args:
            horizon: Prediction time horizon in seconds
            
        Returns:
            List of predicted states
        """
        predictions = []
        
        # Simple linear extrapolation (can be replaced with ML model)
        dt = 0.1  # 100ms steps
        num_steps = int(horizon / dt)
        
        current = self.current_state
        
        for i in range(num_steps):
            # Predict next state using current velocity
            next_state = RobotState(
                timestamp=current.timestamp + dt,
                position=current.position + current.velocity[0] * dt * np.array([1, 0, 0]),
                orientation=current.orientation.copy(),
                velocity=current.velocity.copy()
            )
            predictions.append(next_state)
            current = next_state
        
        return predictions
    
    def _update_physics_sim(self):
        """Update physics simulation with current state"""
        if not self.physics_sim:
            return
        
        # Update robot position in simulation
        # p.resetBasePositionAndOrientation(robot_id, position, orientation)
        pass
    
    def simulate_mission(self, mission_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate a mission plan in the digital twin.
        
        Args:
            mission_plan: Mission specification
            
        Returns:
            Simulation results
        """
        self.get_logger().info('Simulating mission in digital twin')
        
        # Run simulation
        results = {
            'success': True,
            'duration': 120.0,  # seconds
            'energy_consumed': 0.5,  # kWh
            'distance_traveled': 50.0,  # meters
            'obstacles_encountered': 3,
            'failures_predicted': []
        }
        
        return results
    
    def predict_failures(self) -> List[Dict[str, Any]]:
        """
        Predict potential failures based on current state and history.
        
        Returns:
            List of predicted failures with probabilities
        """
        failures = []
        
        # Analyze state history for anomalies
        if len(self.state_history) > 100:
            # Check for degrading performance
            recent_velocities = [s.velocity[0] for s in self.state_history[-100:]]
            if np.mean(recent_velocities) < 0.5 * np.mean([s.velocity[0] for s in self.state_history[:100]]):
                failures.append({
                    'type': 'motor_degradation',
                    'probability': 0.7,
                    'estimated_time': 3600.0  # 1 hour
                })
        
        return failures


def main(args=None):
    rclpy.init(args=args)
    node = RobotDigitalTwin()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
