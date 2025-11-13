#!/usr/bin/env python3
"""
Maintenance Scheduler Node

Provides:
- LSTM-based failure prediction
- Predictive maintenance scheduling
- Adaptive parameter adjustment
- Maintenance logging and history
"""

import rclpy
from rclpy.node import Node

import numpy as np
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from collections import deque
import pickle
import os
from datetime import datetime, timedelta

from std_msgs.msg import String, Float32, Bool
from std_srvs.srv import Trigger


@dataclass
class FailurePrediction:
    """Failure prediction result."""
    timestamp: float
    component: str
    failure_probability: float  # 0-1
    time_to_failure: float  # seconds
    confidence: float
    recommended_action: str


@dataclass
class MaintenanceEvent:
    """Maintenance event record."""
    timestamp: float
    event_type: str  # 'scheduled', 'emergency', 'preventive'
    component: str
    action: str
    duration: float
    notes: str


class LSTMPredictor:
    """
    Simple LSTM-based failure predictor.
    
    Note: This is a simplified implementation. In production,
    would use TensorFlow/PyTorch for more sophisticated models.
    """
    
    def __init__(self, sequence_length: int = 50):
        self.sequence_length = sequence_length
        self.is_trained = False
        self.mean = None
        self.std = None
        
        # Simplified model parameters (would be learned in real LSTM)
        self.weights = None
    
    def prepare_sequences(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare sequences for training."""
        X, y = [], []
        
        for i in range(len(data) - self.sequence_length):
            X.append(data[i:i+self.sequence_length])
            # Predict if failure occurs in next N steps
            y.append(1.0 if self._check_failure(data[i+self.sequence_length]) else 0.0)
        
        return np.array(X), np.array(y)
    
    def _check_failure(self, features: np.ndarray) -> bool:
        """Check if features indicate failure condition."""
        # Simplified failure detection
        # In real system, would have labeled failure data
        return features[0] > 0.8  # Example: high motor current
    
    def train(self, data: np.ndarray):
        """Train the predictor."""
        # Normalize data
        self.mean = np.mean(data, axis=0)
        self.std = np.std(data, axis=0) + 1e-8
        data_normalized = (data - self.mean) / self.std
        
        # Prepare sequences
        X, y = self.prepare_sequences(data_normalized)
        
        if len(X) == 0:
            return
        
        # Simplified training (in real system, would train LSTM)
        # For now, use simple statistical model
        self.weights = np.random.randn(X.shape[-1])
        self.is_trained = True
    
    def predict(self, sequence: np.ndarray) -> float:
        """Predict failure probability."""
        if not self.is_trained:
            return 0.0
        
        # Normalize
        sequence_normalized = (sequence - self.mean) / self.std
        
        # Simplified prediction
        # In real system, would use trained LSTM
        last_values = sequence_normalized[-1]
        score = np.dot(last_values, self.weights)
        probability = 1.0 / (1.0 + np.exp(-score))  # Sigmoid
        
        return float(probability)


class MaintenanceScheduler(Node):
    """
    Maintenance scheduling node with failure prediction.
    
    Monitors system health and predicts failures.
    """
    
    def __init__(self):
        super().__init__('maintenance_scheduler')
        
        # Parameters
        self.declare_parameter('prediction_horizon', 3600.0)  # seconds
        self.declare_parameter('failure_threshold', 0.8)
        self.declare_parameter('sequence_length', 50)
        self.declare_parameter('model_file', 'failure_predictor.pkl')
        self.declare_parameter('maintenance_log', 'maintenance_log.json')
        self.declare_parameter('enable_adaptive_adjustment', True)
        
        self.prediction_horizon = self.get_parameter('prediction_horizon').value
        self.failure_threshold = self.get_parameter('failure_threshold').value
        self.sequence_length = self.get_parameter('sequence_length').value
        self.model_file = self.get_parameter('model_file').value
        self.maintenance_log = self.get_parameter('maintenance_log').value
        self.enable_adaptive = self.get_parameter('enable_adaptive_adjustment').value
        
        # State
        self.predictor = LSTMPredictor(sequence_length=self.sequence_length)
        self.health_history = deque(maxlen=1000)
        self.maintenance_history: List[MaintenanceEvent] = []
        self.last_prediction_time = 0.0
        self.prediction_interval = 60.0  # seconds
        
        # Load existing model and history
        self.load_model()
        self.load_maintenance_history()
        
        # Subscribers
        self.health_sub = self.create_subscription(
            String,
            '/health_metrics',
            self.health_callback,
            10
        )
        
        self.anomaly_sub = self.create_subscription(
            String,
            '/anomaly_detection',
            self.anomaly_callback,
            10
        )
        
        # Publishers
        self.prediction_pub = self.create_publisher(
            String,
            '/failure_prediction',
            10
        )
        
        self.maintenance_alert_pub = self.create_publisher(
            String,
            '/maintenance_alert',
            10
        )
        
        self.adjustment_pub = self.create_publisher(
            String,
            '/parameter_adjustment',
            10
        )
        
        # Services
        self.trigger_maintenance_srv = self.create_service(
            Trigger,
            '/trigger_maintenance',
            self.trigger_maintenance_callback
        )
        
        # Timer for periodic prediction
        self.timer = self.create_timer(
            self.prediction_interval,
            self.prediction_callback
        )
        
        self.get_logger().info('Maintenance Scheduler initialized')
    
    def health_callback(self, msg: String):
        """Process health metrics."""
        try:
            metrics = json.loads(msg.data)
            
            # Extract features for prediction
            features = self.extract_features(metrics)
            self.health_history.append(features)
            
            # Train model if enough data and not trained
            if not self.predictor.is_trained and len(self.health_history) >= self.sequence_length * 2:
                self.train_predictor()
        
        except Exception as e:
            self.get_logger().error(f'Error processing health metrics: {e}')
    
    def anomaly_callback(self, msg: String):
        """Process anomaly detections."""
        try:
            detection = json.loads(msg.data)
            
            # If critical anomaly, trigger immediate maintenance check
            if detection.get('severity') == 'critical':
                self.get_logger().warn('Critical anomaly detected - checking maintenance needs')
                self.check_immediate_maintenance(detection)
        
        except Exception as e:
            self.get_logger().error(f'Error processing anomaly: {e}')
    
    def extract_features(self, metrics: Dict) -> np.ndarray:
        """Extract feature vector from health metrics."""
        features = []
        
        # Motor metrics
        motor_currents = list(metrics.get('motor_currents', {}).values())
        features.append(np.mean(motor_currents) if motor_currents else 0.0)
        
        motor_temps = list(metrics.get('motor_temperatures', {}).values())
        features.append(np.mean(motor_temps) if motor_temps else 25.0)
        
        # Battery metrics
        features.append(metrics.get('battery_voltage', 12.0))
        features.append(metrics.get('battery_percentage', 100.0))
        
        # Health scores
        features.append(metrics.get('motor_health', 100.0))
        features.append(metrics.get('battery_health', 100.0))
        features.append(metrics.get('overall_health', 100.0))
        
        return np.array(features)
    
    def train_predictor(self):
        """Train the failure predictor."""
        self.get_logger().info('Training failure predictor...')
        
        # Convert history to array
        data = np.array(list(self.health_history))
        
        # Train
        self.predictor.train(data)
        
        # Save model
        self.save_model()
        
        self.get_logger().info('Failure predictor training complete')
    
    def prediction_callback(self):
        """Periodic failure prediction."""
        if not self.predictor.is_trained:
            return
        
        if len(self.health_history) < self.sequence_length:
            return
        
        # Get recent sequence
        sequence = np.array(list(self.health_history)[-self.sequence_length:])
        
        # Predict failure probability
        failure_prob = self.predictor.predict(sequence)
        
        # Create prediction
        prediction = FailurePrediction(
            timestamp=self.get_clock().now().nanoseconds / 1e9,
            component='system',
            failure_probability=failure_prob,
            time_to_failure=self.estimate_time_to_failure(failure_prob),
            confidence=0.7,  # Simplified
            recommended_action=self.recommend_action(failure_prob)
        )
        
        # Publish prediction
        self.publish_prediction(prediction)
        
        # Check if maintenance needed
        if failure_prob > self.failure_threshold:
            self.schedule_maintenance(prediction)
        
        # Adaptive adjustment
        if self.enable_adaptive and failure_prob > 0.5:
            self.adjust_parameters(failure_prob)
    
    def estimate_time_to_failure(self, failure_prob: float) -> float:
        """Estimate time until failure based on probability."""
        if failure_prob < 0.1:
            return float('inf')
        
        # Simple exponential model
        # Higher probability = shorter time
        time_to_failure = self.prediction_horizon * (1.0 - failure_prob)
        return max(0.0, time_to_failure)
    
    def recommend_action(self, failure_prob: float) -> str:
        """Recommend maintenance action based on failure probability."""
        if failure_prob > 0.9:
            return 'IMMEDIATE: Stop operations and perform emergency maintenance'
        elif failure_prob > 0.8:
            return 'URGENT: Schedule maintenance within 24 hours'
        elif failure_prob > 0.6:
            return 'SOON: Schedule maintenance within 1 week'
        elif failure_prob > 0.4:
            return 'MONITOR: Increase monitoring frequency'
        else:
            return 'NORMAL: Continue normal operations'
    
    def check_immediate_maintenance(self, detection: Dict):
        """Check if immediate maintenance is needed."""
        affected = detection.get('affected_metrics', [])
        
        critical_components = ['battery_voltage', 'motor_temp_mean']
        
        if any(comp in affected for comp in critical_components):
            alert = {
                'timestamp': self.get_clock().now().nanoseconds / 1e9,
                'severity': 'critical',
                'message': 'Immediate maintenance required',
                'affected_metrics': affected,
                'action': 'Stop operations and inspect system'
            }
            
            msg = String()
            msg.data = json.dumps(alert)
            self.maintenance_alert_pub.publish(msg)
            
            self.get_logger().error('IMMEDIATE MAINTENANCE REQUIRED!')
    
    def schedule_maintenance(self, prediction: FailurePrediction):
        """Schedule maintenance based on prediction."""
        alert = {
            'timestamp': prediction.timestamp,
            'type': 'preventive',
            'component': prediction.component,
            'failure_probability': prediction.failure_probability,
            'time_to_failure': prediction.time_to_failure,
            'recommended_action': prediction.recommended_action
        }
        
        msg = String()
        msg.data = json.dumps(alert)
        self.maintenance_alert_pub.publish(msg)
        
        self.get_logger().warn(
            f'Maintenance scheduled: {prediction.recommended_action} '
            f'(Failure prob: {prediction.failure_probability:.2%})'
        )
    
    def adjust_parameters(self, failure_prob: float):
        """Adjust system parameters to compensate for degradation."""
        adjustments = {}
        
        # Reduce maximum velocity if failure risk high
        if failure_prob > 0.7:
            adjustments['max_velocity'] = 0.5  # 50% of normal
            adjustments['max_acceleration'] = 0.6
        elif failure_prob > 0.5:
            adjustments['max_velocity'] = 0.75  # 75% of normal
            adjustments['max_acceleration'] = 0.8
        
        if adjustments:
            msg = String()
            msg.data = json.dumps({
                'timestamp': self.get_clock().now().nanoseconds / 1e9,
                'reason': f'Failure probability: {failure_prob:.2%}',
                'adjustments': adjustments
            })
            self.adjustment_pub.publish(msg)
            
            self.get_logger().info(f'Parameters adjusted: {adjustments}')
    
    def publish_prediction(self, prediction: FailurePrediction):
        """Publish failure prediction."""
        msg = String()
        msg.data = json.dumps(asdict(prediction))
        self.prediction_pub.publish(msg)
    
    def trigger_maintenance_callback(self, request, response):
        """Service callback to trigger maintenance."""
        event = MaintenanceEvent(
            timestamp=self.get_clock().now().nanoseconds / 1e9,
            event_type='manual',
            component='system',
            action='Manual maintenance triggered',
            duration=0.0,
            notes='Triggered via service call'
        )
        
        self.maintenance_history.append(event)
        self.save_maintenance_history()
        
        response.success = True
        response.message = 'Maintenance event logged'
        
        return response
    
    def save_model(self):
        """Save trained model."""
        try:
            model_data = {
                'predictor': self.predictor,
                'sequence_length': self.sequence_length
            }
            
            with open(self.model_file, 'wb') as f:
                pickle.dump(model_data, f)
            
            self.get_logger().info(f'Model saved to {self.model_file}')
        except Exception as e:
            self.get_logger().error(f'Failed to save model: {e}')
    
    def load_model(self):
        """Load trained model."""
        if not os.path.exists(self.model_file):
            return
        
        try:
            with open(self.model_file, 'rb') as f:
                model_data = pickle.load(f)
            
            self.predictor = model_data['predictor']
            self.sequence_length = model_data['sequence_length']
            
            self.get_logger().info(f'Model loaded from {self.model_file}')
        except Exception as e:
            self.get_logger().error(f'Failed to load model: {e}')
    
    def save_maintenance_history(self):
        """Save maintenance history to file."""
        try:
            history_data = [asdict(event) for event in self.maintenance_history]
            
            with open(self.maintenance_log, 'w') as f:
                json.dump(history_data, f, indent=2)
            
        except Exception as e:
            self.get_logger().error(f'Failed to save maintenance history: {e}')
    
    def load_maintenance_history(self):
        """Load maintenance history from file."""
        if not os.path.exists(self.maintenance_log):
            return
        
        try:
            with open(self.maintenance_log, 'r') as f:
                history_data = json.load(f)
            
            self.maintenance_history = [
                MaintenanceEvent(**event) for event in history_data
            ]
            
            self.get_logger().info(
                f'Loaded {len(self.maintenance_history)} maintenance events'
            )
        except Exception as e:
            self.get_logger().error(f'Failed to load maintenance history: {e}')


def main(args=None):
    """Main function."""
    rclpy.init(args=args)
    
    try:
        node = MaintenanceScheduler()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
