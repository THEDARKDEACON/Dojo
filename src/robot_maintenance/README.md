# Robot Predictive Maintenance System

AI-powered health monitoring and failure prediction system for the Dojo robot.

## Features

### Health Monitor
- **Real-time monitoring** of motors, sensors, battery, and system resources
- **Health scoring** for each component (0-100 scale)
- **Alert generation** with severity levels (info, warning, critical)
- **Metrics logging** for historical analysis
- **ROS diagnostics** integration

### Anomaly Detector
- **Machine learning** based anomaly detection using Isolation Forest
- **Unsupervised learning** from normal operation data
- **Automatic training** with configurable sample size
- **Periodic retraining** to adapt to system changes
- **Interpretable results** showing affected metrics

### Maintenance Scheduler
- **LSTM-based failure prediction** (simplified implementation)
- **Predictive maintenance scheduling** based on failure probability
- **Adaptive parameter adjustment** to compensate for degradation
- **Maintenance logging** and history tracking
- **Service interface** for manual maintenance triggers

## Installation

The package is already included in the workspace. Build with:

```bash
colcon build --packages-select robot_maintenance
source install/setup.bash
```

### Dependencies

Python packages (install if needed):
```bash
pip install scikit-learn psutil
```

## Usage

### Launch Complete System

```bash
ros2 launch robot_maintenance maintenance_system.launch.py
```

### Launch Individual Nodes

```bash
# Health Monitor only
ros2 run robot_maintenance health_monitor

# Anomaly Detector only
ros2 run robot_maintenance anomaly_detector

# Maintenance Scheduler only
ros2 run robot_maintenance maintenance_scheduler
```

### Configuration

Edit `config/maintenance_params.yaml` to customize:
- Update rates
- Alert thresholds
- Model parameters
- Logging options

## Topics

### Published Topics

- `/health_metrics` (std_msgs/String) - JSON health metrics
- `/overall_health` (std_msgs/Float32) - Overall health score (0-100)
- `/diagnostics` (diagnostic_msgs/DiagnosticArray) - ROS diagnostics
- `/health_alerts` (std_msgs/String) - Health alerts
- `/anomaly_detection` (std_msgs/String) - Anomaly detections
- `/failure_prediction` (std_msgs/String) - Failure predictions
- `/maintenance_alert` (std_msgs/String) - Maintenance alerts
- `/parameter_adjustment` (std_msgs/String) - Parameter adjustments

### Subscribed Topics

- `/joint_states` (sensor_msgs/JointState) - Motor states
- `/battery_state` (sensor_msgs/BatteryState) - Battery status
- `/motor_temperature` (sensor_msgs/Temperature) - Motor temperatures

### Services

- `/trigger_maintenance` (std_srvs/Trigger) - Manually trigger maintenance event

## Monitoring

### View Health Metrics

```bash
ros2 topic echo /health_metrics
```

### View Overall Health Score

```bash
ros2 topic echo /overall_health
```

### View Alerts

```bash
ros2 topic echo /health_alerts
```

### View Anomaly Detections

```bash
ros2 topic echo /anomaly_detection
```

### View Failure Predictions

```bash
ros2 topic echo /failure_prediction
```

### View Diagnostics

```bash
ros2 topic echo /diagnostics
```

## Workflow

### 1. Initial Training Phase

When first launched, the system collects data for training:

- **Health Monitor**: Immediately starts monitoring
- **Anomaly Detector**: Collects 1000 samples (~17 minutes at 1Hz) before training
- **Maintenance Scheduler**: Collects 100 samples before training predictor

During this phase, monitoring continues but anomaly detection and failure prediction are not active.

### 2. Normal Operation

After training:

- Health metrics published at 1Hz
- Anomaly detection on every health update
- Failure prediction every 60 seconds
- Alerts generated when thresholds exceeded

### 3. Anomaly Detection

When anomalies detected:

- Alert published with severity level
- Affected metrics identified
- Logged for analysis

### 4. Failure Prediction

When failure probability > 80%:

- Maintenance alert generated
- Recommended action provided
- Time to failure estimated
- Adaptive adjustments applied (if enabled)

### 5. Maintenance Execution

When maintenance performed:

- Log event via service call
- Update health models
- Reset failure predictions

## Example: Trigger Maintenance

