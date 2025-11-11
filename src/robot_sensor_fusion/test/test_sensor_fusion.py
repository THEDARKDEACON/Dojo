"""Unit tests for sensor fusion system."""

import unittest
import numpy as np
from robot_sensor_fusion.extended_kalman_filter import ExtendedKalmanFilter


class TestExtendedKalmanFilter(unittest.TestCase):
    """Test cases for Extended Kalman Filter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.ekf = ExtendedKalmanFilter()
        
    def test_initialization(self):
        """Test EKF initialization."""
        state, cov = self.ekf.get_state()
        
        # State should be zeros
        np.testing.assert_array_equal(state, np.zeros(6))
        
        # Covariance should be positive definite
        self.assertTrue(np.all(np.linalg.eigvals(cov) > 0))
        
    def test_predict_step(self):
        """Test prediction step."""
        # Set initial state
        initial_state = np.array([0.0, 0.0, 0.0, 1.0, 0.0, 0.1])
        self.ekf.reset(initial_state)
        
        # Predict for 1 second
        self.ekf.predict(None, 1.0)
        
        state, _ = self.ekf.get_state()
        
        # Position should have moved based on velocity
        self.assertAlmostEqual(state[0], 1.0, places=1)  # x moved by vx*dt
        self.assertAlmostEqual(state[1], 0.0, places=1)  # y unchanged
        self.assertAlmostEqual(state[2], 0.1, places=1)  # theta moved by omega*dt
        
    def test_lidar_update(self):
        """Test LiDAR measurement update."""
        # Set initial state with some uncertainty
        self.ekf.reset(np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
        
        # Simulate LiDAR measurement
        measurement = np.array([1.0, 2.0, 0.5])
        self.ekf.update_lidar(measurement)
        
        state, cov = self.ekf.get_state()
        
        # State should move toward measurement
        self.assertGreater(state[0], 0.5)  # x moved toward 1.0
        self.assertGreater(state[1], 1.0)  # y moved toward 2.0
        self.assertGreater(state[2], 0.2)  # theta moved toward 0.5
        
        # Covariance should decrease (more certain)
        self.assertLess(cov[0, 0], 0.1)
        
    def test_camera_update(self):
        """Test camera measurement update."""
        self.ekf.reset(np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
        
        # Simulate camera measurement
        measurement = np.array([0.5, 1.0, 0.3])
        self.ekf.update_camera(measurement)
        
        state, _ = self.ekf.get_state()
        
        # State should move toward measurement
        self.assertGreater(state[0], 0.2)
        self.assertGreater(state[1], 0.5)
        
    def test_imu_update(self):
        """Test IMU measurement update."""
        self.ekf.reset(np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
        
        # Simulate IMU measurement [theta, omega]
        measurement = np.array([0.5, 0.2])
        self.ekf.update_imu(measurement)
        
        state, _ = self.ekf.get_state()
        
        # Orientation and angular velocity should update
        self.assertGreater(state[2], 0.2)  # theta
        self.assertGreater(state[5], 0.1)  # omega
        
    def test_odometry_update(self):
        """Test odometry measurement update."""
        self.ekf.reset(np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
        
        # Simulate odometry measurement [vx, vy, omega]
        measurement = np.array([1.0, 0.5, 0.3])
        self.ekf.update_odometry(measurement)
        
        state, _ = self.ekf.get_state()
        
        # Velocities should update
        self.assertGreater(state[3], 0.5)  # vx
        self.assertGreater(state[4], 0.2)  # vy
        self.assertGreater(state[5], 0.1)  # omega
        
    def test_multi_sensor_fusion(self):
        """Test fusion of multiple sensors."""
        self.ekf.reset(np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
        
        # Update with multiple sensors
        self.ekf.update_lidar(np.array([1.0, 1.0, 0.5]))
        self.ekf.update_imu(np.array([0.5, 0.1]))
        self.ekf.update_odometry(np.array([0.5, 0.0, 0.1]))
        
        state, cov = self.ekf.get_state()
        
        # State should be influenced by all sensors
        self.assertGreater(state[0], 0.5)  # x from LiDAR
        self.assertGreater(state[1], 0.5)  # y from LiDAR
        self.assertGreater(state[2], 0.2)  # theta from LiDAR and IMU
        self.assertGreater(state[3], 0.2)  # vx from odometry
        
        # Covariance should be smaller with multiple sensors
        self.assertLess(cov[0, 0], 0.1)
        
    def test_sensor_reliability(self):
        """Test sensor reliability weighting."""
        # Set low reliability for LiDAR
        self.ekf.set_reliability('lidar', 0.3)
        
        self.ekf.reset(np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
        
        # Update with LiDAR
        self.ekf.update_lidar(np.array([1.0, 1.0, 0.5]))
        
        state1, _ = self.ekf.get_state()
        
        # Reset and test with high reliability
        self.ekf.set_reliability('lidar', 0.9)
        self.ekf.reset(np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
        self.ekf.update_lidar(np.array([1.0, 1.0, 0.5]))
        
        state2, _ = self.ekf.get_state()
        
        # High reliability should move state closer to measurement
        self.assertGreater(state2[0], state1[0])
        
    def test_angle_normalization(self):
        """Test angle normalization to [-π, π]."""
        # Set state with large angle
        self.ekf.reset(np.array([0.0, 0.0, 4.0, 0.0, 0.0, 0.0]))
        
        # Update with measurement
        self.ekf.update_lidar(np.array([0.0, 0.0, -2.0]))
        
        state, _ = self.ekf.get_state()
        
        # Angle should be normalized
        self.assertGreaterEqual(state[2], -np.pi)
        self.assertLessEqual(state[2], np.pi)
        
    def test_covariance_decrease(self):
        """Test that covariance decreases with measurements."""
        self.ekf.reset()
        
        _, cov_initial = self.ekf.get_state()
        initial_trace = np.trace(cov_initial)
        
        # Add multiple measurements
        for _ in range(10):
            self.ekf.update_lidar(np.array([1.0, 1.0, 0.5]))
            
        _, cov_final = self.ekf.get_state()
        final_trace = np.trace(cov_final)
        
        # Covariance should decrease
        self.assertLess(final_trace, initial_trace)
        
    def test_prediction_increases_uncertainty(self):
        """Test that prediction increases uncertainty."""
        self.ekf.reset()
        
        # Add measurement to reduce uncertainty
        self.ekf.update_lidar(np.array([1.0, 1.0, 0.5]))
        
        _, cov_before = self.ekf.get_state()
        trace_before = np.trace(cov_before)
        
        # Predict for some time
        for _ in range(10):
            self.ekf.predict(None, 0.1)
            
        _, cov_after = self.ekf.get_state()
        trace_after = np.trace(cov_after)
        
        # Uncertainty should increase
        self.assertGreater(trace_after, trace_before)
        
    def test_static_localization_accuracy(self):
        """Test static localization accuracy (target: ±2cm)."""
        # Simulate perfect measurements at known position
        true_position = np.array([5.0, 3.0, 1.57])
        
        self.ekf.reset()
        
        # Add multiple measurements with small noise
        np.random.seed(42)
        for _ in range(50):
            noise = np.random.normal(0, 0.01, 3)  # 1cm std dev
            measurement = true_position + noise
            self.ekf.update_lidar(measurement)
            
        x, y, theta = self.ekf.get_position()
        
        # Check accuracy (should be within 2cm)
        self.assertLess(abs(x - true_position[0]), 0.02)
        self.assertLess(abs(y - true_position[1]), 0.02)
        self.assertLess(abs(theta - true_position[2]), 0.05)
        
    def test_dynamic_localization_accuracy(self):
        """Test dynamic localization accuracy (target: ±5cm)."""
        # Simulate moving robot
        self.ekf.reset(np.array([0.0, 0.0, 0.0, 1.0, 0.0, 0.1]))
        
        # Simulate motion with measurements
        np.random.seed(42)
        for i in range(20):
            # Predict
            self.ekf.predict(np.array([1.0, 0.1]), 0.1)
            
            # Measure with noise
            state, _ = self.ekf.get_state()
            noise = np.random.normal(0, 0.02, 3)  # 2cm std dev
            measurement = state[:3] + noise
            self.ekf.update_lidar(measurement)
            
        # Final position should be reasonably accurate
        x, y, theta = self.ekf.get_position()
        
        # After 2 seconds at 1 m/s, should be around x=2.0
        self.assertLess(abs(x - 2.0), 0.05)  # Within 5cm
        
    def test_sensor_failure_handling(self):
        """Test handling of sensor failures."""
        self.ekf.reset()
        
        # Normal operation with LiDAR
        self.ekf.update_lidar(np.array([1.0, 1.0, 0.5]))
        
        # Simulate LiDAR failure by reducing reliability
        self.ekf.set_reliability('lidar', 0.1)
        
        # Continue with IMU only
        for _ in range(10):
            self.ekf.update_imu(np.array([0.5, 0.1]))
            self.ekf.predict(None, 0.1)
            
        # Should still have valid state
        state, cov = self.ekf.get_state()
        self.assertFalse(np.any(np.isnan(state)))
        self.assertFalse(np.any(np.isnan(cov)))
        
    def test_single_sensor_operation(self):
        """Test operation with single sensor."""
        self.ekf.reset()
        
        # Use only IMU
        for i in range(20):
            self.ekf.update_imu(np.array([0.1 * i, 0.1]))
            self.ekf.predict(None, 0.1)
            
        state, _ = self.ekf.get_state()
        
        # Should have valid orientation estimate
        self.assertGreater(state[2], 0.0)  # theta should increase
        self.assertFalse(np.any(np.isnan(state)))


class TestSensorFusionIntegration(unittest.TestCase):
    """Integration tests for sensor fusion."""
    
    def test_complete_fusion_pipeline(self):
        """Test complete sensor fusion pipeline."""
        ekf = ExtendedKalmanFilter()
        ekf.reset()
        
        # Simulate complete sensor suite
        dt = 0.02  # 50Hz
        
        for i in range(100):
            # Predict
            ekf.predict(np.array([1.0, 0.1]), dt)
            
            # Update with all sensors (at different rates)
            if i % 5 == 0:  # LiDAR at 10Hz
                state, _ = ekf.get_state()
                ekf.update_lidar(state[:3] + np.random.normal(0, 0.01, 3))
                
            if i % 10 == 0:  # Camera at 5Hz
                state, _ = ekf.get_state()
                ekf.update_camera(state[:3] + np.random.normal(0, 0.02, 3))
                
            if i % 2 == 0:  # IMU at 25Hz
                state, _ = ekf.get_state()
                ekf.update_imu(state[2:4:3] + np.random.normal(0, 0.01, 2))
                
            # Odometry at 50Hz
            state, _ = ekf.get_state()
            ekf.update_odometry(state[3:] + np.random.normal(0, 0.05, 3))
            
        # Should have valid final state
        state, cov = ekf.get_state()
        self.assertFalse(np.any(np.isnan(state)))
        self.assertFalse(np.any(np.isnan(cov)))
        
        # Covariance should be reasonable
        self.assertLess(np.trace(cov), 1.0)


if __name__ == '__main__':
    unittest.main()
