#!/usr/bin/env python3
"""
Comprehensive Diagnostic System for Dojo Robot

This module provides detailed diagnostic reporting and health metrics publishing
for monitoring tools and system analysis.
"""

import time
import threading
import psutil
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import json
import statistics

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import String, Header
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from geometry_msgs.msg import Twist
from sensor_msgs.msg import BatteryState, Temperature


class DiagnosticLevel(Enum):
    """Diagnostic severity levels"""
    OK = 0
    WARN = 1
    ERROR = 2
    STALE = 3


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class SystemMetric:
    """System performance metric"""
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    metric_type: MetricType = MetricType.GAUGE
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class DiagnosticReport:
    """Comprehensive diagnostic report"""
    timestamp: datetime
    system_health: str
    component_status: Dict[str, str]
    performance_metrics: Dict[str, SystemMetric]
    alerts: List[str]
    recommendations: List[str]
    system_info: Dict[str, Any]


@dataclass
class HealthThreshold:
    """Health monitoring threshold"""
    metric_name: str
    warning_threshold: float
    error_threshold: float
    comparison: str  # 'greater', 'less', 'equal'
    unit: str = ""


@dataclass
class PerformanceHistory:
    """Performance metric history"""
    values: List[float] = field(default_factory=list)
    timestamps: List[datetime] = field(default_factory=list)
    max_history: int = 1000
    
    def add_value(self, value: float, timestamp: datetime = None):
        if timestamp is None:
            timestamp = datetime.now()
        
        self.values.append(value)
        self.timestamps.append(timestamp)
        
        # Maintain max history
        if len(self.values) > self.max_history:
            self.values = self.values[-self.max_history:]
            self.timestamps = self.timestamps[-self.max_history:]
    
    def get_statistics(self) -> Dict[str, float]:
        if not self.values:
            return {}
        
        return {
            'mean': statistics.mean(self.values),
            'median': statistics.median(self.values),
            'min': min(self.values),
            'max': max(self.values),
            'std_dev': statistics.stdev(self.values) if len(self.values) > 1 else 0.0,
            'count': len(self.values)
        }