```bash
ros2 service call /trigger_maintenance std_srvs/srv/Trigger
```

## Health Metrics Structure

```json
{
  "timestamp": 1699564800.0,
  "motor_currents": {"left_wheel": 2.5, "right_wheel": 2.3},
  "motor_temperatures": {"left_wheel": 45.0, "right_wheel": 43.0},
  "motor_velocities": {"left_wheel": 1.2, "right_wheel": 1.2},
  "battery_voltage": 12.3,
  "battery_current": -5.2,
  "battery_percentage": 85.0,
  "battery_temperature": 28.0,
  "cpu_usage": 45.2,
  "memory_usage": 62.1,
  "disk_usage": 35.8,
  "motor_health": 92.5,
  "sensor_health": 95.0,
  "battery_health": 88.3,
  "system_health": 85.7,
  "overall_health": 90.4
}
```

## Anomaly Detection Structure

```json
{
  "timestamp": 1699564800.0,
  "is_anomaly": true,
  "anomaly_score": -0.65,
  "affected_metrics": ["motor_current_mean", "motor_temp_mean"],
  "severity": "warning",
  "confidence": 0.85
}
```

## Failure Prediction Structure

```json
{
  "timestamp": 1699564800.0,
  "component": "system",
  "failure_probability": 0.75,
  "time_to_failure": 900.0,
  "confidence": 0.7,
  "recommended_action": "SOON: Schedule maintenance within 1 week"
}
```

## Adaptive Parameter Adjustment

When failure probability exceeds thresholds, the system automatically adjusts parameters:

- **Failure prob > 70%**: Reduce max velocity to 50%, acceleration to 60%
- **Failure prob > 50%**: Reduce max velocity to 75%, acceleration to 80%

Adjustments are published to `/parameter_adjustment` for other nodes to consume.

## Logging

### Health Metrics Log

File: `health_metrics.json` (one JSON object per line)

### Maintenance Log

File: `maintenance_log.json` (JSON array of maintenance events)

### Model Files

- `anomaly_model.pkl` - Trained anomaly detection model
- `failure_predictor.pkl` - Trained failure prediction model

## Integration with Other Systems

### With Safety System

Health alerts can trigger safety responses:

```python
# Subscribe to health alerts in safety system
self.health_sub = self.create_subscription(
    String, '/health_alerts', self.health_alert_callback, 10
)
```

### With Navigation System

Parameter adjustments can modify navigation behavior:

```python
# Subscribe to parameter adjustments
self.adjustment_sub = self.create_subscription(
    String, '/parameter_adjustment', self.adjustment_callback, 10
)
```

### With Performance Dashboard

Health metrics can be displayed in dashboard:

```python
# Subscribe to overall health
self.health_sub = self.create_subscription(
    Float32, '/overall_health', self.health_callback, 10
)
```

## Testing

Run the test script:

```bash
python3 src/robot_maintenance/test/test_maintenance_system.py
```

## Troubleshooting

### No health metrics published

- Check if `/joint_states` and `/battery_state` topics are available
- Verify nodes are running: `ros2 node list`

### Anomaly detector not training

- Wait for 1000 samples (~17 minutes at 1Hz)
- Check logs: `ros2 node info /anomaly_detector`

### High false positive rate

- Adjust `contamination` parameter (default: 0.1)
- Increase `training_samples` for better model
- Adjust `anomaly_threshold` (default: -0.5)

### Failure predictions inaccurate

- Collect more training data
- Adjust `sequence_length` parameter
- In production, replace simplified LSTM with TensorFlow/PyTorch model

## Future Enhancements

- Replace simplified LSTM with proper deep learning model
- Add more sophisticated feature engineering
- Implement component-specific failure predictors
- Add visualization dashboard
- Integrate with cloud-based analytics
- Add support for multiple robot fleet monitoring

## Requirements Met

This implementation satisfies all Task 12 requirements:

- ✅ 12.1: Package structure created
- ✅ 12.2: Health Monitor node implemented
- ✅ 12.3: Anomaly detection with Isolation Forest
- ✅ 12.4: Failure prediction with LSTM (simplified)
- ✅ 12.5: Adaptive parameter adjustment
- ✅ 12.6: Maintenance logging system
- ✅ 12.7: Ready for testing (test script included)

## License

MIT
