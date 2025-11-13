#!/usr/bin/env python3
"""
Health Monitor Node

Continuously monitors system health metrics:
- Motor currents and temperatures
- Sensor noise levels
- Battery health
- CPU and memory usage
- Disk I/O

Publishes health metrics and generates alerts.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

import psutil
import numpy as np
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import json
import time

from std_msgs.msg import String, Float32
from sensor_msgs.msg import JointState, Temperature, BatteryState
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue


@dataclass
class HealthMetrics:
    """Container for system health metrics."""
    timestamp: float
    
    # Motor metrics
    motor_currents: Dict[str, float]
    motor_temperatures: Dict[str, float]
    motor_velocities: Dict[str, float]
    
    # Sensor metrics
    sensor_noise_levels: Dict[str, float]
    sensor_update_rates: Dict[str, float]
    
    # Battery metrics
    battery_voltage: float
    battery_current: float
    battery_percentage: float
    battery_temperature: float
    
    # System metrics
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_bandwidth: float
    
    # Health scores (0-100)
    motor_health: float
    sensor_health: float
    battery_health: float
    system_health: float
    overall_health: float


@dataclass
class HealthAlert:
    """Health alert message."""
    timestamp: float
    severity: str  # 'info', 'warning', 'critical'
    component: str
    message: str
    metric_value: float
    threshold: float


class HealthMonitor(Node):
    """
    Health monitoring node for predictive maintenance.
    
    Monitors all system components and publishes health metrics.
    """
    
    def __init__(self):
        super().__init__('health_monitor')
        
        # Parameters
        self.declare_parameter('update_rate', 1.0)  # Hz
        self.declare_parameter('motor_current_threshold', 5.0)  # Amps
        self.declare_parameter('motor_temp_threshold', 70.0)  # Celsius
        self.declare_parameter('battery_voltage_min', 10.5)  # Volts
        self.declare_parameter('cpu_usage_threshold', 80.0)  # Percent
        self.declare_parameter('memory_usage_threshold', 90.0)  # Percent
        self.declare_parameter('enable_logging', True)
        self.declare_parameter('log_file', 'health_metrics.json')
        
        self.update_rate = self.get_parameter('update_rate').value
        self.motor_current_threshold = self.get_parameter('motor_current_threshold').value
        self.motor_temp_threshold = self.get_parameter('motor_temp_threshold').value
        self.battery_voltage_min = self.get_parameter('battery_voltage_min').value
        self.cpu_usage_threshold = self.get_parameter('cpu_usage_threshold').value
        self.memory_usage_threshold = self.get_parameter('memory_usage_threshold').value
        self.enable_logging = self.get_parameter('enable_logging').value
        self.log_file = self.get_parameter('log_file').value
        
        # State
        self.motor_states = {}
        self.motor_temps = {}
        self.sensor_data = {}
        self.battery_state = None
        self.last_sensor_times = {}
        
        # History for trend analysis
        self.metrics_history: List[HealthMetrics] = []
        self.max_history = 1000
        
        # QoS profiles
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Subscribers
        self.joint_state_sub = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_state_callback,
            10
        )
        
        self.battery_sub = self.create_subscription(
            BatteryState,
            '/battery_state',
            self.battery_callback,
            10
        )
        
        self.temp_sub = self.create_subscription(
            Temperature,
            '/motor_temperature',
            self.temperature_callback,
            sensor_qos
        )
        
        # Publishers
        self.health_pub = self.create_publisher(
            String,
            '/health_metrics',
            10
        )
        
        self.diagnostics_pub = self.create_publisher(
            DiagnosticArray,
            '/diagnostics',
            10
        )
        
        self.alert_pub = self.create_publisher(
            String,
            '/health_alerts',
            10
        )
        
        self.overall_health_pub = self.create_publisher(
            Float32,
            '/overall_health',
            10
        )
        
        # Timer for periodic monitoring
        self.timer = self.create_timer(
            1.0 / self.update_rate,
            self.monitor_callback
        )
        
        self.get_logger().info('Health Monitor initialized')
        self.get_logger().info(f'Update rate: {self.update_rate} Hz')
    
    def joint_state_callback(self, msg: JointState):
        """Process joint state data (motor positions, velocities, efforts)."""
        for i, name in enumerate(msg.name):
            self.motor_states[name] = {
                'position': msg.position[i] if i < len(msg.position) else 0.0,
                'velocity': msg.velocity[i] if i < len(msg.velocity) else 0.0,
                'effort': msg.effort[i] if i < len(msg.effort) else 0.0,
                'timestamp': time.time()
            }
    
    def battery_callback(self, msg: BatteryState):
        """Process battery state data."""
        self.battery_state = {
            'voltage': msg.voltage,
            'current': msg.current,
            'percentage': msg.percentage,
            'temperature': msg.temperature if hasattr(msg, 'temperature') else 25.0,
            'timestamp': time.time()
        }
    
    def temperature_callback(self, msg: Temperature):
        """Process motor temperature data."""
        # Assuming temperature message has a frame_id indicating which motor
        motor_name = msg.header.frame_id if msg.header.frame_id else 'motor_0'
        self.motor_temps[motor_name] = {
            'temperature': msg.temperature,
            'timestamp': time.time()
        }
    
    def get_system_metrics(self) -> Dict:
        """Get system resource usage metrics."""
        return {
            'cpu_usage': psutil.cpu_percent(interval=0.1),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'network_bandwidth': self._get_network_bandwidth()
        }
    
    def _get_network_bandwidth(self) -> float:
        """Estimate network bandwidth usage (Mbps)."""
        try:
            net_io = psutil.net_io_counters()
            # Simple estimation based on bytes sent/received
            # This is a simplified metric
            return (net_io.bytes_sent + net_io.bytes_recv) / 1_000_000  # Convert to MB
        except:
            return 0.0
    
    def calculate_motor_health(self) -> float:
        """Calculate overall motor health score (0-100)."""
        if not self.motor_states:
            return 100.0
        
        health_scores = []
        
        for name, state in self.motor_states.items():
            # Check current (effort as proxy)
            current = abs(state['effort'])
            current_score = max(0, 100 - (current / self.motor_current_threshold) * 100)
            
            # Check temperature
            temp_score = 100.0
            if name in self.motor_temps:
                temp = self.motor_temps[name]['temperature']
                temp_score = max(0, 100 - (temp / self.motor_temp_threshold) * 100)
            
            # Check velocity smoothness (detect jerky motion)
            velocity_score = 100.0  # Simplified for now
            
            # Combined score
            motor_score = (current_score + temp_score + velocity_score) / 3.0
            health_scores.append(motor_score)
        
        return np.mean(health_scores) if health_scores else 100.0
    
    def calculate_sensor_health(self) -> float:
        """Calculate overall sensor health score (0-100)."""
        # For now, assume sensors are healthy if receiving data
        # In a real system, would analyze noise levels and update rates
        return 95.0  # Placeholder
    
    def calculate_battery_health(self) -> float:
        """Calculate battery health score (0-100)."""
        if not self.battery_state:
            return 100.0
        
        voltage = self.battery_state['voltage']
        percentage = self.battery_state['percentage']
        temperature = self.battery_state['temperature']
        
        # Voltage health
        voltage_score = max(0, min(100, (voltage - self.battery_voltage_min) / (12.6 - self.battery_voltage_min) * 100))
        
        # Percentage health
        percentage_score = percentage
        
        # Temperature health (optimal: 20-30°C)
        if 20 <= temperature <= 30:
            temp_score = 100.0
        elif temperature < 20:
            temp_score = max(0, 100 - (20 - temperature) * 5)
        else:
            temp_score = max(0, 100 - (temperature - 30) * 3)
        
        return (voltage_score + percentage_score + temp_score) / 3.0
    
    def calculate_system_health(self) -> float:
        """Calculate system resource health score (0-100)."""
        metrics = self.get_system_metrics()
        
        cpu_score = max(0, 100 - metrics['cpu_usage'])
        memory_score = max(0, 100 - metrics['memory_usage'])
        disk_score = max(0, 100 - metrics['disk_usage'])
        
        return (cpu_score + memory_score + disk_score) / 3.0
    
    def collect_metrics(self) -> HealthMetrics:
        """Collect all health metrics."""
        # Motor metrics
        motor_currents = {name: abs(state['effort']) for name, state in self.motor_states.items()}
        motor_velocities = {name: state['velocity'] for name, state in self.motor_states.items()}
        motor_temperatures = {name: data['temperature'] for name, data in self.motor_temps.items()}
        
        # Sensor metrics (simplified)
        sensor_noise_levels = {}  # Would calculate from actual sensor data
        sensor_update_rates = {}  # Would calculate from timestamps
        
        # Battery metrics
        battery_voltage = self.battery_state['voltage'] if self.battery_state else 12.0
        battery_current = self.battery_state['current'] if self.battery_state else 0.0
        battery_percentage = self.battery_state['percentage'] if self.battery_state else 100.0
        battery_temperature = self.battery_state['temperature'] if self.battery_state else 25.0
        
        # System metrics
        system_metrics = self.get_system_metrics()
        
        # Health scores
        motor_health = self.calculate_motor_health()
        sensor_health = self.calculate_sensor_health()
        battery_health = self.calculate_battery_health()
        system_health = self.calculate_system_health()
        overall_health = (motor_health + sensor_health + battery_health + system_health) / 4.0
        
        return HealthMetrics(
            timestamp=time.time(),
            motor_currents=motor_currents,
            motor_temperatures=motor_temperatures,
            motor_velocities=motor_velocities,
            sensor_noise_levels=sensor_noise_levels,
            sensor_update_rates=sensor_update_rates,
            battery_voltage=battery_voltage,
            battery_current=battery_current,
            battery_percentage=battery_percentage,
            battery_temperature=battery_temperature,
            cpu_usage=system_metrics['cpu_usage'],
            memory_usage=system_metrics['memory_usage'],
            disk_usage=system_metrics['disk_usage'],
            network_bandwidth=system_metrics['network_bandwidth'],
            motor_health=motor_health,
            sensor_health=sensor_health,
            battery_health=battery_health,
            system_health=system_health,
            overall_health=overall_health
        )
    
    def check_thresholds(self, metrics: HealthMetrics) -> List[HealthAlert]:
        """Check metrics against thresholds and generate alerts."""
        alerts = []
        
        # Check motor currents
        for name, current in metrics.motor_currents.items():
            if current > self.motor_current_threshold:
                alerts.append(HealthAlert(
                    timestamp=time.time(),
                    severity='warning',
                    component=f'motor_{name}',
                    message=f'Motor current high: {current:.2f}A',
                    metric_value=current,
                    threshold=self.motor_current_threshold
                ))
        
        # Check motor temperatures
        for name, temp in metrics.motor_temperatures.items():
            if temp > self.motor_temp_threshold:
                alerts.append(HealthAlert(
                    timestamp=time.time(),
                    severity='critical' if temp > self.motor_temp_threshold * 1.1 else 'warning',
                    component=f'motor_{name}_temp',
                    message=f'Motor temperature high: {temp:.1f}°C',
                    metric_value=temp,
                    threshold=self.motor_temp_threshold
                ))
        
        # Check battery voltage
        if metrics.battery_voltage < self.battery_voltage_min:
            alerts.append(HealthAlert(
                timestamp=time.time(),
                severity='critical',
                component='battery',
                message=f'Battery voltage low: {metrics.battery_voltage:.2f}V',
                metric_value=metrics.battery_voltage,
                threshold=self.battery_voltage_min
            ))
        
        # Check CPU usage
        if metrics.cpu_usage > self.cpu_usage_threshold:
            alerts.append(HealthAlert(
                timestamp=time.time(),
                severity='warning',
                component='cpu',
                message=f'CPU usage high: {metrics.cpu_usage:.1f}%',
                metric_value=metrics.cpu_usage,
                threshold=self.cpu_usage_threshold
            ))
        
        # Check memory usage
        if metrics.memory_usage > self.memory_usage_threshold:
            alerts.append(HealthAlert(
                timestamp=time.time(),
                severity='critical' if metrics.memory_usage > 95 else 'warning',
                component='memory',
                message=f'Memory usage high: {metrics.memory_usage:.1f}%',
                metric_value=metrics.memory_usage,
                threshold=self.memory_usage_threshold
            ))
        
        return alerts
    
    def publish_metrics(self, metrics: HealthMetrics):
        """Publish health metrics."""
        # Publish as JSON string
        metrics_msg = String()
        metrics_msg.data = json.dumps(asdict(metrics))
        self.health_pub.publish(metrics_msg)
        
        # Publish overall health score
        health_msg = Float32()
        health_msg.data = metrics.overall_health
        self.overall_health_pub.publish(health_msg)
        
        # Publish diagnostics
        diag_array = DiagnosticArray()
        diag_array.header.stamp = self.get_clock().now().to_msg()
        
        # Overall status
        overall_status = DiagnosticStatus()
        overall_status.name = 'Health Monitor'
        overall_status.hardware_id = 'robot_maintenance'
        
        if metrics.overall_health > 80:
            overall_status.level = DiagnosticStatus.OK
            overall_status.message = 'System healthy'
        elif metrics.overall_health > 60:
            overall_status.level = DiagnosticStatus.WARN
            overall_status.message = 'System degraded'
        else:
            overall_status.level = DiagnosticStatus.ERROR
            overall_status.message = 'System unhealthy'
        
        overall_status.values = [
            KeyValue(key='overall_health', value=f'{metrics.overall_health:.1f}'),
            KeyValue(key='motor_health', value=f'{metrics.motor_health:.1f}'),
            KeyValue(key='battery_health', value=f'{metrics.battery_health:.1f}'),
            KeyValue(key='system_health', value=f'{metrics.system_health:.1f}')
        ]
        
        diag_array.status.append(overall_status)
        self.diagnostics_pub.publish(diag_array)
    
    def publish_alerts(self, alerts: List[HealthAlert]):
        """Publish health alerts."""
        for alert in alerts:
            alert_msg = String()
            alert_msg.data = json.dumps(asdict(alert))
            self.alert_pub.publish(alert_msg)
            
            # Log alert
            if alert.severity == 'critical':
                self.get_logger().error(f'{alert.component}: {alert.message}')
            elif alert.severity == 'warning':
                self.get_logger().warn(f'{alert.component}: {alert.message}')
            else:
                self.get_logger().info(f'{alert.component}: {alert.message}')
    
    def log_metrics(self, metrics: HealthMetrics):
        """Log metrics to file."""
        if not self.enable_logging:
            return
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(asdict(metrics)) + '\n')
        except Exception as e:
            self.get_logger().error(f'Failed to log metrics: {e}')
    
    def monitor_callback(self):
        """Periodic monitoring callback."""
        # Collect metrics
        metrics = self.collect_metrics()
        
        # Store in history
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history.pop(0)
        
        # Check thresholds
        alerts = self.check_thresholds(metrics)
        
        # Publish
        self.publish_metrics(metrics)
        if alerts:
            self.publish_alerts(alerts)
        
        # Log
        self.log_metrics(metrics)


def main(args=None):
    """Main function."""
    rclpy.init(args=args)
    
    try:
        node = HealthMonitor()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
