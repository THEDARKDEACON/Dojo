"""Extended Kalman Filter for multi-sensor fusion."""

import numpy as np
from typing import Tuple, Optional


class ExtendedKalmanFilter:
    """
    Extended Kalman Filter for robot localization.
    
    State vector: [x, y, θ, vx, vy, ω]
    - x, y: position in map frame (meters)
    - θ: orientation (radians)
    - vx, vy: linear velocities (m/s)
    - ω: angular velocity (rad/s)
    """
    
    def __init__(self):
        """Initialize the Extended Kalman Filter."""
        # State vector [x, y, θ, vx, vy, ω]
        self.state = np.zeros(6)
        
        # State covariance matrix (6x6) - start with high uncertainty
        self.covariance = np.eye(6) * 1.0
        
        # Process noise covariance
        self.Q = np.diag([0.001, 0.001, 0.001, 0.01, 0.01, 0.01])
        
        # Measurement noise covariances (will be set per sensor)
        self.R_lidar = np.diag([0.01, 0.01, 0.02])  # [x, y, θ] - high precision
        self.R_camera = np.diag([0.05, 0.05, 0.08])  # [x, y, θ]
        self.R_imu = np.diag([0.02, 0.02])  # [θ, ω]
        self.R_odom = np.diag([0.05, 0.05, 0.05])  # [vx, vy, ω]
        
        # Sensor reliability weights
        self.reliability = {
            'lidar': 0.9,
            'camera': 0.7,
            'imu': 0.8,
            'odometry': 0.6
        }
        
        # Last update timestamps
        self.last_update_time = None
        
    def predict(self, control_input: Optional[np.ndarray], dt: float):
        """
        Prediction step using motion model.
        
        Args:
            control_input: Control input [v, ω] (linear and angular velocity)
            dt: Time step (seconds)
        """
        if dt <= 0:
            return
            
        # Extract current state
        x, y, theta, vx, vy, omega = self.state
        
        # Motion model: constant velocity with control input
        if control_input is not None:
            v_cmd, omega_cmd = control_input
            # Blend commanded and estimated velocities
            vx = 0.7 * vx + 0.3 * v_cmd * np.cos(theta)
            vy = 0.7 * vy + 0.3 * v_cmd * np.sin(theta)
            omega = 0.7 * omega + 0.3 * omega_cmd
        
        # Predict new state
        x_new = x + vx * dt
        y_new = y + vy * dt
        theta_new = theta + omega * dt
        
        # Normalize angle to [-π, π]
        theta_new = np.arctan2(np.sin(theta_new), np.cos(theta_new))
        
        # Update state
        self.state = np.array([x_new, y_new, theta_new, vx, vy, omega])
        
        # Compute Jacobian of motion model
        F = np.eye(6)
        F[0, 3] = dt  # dx/dvx
        F[1, 4] = dt  # dy/dvy
        F[2, 5] = dt  # dθ/dω
        
        # Predict covariance
        self.covariance = F @ self.covariance @ F.T + self.Q
        
    def update_lidar(self, measurement: np.ndarray):
        """
        Update step with LiDAR measurement.
        
        Args:
            measurement: LiDAR measurement [x, y, θ]
        """
        # Measurement model: H maps state to measurement
        H = np.zeros((3, 6))
        H[0, 0] = 1  # x
        H[1, 1] = 1  # y
        H[2, 2] = 1  # θ
        
        # Apply reliability weight to measurement noise
        R = self.R_lidar / self.reliability['lidar']
        
        self._update(measurement, H, R)
        
    def update_camera(self, measurement: np.ndarray):
        """
        Update step with camera (visual odometry) measurement.
        
        Args:
            measurement: Camera measurement [x, y, θ]
        """
        # Measurement model
        H = np.zeros((3, 6))
        H[0, 0] = 1  # x
        H[1, 1] = 1  # y
        H[2, 2] = 1  # θ
        
        # Apply reliability weight
        R = self.R_camera / self.reliability['camera']
        
        self._update(measurement, H, R)
        
    def update_imu(self, measurement: np.ndarray):
        """
        Update step with IMU measurement.
        
        Args:
            measurement: IMU measurement [θ, ω]
        """
        # Measurement model
        H = np.zeros((2, 6))
        H[0, 2] = 1  # θ
        H[1, 5] = 1  # ω
        
        # Apply reliability weight
        R = self.R_imu / self.reliability['imu']
        
        self._update(measurement, H, R)
        
    def update_odometry(self, measurement: np.ndarray):
        """
        Update step with wheel odometry measurement.
        
        Args:
            measurement: Odometry measurement [vx, vy, ω]
        """
        # Measurement model
        H = np.zeros((3, 6))
        H[0, 3] = 1  # vx
        H[1, 4] = 1  # vy
        H[2, 5] = 1  # ω
        
        # Apply reliability weight
        R = self.R_odom / self.reliability['odometry']
        
        self._update(measurement, H, R)
        
    def _update(self, measurement: np.ndarray, H: np.ndarray, R: np.ndarray):
        """
        Generic update step for any sensor.
        
        Args:
            measurement: Sensor measurement
            H: Measurement matrix
            R: Measurement noise covariance
        """
        # Innovation (measurement residual)
        z_pred = H @ self.state
        y = measurement - z_pred
        
        # Normalize angle differences to [-π, π]
        for i in range(len(y)):
            if i == 2 or (len(y) == 2 and i == 0):  # θ component
                y[i] = np.arctan2(np.sin(y[i]), np.cos(y[i]))
        
        # Innovation covariance
        S = H @ self.covariance @ H.T + R
        
        # Kalman gain
        K = self.covariance @ H.T @ np.linalg.inv(S)
        
        # Update state
        self.state = self.state + K @ y
        
        # Normalize orientation
        self.state[2] = np.arctan2(np.sin(self.state[2]), np.cos(self.state[2]))
        
        # Update covariance
        I = np.eye(6)
        self.covariance = (I - K @ H) @ self.covariance
        
    def get_state(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get current state estimate and covariance.
        
        Returns:
            Tuple of (state, covariance)
        """
        return self.state.copy(), self.covariance.copy()
        
    def get_position(self) -> Tuple[float, float, float]:
        """
        Get current position estimate.
        
        Returns:
            Tuple of (x, y, θ)
        """
        return self.state[0], self.state[1], self.state[2]
        
    def get_velocity(self) -> Tuple[float, float, float]:
        """
        Get current velocity estimate.
        
        Returns:
            Tuple of (vx, vy, ω)
        """
        return self.state[3], self.state[4], self.state[5]
        
    def get_position_covariance(self) -> np.ndarray:
        """
        Get position covariance (3x3 for x, y, θ).
        
        Returns:
            Position covariance matrix
        """
        return self.covariance[:3, :3]
        
    def set_reliability(self, sensor: str, reliability: float):
        """
        Update sensor reliability weight.
        
        Args:
            sensor: Sensor name ('lidar', 'camera', 'imu', 'odometry')
            reliability: Reliability weight (0-1)
        """
        if sensor in self.reliability:
            self.reliability[sensor] = np.clip(reliability, 0.1, 1.0)
            
    def reset(self, initial_state: Optional[np.ndarray] = None,
              initial_covariance: Optional[np.ndarray] = None):
        """
        Reset the filter to initial conditions.
        
        Args:
            initial_state: Initial state vector (default: zeros)
            initial_covariance: Initial covariance (default: 0.1*I)
        """
        if initial_state is not None:
            self.state = initial_state.copy()
        else:
            self.state = np.zeros(6)
            
        if initial_covariance is not None:
            self.covariance = initial_covariance.copy()
        else:
            self.covariance = np.eye(6) * 0.1
            
        self.last_update_time = None