class ComprehensiveDiagnosticSystem(Node):
    """
    Comprehensive Diagnostic System
    
    Provides:
    - Detailed diagnostic reporting
    - Health metrics publishing
    - Performance monitoring
    - System resource tracking
    - Alert generation
    - Historical data analysis
    """
    
    def __init__(self):
        super().__init__('comprehensive_diagnostic_system')
        
        self.logger = self.get_logger()
        
        # System state
        self.current_metrics: Dict[str, SystemMetric] = {}
        self.metric_history: Dict[str, PerformanceHistory] = {}
        self.health_thresholds: Dict[str, HealthThreshold] = {}
        self.active_alerts: List[str] = []
        self.component_statuses: Dict[str, str] = {}
        
        # Monitoring
        self.monitoring_active = False
        self.monitor_thread = None
        self.collection_interval = 1.0  # seconds
        
        # Configuration
        self.declare_parameter('diagnostic_rate', 2.0)
        self.declare_parameter('metric_history_size', 1000)
        self.declare_parameter('enable_system_monitoring', True)
        self.declare_parameter('enable_performance_tracking', True)
        self.declare_parameter('alert_cooldown_period', 30.0)
        
        self.diagnostic_rate = self.get_parameter('diagnostic_rate').value
        self.metric_history_size = self.get_parameter('metric_history_size').value
        self.enable_system_monitoring = self.get_parameter('enable_system_monitoring').value
        self.enable_performance_tracking = self.get_parameter('enable_performance_tracking').value
        self.alert_cooldown_period = self.get_parameter('alert_cooldown_period').value
        
        # Alert management
        self.alert_history: List[Dict] = []
        self.last_alert_times: Dict[str, datetime] = {}
        
        # Publishers
        self.diagnostics_pub = self.create_publisher(
            DiagnosticArray,
            '/diagnostics',
            10
        )
        
        self.system_metrics_pub = self.create_publisher(
            String,
            '/system/metrics',
            10
        )
        
        self.health_report_pub = self.create_publisher(
            String,
            '/system/health_report',
            10
        )
        
        self.alerts_pub = self.create_publisher(
            String,
            '/system/alerts',
            10
        )
        
        # Subscribers
        self.hardware_health_sub = self.create_subscription(
            DiagnosticArray,
            '/diagnostics/hardware_health',
            self._hardware_health_callback,
            10
        )
        
        self.component_status_sub = self.create_subscription(
            String,
            '/system/component_status',
            self._component_status_callback,
            10
        )
        
        self.degradation_status_sub = self.create_subscription(
            String,
            '/system/degradation_status',
            self._degradation_status_callback,
            10
        )
        
        # Timers
        self.diagnostic_timer = self.create_timer(
            1.0 / self.diagnostic_rate, 
            self._publish_diagnostics
        )
        self.metrics_timer = self.create_timer(5.0, self._publish_metrics)
        self.report_timer = self.create_timer(10.0, self._publish_health_report)
        
        # Initialize system
        self._initialize_health_thresholds()
        self._initialize_metric_history()
        
        # Start monitoring
        if self.enable_system_monitoring:
            self.start_monitoring()
        
        self.logger.info("Comprehensive Diagnostic System initialized")
    
    def _initialize_health_thresholds(self):
        """Initialize health monitoring thresholds"""
        self.health_thresholds.update({
            'cpu_usage': HealthThreshold(
                metric_name='cpu_usage',
                warning_threshold=70.0,
                error_threshold=90.0,
                comparison='greater',
                unit='%'
            ),
            'memory_usage': HealthThreshold(
                metric_name='memory_usage',
                warning_threshold=80.0,
                error_threshold=95.0,
                comparison='greater',
                unit='%'
            ),
            'disk_usage': HealthThreshold(
                metric_name='disk_usage',
                warning_threshold=85.0,
                error_threshold=95.0,
                comparison='greater',
                unit='%'
            ),
            'temperature': HealthThreshold(
                metric_name='temperature',
                warning_threshold=70.0,
                error_threshold=85.0,
                comparison='greater',
                unit='°C'
            ),
            'battery_voltage': HealthThreshold(
                metric_name='battery_voltage',
                warning_threshold=11.5,
                error_threshold=11.0,
                comparison='less',
                unit='V'
            ),
            'communication_latency': HealthThreshold(
                metric_name='communication_latency',
                warning_threshold=100.0,
                error_threshold=500.0,
                comparison='greater',
                unit='ms'
            ),
            'error_rate': HealthThreshold(
                metric_name='error_rate',
                warning_threshold=5.0,
                error_threshold=10.0,
                comparison='greater',
                unit='errors/min'
            )
        })
    
    def _initialize_metric_history(self):
        """Initialize metric history tracking"""
        metric_names = [
            'cpu_usage', 'memory_usage', 'disk_usage', 'temperature',
            'battery_voltage', 'communication_latency', 'error_rate',
            'network_throughput', 'process_count', 'uptime'
        ]
        
        for name in metric_names:
            self.metric_history[name] = PerformanceHistory(max_history=self.metric_history_size)
    
    def start_monitoring(self):
        """Start system monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("Started system monitoring")
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        
        self.logger.info("Stopped system monitoring")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Check health thresholds
                self._check_health_thresholds()
                
                # Update metric history
                if self.enable_performance_tracking:
                    self._update_metric_history()
                
                time.sleep(self.collection_interval)
                
            except Exception as e:
                self.logger.error(f"Error in diagnostic monitoring loop: {e}")
                time.sleep(self.collection_interval)
    
    def _collect_system_metrics(self):
        """Collect system performance metrics"""
        current_time = datetime.now()
        
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            self.current_metrics['cpu_usage'] = SystemMetric(
                name='cpu_usage',
                value=cpu_percent,
                unit='%',
                timestamp=current_time,
                metric_type=MetricType.GAUGE
            )
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.current_metrics['memory_usage'] = SystemMetric(
                name='memory_usage',
                value=memory.percent,
                unit='%',
                timestamp=current_time,
                metric_type=MetricType.GAUGE
            )
            
            self.current_metrics['memory_available'] = SystemMetric(
                name='memory_available',
                value=memory.available / (1024**3),  # GB
                unit='GB',
                timestamp=current_time,
                metric_type=MetricType.GAUGE
            )
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.current_metrics['disk_usage'] = SystemMetric(
                name='disk_usage',
                value=disk_percent,
                unit='%',
                timestamp=current_time,
                metric_type=MetricType.GAUGE
            )
            
            self.current_metrics['disk_free'] = SystemMetric(
                name='disk_free',
                value=disk.free / (1024**3),  # GB
                unit='GB',
                timestamp=current_time,
                metric_type=MetricType.GAUGE
            )
            
            # Network metrics
            network = psutil.net_io_counters()
            self.current_metrics['network_bytes_sent'] = SystemMetric(
                name='network_bytes_sent',
                value=network.bytes_sent,
                unit='bytes',
                timestamp=current_time,
                metric_type=MetricType.COUNTER
            )
            
            self.current_metrics['network_bytes_recv'] = SystemMetric(
                name='network_bytes_recv',
                value=network.bytes_recv,
                unit='bytes',
                timestamp=current_time,
                metric_type=MetricType.COUNTER
            )
            
            # Process metrics
            process_count = len(psutil.pids())
            self.current_metrics['process_count'] = SystemMetric(
                name='process_count',
                value=process_count,
                unit='count',
                timestamp=current_time,
                metric_type=MetricType.GAUGE
            )
            
            # System uptime
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime_hours = (current_time - boot_time).total_seconds() / 3600
            self.current_metrics['uptime'] = SystemMetric(
                name='uptime',
                value=uptime_hours,
                unit='hours',
                timestamp=current_time,
                metric_type=MetricType.GAUGE
            )
            
            # Temperature (if available)
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    # Get CPU temperature if available
                    for name, entries in temps.items():
                        if entries:
                            temp_value = entries[0].current
                            self.current_metrics['temperature'] = SystemMetric(
                                name='temperature',
                                value=temp_value,
                                unit='°C',
                                timestamp=current_time,
                                metric_type=MetricType.GAUGE,
                                labels={'sensor': name}
                            )
                            break
            except (AttributeError, OSError):
                # Temperature sensors not available on this system
                pass
            
            # Battery metrics (if available)
            try:
                battery = psutil.sensors_battery()
                if battery:
                    self.current_metrics['battery_percent'] = SystemMetric(
                        name='battery_percent',
                        value=battery.percent,
                        unit='%',
                        timestamp=current_time,
                        metric_type=MetricType.GAUGE
                    )
                    
                    # Estimate voltage (simplified)
                    estimated_voltage = 11.0 + (battery.percent / 100.0) * 1.4  # 11.0V to 12.4V range
                    self.current_metrics['battery_voltage'] = SystemMetric(
                        name='battery_voltage',
                        value=estimated_voltage,
                        unit='V',
                        timestamp=current_time,
                        metric_type=MetricType.GAUGE
                    )
            except (AttributeError, OSError):
                # Battery not available on this system
                pass
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
    
    def _check_health_thresholds(self):
        """Check metrics against health thresholds"""
        for threshold_name, threshold in self.health_thresholds.items():
            metric = self.current_metrics.get(threshold.metric_name)
            if not metric:
                continue
            
            # Check threshold
            alert_level = None
            if threshold.comparison == 'greater':
                if metric.value >= threshold.error_threshold:
                    alert_level = 'error'
                elif metric.value >= threshold.warning_threshold:
                    alert_level = 'warning'
            elif threshold.comparison == 'less':
                if metric.value <= threshold.error_threshold:
                    alert_level = 'error'
                elif metric.value <= threshold.warning_threshold:
                    alert_level = 'warning'
            
            # Generate alert if threshold exceeded
            if alert_level:
                alert_message = (
                    f"{threshold.metric_name} {alert_level}: "
                    f"{metric.value:.2f}{threshold.unit} "
                    f"(threshold: {threshold.warning_threshold if alert_level == 'warning' else threshold.error_threshold}{threshold.unit})"
                )
                self._generate_alert(alert_message, alert_level)
    
    def _update_metric_history(self):
        """Update metric history for trend analysis"""
        for name, metric in self.current_metrics.items():
            if name in self.metric_history:
                self.metric_history[name].add_value(metric.value, metric.timestamp)
    
    def _generate_alert(self, message: str, level: str):
        """Generate system alert"""
        # Check cooldown period
        alert_key = f"{level}:{message.split(':')[0]}"  # Use metric name as key
        current_time = datetime.now()
        
        if alert_key in self.last_alert_times:
            time_since_last = (current_time - self.last_alert_times[alert_key]).total_seconds()
            if time_since_last < self.alert_cooldown_period:
                return  # Still in cooldown
        
        # Record alert
        self.last_alert_times[alert_key] = current_time
        
        alert_record = {
            'timestamp': current_time.isoformat(),
            'level': level,
            'message': message,
            'source': 'diagnostic_system'
        }
        
        self.alert_history.append(alert_record)
        
        # Keep only last 100 alerts
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
        
        # Add to active alerts
        if message not in self.active_alerts:
            self.active_alerts.append(message)
        
        # Log alert
        if level == 'error':
            self.logger.error(f"ALERT: {message}")
        else:
            self.logger.warning(f"ALERT: {message}")
        
        # Publish alert
        self._publish_alert(alert_record)
    
    def _hardware_health_callback(self, msg: DiagnosticArray):
        """Handle hardware health diagnostics"""
        for status in msg.status:
            component_name = status.name.split('/')[-1]  # Extract component name
            
            # Update component status
            if status.level == DiagnosticStatus.OK:
                self.component_statuses[component_name] = 'healthy'
            elif status.level == DiagnosticStatus.WARN:
                self.component_statuses[component_name] = 'warning'
            elif status.level == DiagnosticStatus.ERROR:
                self.component_statuses[component_name] = 'error'
            else:
                self.component_statuses[component_name] = 'unknown'
            
            # Extract metrics from diagnostic values
            for kv in status.values:
                if kv.key in ['error_count', 'reconnect_attempts', 'last_communication_age']:
                    try:
                        value = float(kv.value)
                        metric_name = f"{component_name}_{kv.key}"
                        
                        self.current_metrics[metric_name] = SystemMetric(
                            name=metric_name,
                            value=value,
                            unit='count' if 'count' in kv.key else 'seconds',
                            timestamp=datetime.now(),
                            metric_type=MetricType.GAUGE,
                            labels={'component': component_name}
                        )
                    except ValueError:
                        pass
    
    def _component_status_callback(self, msg: String):
        """Handle component status updates"""
        try:
            status_data = json.loads(msg.data)
            component_name = status_data.get('component')
            status = status_data.get('status')
            
            if component_name and status:
                self.component_statuses[component_name] = status
                
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.debug(f"Error parsing component status: {e}")
    
    def _degradation_status_callback(self, msg: String):
        """Handle degradation status updates"""
        try:
            degradation_data = json.loads(msg.data)
            
            # Create metrics from degradation data
            self.current_metrics['degradation_level'] = SystemMetric(
                name='degradation_level',
                value=self._degradation_level_to_numeric(degradation_data.get('degradation_level', 'none')),
                unit='level',
                timestamp=datetime.now(),
                metric_type=MetricType.GAUGE
            )
            
            self.current_metrics['performance_reduction'] = SystemMetric(
                name='performance_reduction',
                value=degradation_data.get('performance_reduction', 0.0),
                unit='%',
                timestamp=datetime.now(),
                metric_type=MetricType.GAUGE
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.debug(f"Error parsing degradation status: {e}")
    
    def _degradation_level_to_numeric(self, level: str) -> float:
        """Convert degradation level to numeric value"""
        level_map = {
            'none': 0.0,
            'minimal': 1.0,
            'moderate': 2.0,
            'severe': 3.0,
            'critical': 4.0
        }
        return level_map.get(level.lower(), 0.0)
    
    def _publish_diagnostics(self):
        """Publish comprehensive diagnostics"""
        msg = DiagnosticArray()
        msg.header.stamp = self.get_clock().now().to_msg()
        
        # System overview
        system_status = DiagnosticStatus()
        system_status.name = "diagnostic_system/overview"
        system_status.hardware_id = "system"
        
        # Determine overall system health
        error_count = sum(1 for status in self.component_statuses.values() if status == 'error')
        warning_count = sum(1 for status in self.component_statuses.values() if status == 'warning')
        
        if error_count > 0:
            system_status.level = DiagnosticStatus.ERROR
            system_status.message = f"System has {error_count} error(s)"
        elif warning_count > 0:
            system_status.level = DiagnosticStatus.WARN
            system_status.message = f"System has {warning_count} warning(s)"
        else:
            system_status.level = DiagnosticStatus.OK
            system_status.message = "System healthy"
        
        # Add system metrics
        for name, metric in self.current_metrics.items():
            if name in ['cpu_usage', 'memory_usage', 'disk_usage', 'temperature']:
                system_status.values.append(KeyValue(
                    key=name,
                    value=f"{metric.value:.2f}{metric.unit}"
                ))
        
        system_status.values.append(KeyValue(key="active_alerts", value=str(len(self.active_alerts))))
        system_status.values.append(KeyValue(key="component_count", value=str(len(self.component_statuses))))
        
        msg.status.append(system_status)
        
        # Component diagnostics
        for component_name, status in self.component_statuses.items():
            comp_status = DiagnosticStatus()
            comp_status.name = f"diagnostic_system/{component_name}"
            comp_status.hardware_id = component_name
            
            if status == 'healthy':
                comp_status.level = DiagnosticStatus.OK
                comp_status.message = f"Component {component_name} healthy"
            elif status == 'warning':
                comp_status.level = DiagnosticStatus.WARN
                comp_status.message = f"Component {component_name} has warnings"
            elif status == 'error':
                comp_status.level = DiagnosticStatus.ERROR
                comp_status.message = f"Component {component_name} has errors"
            else:
                comp_status.level = DiagnosticStatus.STALE
                comp_status.message = f"Component {component_name} status unknown"
            
            comp_status.values.append(KeyValue(key="status", value=status))
            
            # Add component-specific metrics
            for metric_name, metric in self.current_metrics.items():
                if metric_name.startswith(f"{component_name}_"):
                    comp_status.values.append(KeyValue(
                        key=metric_name.replace(f"{component_name}_", ""),
                        value=f"{metric.value:.2f}{metric.unit}"
                    ))
            
            msg.status.append(comp_status)
        
        self.diagnostics_pub.publish(msg)
    
    def _publish_metrics(self):
        """Publish system metrics"""
        metrics_data = {
            'timestamp': datetime.now().isoformat(),
            'metrics': {}
        }
        
        for name, metric in self.current_metrics.items():
            metrics_data['metrics'][name] = {
                'value': metric.value,
                'unit': metric.unit,
                'type': metric.metric_type.value,
                'labels': metric.labels,
                'timestamp': metric.timestamp.isoformat()
            }
            
            # Add statistics if history is available
            if name in self.metric_history:
                stats = self.metric_history[name].get_statistics()
                if stats:
                    metrics_data['metrics'][name]['statistics'] = stats
        
        msg = String()
        msg.data = json.dumps(metrics_data)
        self.system_metrics_pub.publish(msg)
    
    def _publish_health_report(self):
        """Publish comprehensive health report"""
        report = DiagnosticReport(
            timestamp=datetime.now(),
            system_health=self._get_overall_system_health(),
            component_status=self.component_statuses.copy(),
            performance_metrics=self.current_metrics.copy(),
            alerts=self.active_alerts.copy(),
            recommendations=self._generate_recommendations(),
            system_info=self._get_system_info()
        )
        
        report_data = {
            'timestamp': report.timestamp.isoformat(),
            'system_health': report.system_health,
            'component_status': report.component_status,
            'performance_summary': self._get_performance_summary(),
            'alerts': report.alerts,
            'recommendations': report.recommendations,
            'system_info': report.system_info,
            'uptime': self.current_metrics.get('uptime', SystemMetric('uptime', 0, 'hours')).value
        }
        
        msg = String()
        msg.data = json.dumps(report_data)
        self.health_report_pub.publish(msg)
    
    def _publish_alert(self, alert_record: Dict):
        """Publish system alert"""
        msg = String()
        msg.data = json.dumps(alert_record)
        self.alerts_pub.publish(msg)
    
    def _get_overall_system_health(self) -> str:
        """Determine overall system health"""
        error_count = sum(1 for status in self.component_statuses.values() if status == 'error')
        warning_count = sum(1 for status in self.component_statuses.values() if status == 'warning')
        
        if error_count > 0:
            return 'error'
        elif warning_count > 0:
            return 'warning'
        else:
            return 'healthy'
    
    def _get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        summary = {}
        
        key_metrics = ['cpu_usage', 'memory_usage', 'disk_usage', 'temperature']
        for metric_name in key_metrics:
            metric = self.current_metrics.get(metric_name)
            if metric:
                summary[metric_name] = {
                    'current': metric.value,
                    'unit': metric.unit
                }
                
                # Add trend if history available
                if metric_name in self.metric_history:
                    stats = self.metric_history[metric_name].get_statistics()
                    if stats and stats['count'] > 1:
                        summary[metric_name]['trend'] = {
                            'mean': stats['mean'],
                            'min': stats['min'],
                            'max': stats['max']
                        }
        
        return summary
    
    def _generate_recommendations(self) -> List[str]:
        """Generate system recommendations based on current state"""
        recommendations = []
        
        # CPU usage recommendations
        cpu_metric = self.current_metrics.get('cpu_usage')
        if cpu_metric and cpu_metric.value > 80:
            recommendations.append("High CPU usage detected. Consider reducing computational load or upgrading hardware.")
        
        # Memory usage recommendations
        memory_metric = self.current_metrics.get('memory_usage')
        if memory_metric and memory_metric.value > 85:
            recommendations.append("High memory usage detected. Consider closing unnecessary processes or adding more RAM.")
        
        # Disk usage recommendations
        disk_metric = self.current_metrics.get('disk_usage')
        if disk_metric and disk_metric.value > 90:
            recommendations.append("Disk space is critically low. Clean up unnecessary files or expand storage.")
        
        # Temperature recommendations
        temp_metric = self.current_metrics.get('temperature')
        if temp_metric and temp_metric.value > 75:
            recommendations.append("High system temperature detected. Check cooling system and ventilation.")
        
        # Component-specific recommendations
        error_components = [name for name, status in self.component_statuses.items() if status == 'error']
        if error_components:
            recommendations.append(f"Components with errors: {', '.join(error_components)}. Check hardware connections and logs.")
        
        # Battery recommendations
        battery_metric = self.current_metrics.get('battery_voltage')
        if battery_metric and battery_metric.value < 11.5:
            recommendations.append("Battery voltage is low. Consider charging or replacing the battery.")
        
        return recommendations
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            return {
                'platform': os.uname().sysname,
                'architecture': os.uname().machine,
                'hostname': os.uname().nodename,
                'kernel_version': os.uname().release,
                'python_version': os.sys.version.split()[0],
                'cpu_count': psutil.cpu_count(),
                'total_memory_gb': psutil.virtual_memory().total / (1024**3),
                'total_disk_gb': psutil.disk_usage('/').total / (1024**3)
            }
        except Exception as e:
            self.logger.error(f"Error getting system info: {e}")
            return {}
    
    def get_current_metrics(self) -> Dict[str, SystemMetric]:
        """Get current system metrics"""
        return self.current_metrics.copy()
    
    def get_metric_history(self, metric_name: str) -> Optional[PerformanceHistory]:
        """Get history for a specific metric"""
        return self.metric_history.get(metric_name)
    
    def get_alert_history(self) -> List[Dict]:
        """Get alert history"""
        return self.alert_history.copy()
    
    def clear_alerts(self):
        """Clear active alerts"""
        self.active_alerts.clear()
        self.logger.info("Cleared all active alerts")
    
    def add_custom_metric(self, name: str, value: float, unit: str, labels: Dict[str, str] = None):
        """Add custom metric"""
        self.current_metrics[name] = SystemMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            metric_type=MetricType.GAUGE,
            labels=labels or {}
        )
        
        # Add to history if not exists
        if name not in self.metric_history:
            self.metric_history[name] = PerformanceHistory(max_history=self.metric_history_size)
    
    def destroy_node(self):
        """Clean shutdown"""
        self.stop_monitoring()
        super().destroy_node()


def main(args=None):
    """Main entry point for comprehensive diagnostic system"""
    rclpy.init(args=args)
    
    try:
        diagnostic_system = ComprehensiveDiagnosticSystem()
        rclpy.spin(diagnostic_system)
    except KeyboardInterrupt:
        pass
    finally:
        if 'diagnostic_system' in locals():
            diagnostic_system.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()