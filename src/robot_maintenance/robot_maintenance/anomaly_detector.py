#!/usr/bin/env python3
"""
Anomaly Detector Node

Uses machine learning to detect anomalies in system behavior:
- Isolation Forest for unsupervised anomaly detection
- Trains on normal operation data
- Detects deviations from normal patterns
- Generates alerts with severity levels
"""

import rclpy
from rclpy.node import Node

import numpy as np
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from collections import deque
import pickle
import os

from std_msgs.msg import String
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


@dataclass
class AnomalyDetection:
    """Anomaly detection result."""
    timestamp: float
    is_anomaly: bool
    anomaly_score: float  # -1 to 1, lower is more anomalous
    affected_metrics: List[str]
    severity: str  # 'info', 'warning', 'critical'
    confidence: float


class AnomalyDetector(Node):
    """
    Anomaly detection node using Isolation Forest.
    
    Learns normal behavior patterns and detects deviations.
    """
    
    def __init__(self):
        super().__init__('anomaly_detector')
        
        # Parameters
        self.declare_parameter('training_samples', 1000)
        self.declare_parameter('contamination', 0.1)  # Expected anomaly rate
        self.declare_parameter('anomaly_threshold', -0.5)
        self.declare_parameter('model_file', 'anomaly_model.pkl')
        self.declare_parameter('auto_train', True)
        self.declare_parameter('retrain_interval', 3600.0)  # seconds
        
        self.training_samples = self.get_parameter('training_samples').value
        self.contamination = self.get_parameter('contamination').value
        self.anomaly_threshold = self.get_parameter('anomaly_threshold').value
        self.model_file = self.get_parameter('model_file').value
        self.auto_train = self.get_parameter('auto_train').value
        self.retrain_interval = self.get_parameter('retrain_interval').value
        
        # State
        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        self.training_data = deque(maxlen=self.training_samples)
        self.is_trained = False
        self.last_train_time = 0.0
        
        # Feature names for interpretability
        self.feature_names = [
            'motor_current_mean',
            'motor_current_std',
            'motor_temp_mean',
            'motor_temp_std',
            'battery_voltage',
            'battery_current',
            'battery_percentage',
            'cpu_usage',
            'memory_usage',
            'disk_usage'
        ]
        
        # Load existing model if available
        self.load_model()
        
        # Subscribers
        self.health_sub = self.create_subscription(
            String,
            '/health_metrics',
            self.health_callback,
            10
        )
        
        # Publishers
        self.anomaly_pub = self.create_publisher(
            String,
            '/anomaly_detection',
            10
        )
        
        self.get_logger().info('Anomaly Detector initialized')
        if self.is_trained:
            self.get_logger().info('Loaded pre-trained model')
        else:
            self.get_logger().info(f'Collecting {self.training_samples} samples for training')
    
    def health_callback(self, msg: String):
        """Process health metrics and detect anomalies."""
        try:
            metrics = json.loads(msg.data)
            
            # Extract features
            features = self.extract_features(metrics)
            
            if not self.is_trained:
                # Collect training data
                self.training_data.append(features)
                
                if len(self.training_data) >= self.training_samples:
                    self.train_model()
            else:
                # Detect anomalies
                detection = self.detect_anomaly(features, metrics)
                
                if detection.is_anomaly:
                    self.publish_detection(detection)
                
                # Periodic retraining
                if self.auto_train:
                    current_time = self.get_clock().now().nanoseconds / 1e9
                    if current_time - self.last_train_time > self.retrain_interval:
                        self.training_data.append(features)
                        if len(self.training_data) >= self.training_samples:
                            self.retrain_model()
        
        except Exception as e:
            self.get_logger().error(f'Error processing health metrics: {e}')
    
    def extract_features(self, metrics: Dict) -> np.ndarray:
        """Extract feature vector from health metrics."""
        features = []
        
        # Motor current statistics
        motor_currents = list(metrics.get('motor_currents', {}).values())
        if motor_currents:
            features.append(np.mean(motor_currents))
            features.append(np.std(motor_currents))
        else:
            features.extend([0.0, 0.0])
        
        # Motor temperature statistics
        motor_temps = list(metrics.get('motor_temperatures', {}).values())
        if motor_temps:
            features.append(np.mean(motor_temps))
            features.append(np.std(motor_temps))
        else:
            features.extend([25.0, 0.0])
        
        # Battery metrics
        features.append(metrics.get('battery_voltage', 12.0))
        features.append(metrics.get('battery_current', 0.0))
        features.append(metrics.get('battery_percentage', 100.0))
        
        # System metrics
        features.append(metrics.get('cpu_usage', 0.0))
        features.append(metrics.get('memory_usage', 0.0))
        features.append(metrics.get('disk_usage', 0.0))
        
        return np.array(features)
    
    def train_model(self):
        """Train the anomaly detection model."""
        self.get_logger().info('Training anomaly detection model...')
        
        # Convert training data to array
        X = np.array(list(self.training_data))
        
        # Initialize scaler
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Isolation Forest
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=100
        )
        self.model.fit(X_scaled)
        
        self.is_trained = True
        self.last_train_time = self.get_clock().now().nanoseconds / 1e9
        
        # Save model
        self.save_model()
        
        self.get_logger().info('Model training complete')
    
    def retrain_model(self):
        """Retrain the model with new data."""
        self.get_logger().info('Retraining anomaly detection model...')
        self.train_model()
        self.get_logger().info('Model retraining complete')
    
    def detect_anomaly(self, features: np.ndarray, metrics: Dict) -> AnomalyDetection:
        """Detect if features represent an anomaly."""
        # Scale features
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # Predict
        prediction = self.model.predict(features_scaled)[0]
        anomaly_score = self.model.score_samples(features_scaled)[0]
        
        is_anomaly = prediction == -1 or anomaly_score < self.anomaly_threshold
        
        # Determine affected metrics
        affected_metrics = []
        if is_anomaly:
            affected_metrics = self.identify_affected_metrics(features, metrics)
        
        # Determine severity
        severity = self.determine_severity(anomaly_score, affected_metrics)
        
        # Calculate confidence
        confidence = abs(anomaly_score)
        
        return AnomalyDetection(
            timestamp=metrics.get('timestamp', 0.0),
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            affected_metrics=affected_metrics,
            severity=severity,
            confidence=confidence
        )
    
    def identify_affected_metrics(self, features: np.ndarray, metrics: Dict) -> List[str]:
        """Identify which metrics are contributing to the anomaly."""
        affected = []
        
        # Simple heuristic: check which features are far from mean
        if self.scaler is not None:
            features_scaled = self.scaler.transform(features.reshape(1, -1))[0]
            
            for i, (name, value) in enumerate(zip(self.feature_names, features_scaled)):
                if abs(value) > 2.0:  # More than 2 standard deviations
                    affected.append(name)
        
        return affected
    
    def determine_severity(self, anomaly_score: float, affected_metrics: List[str]) -> str:
        """Determine severity level of anomaly."""
        # Critical if score is very low or critical metrics affected
        critical_metrics = ['battery_voltage', 'motor_temp_mean']
        
        if anomaly_score < -0.8:
            return 'critical'
        elif any(m in critical_metrics for m in affected_metrics):
            return 'critical'
        elif anomaly_score < -0.5:
            return 'warning'
        else:
            return 'info'
    
    def publish_detection(self, detection: AnomalyDetection):
        """Publish anomaly detection result."""
        msg = String()
        msg.data = json.dumps(asdict(detection))
        self.anomaly_pub.publish(msg)
        
        # Log
        if detection.severity == 'critical':
            self.get_logger().error(
                f'CRITICAL ANOMALY detected! Score: {detection.anomaly_score:.3f}, '
                f'Affected: {", ".join(detection.affected_metrics)}'
            )
        elif detection.severity == 'warning':
            self.get_logger().warn(
                f'Anomaly detected. Score: {detection.anomaly_score:.3f}, '
                f'Affected: {", ".join(detection.affected_metrics)}'
            )
        else:
            self.get_logger().info(
                f'Minor anomaly detected. Score: {detection.anomaly_score:.3f}'
            )
    
    def save_model(self):
        """Save trained model to file."""
        try:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names
            }
            
            with open(self.model_file, 'wb') as f:
                pickle.dump(model_data, f)
            
            self.get_logger().info(f'Model saved to {self.model_file}')
        except Exception as e:
            self.get_logger().error(f'Failed to save model: {e}')
    
    def load_model(self):
        """Load trained model from file."""
        if not os.path.exists(self.model_file):
            return
        
        try:
            with open(self.model_file, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            self.is_trained = True
            
            self.get_logger().info(f'Model loaded from {self.model_file}')
        except Exception as e:
            self.get_logger().error(f'Failed to load model: {e}')


def main(args=None):
    """Main function."""
    rclpy.init(args=args)
    
    try:
        node = AnomalyDetector()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
