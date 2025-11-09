#!/usr/bin/env python3
"""
Performance Monitor Module

Provides frame rate monitoring, CPU and memory usage tracking, and performance
alerts for the robot vision detection pipeline.
"""

import time
import psutil
import threading
from typing import Dict, Optional, Callable
from collections import deque
from dataclasses import dataclass
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    frame_rate: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    memory_usage_mb: float = 0.0
    processing_time_ms: float = 0.0
    frames_processed: int = 0
    frames_dropped: int = 0
    detection_count: int = 0


class PerformanceMonitor:
    """
    Performance monitoring system for object detection pipeline.
    
    Implements frame rate monitoring and reporting for object detection,
    CPU and memory usage tracking for detection processes, and creates
    performance alerts when targets are not met.
    """
    
    def __init__(self, node: Node, target_fps: float = 10.0, 
                 cpu_threshold: float = 80.0, memory_threshold_mb: float = 500.0):
        """
        Initialize performance monitor.
        
        Args:
            node: ROS2 node for logging and publishing
            target_fps: Target frame rate for performance monitoring
            cpu_threshold: CPU usage threshold for alerts (percentage)
            memory_threshold_mb: Memory usage threshold for alerts (MB)
        """
        self.node = node
        self.target_fps = target_fps
        self.cpu_threshold = cpu_threshold
        self.memory_threshold_mb = memory_threshold_mb
        
        # Performance tracking
        self.frame_times = deque(maxlen=100)  # Store last 100 frame times
        self.processing_times = deque(maxlen=100)  # Store last 100 processing times
        self.start_time = time.time()
        self.last_frame_time = time.time()
        self.frames_processed = 0
        self.frames_dropped = 0
        self.detection_count = 0
        
        # System monitoring
        self.process = psutil.Process()
        self.cpu_percent = 0.0
        self.memory_usage_mb = 0.0
        
        # Alert callbacks
        self.alert_callbacks: Dict[str, Callable] = {}
        
        # Monitoring thread
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_system_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        # Publishers for diagnostics
        self.diagnostic_publisher = node.create_publisher(
            DiagnosticArray,
            '/diagnostics',
            10
        )
        
        # Performance reporting timer
        self.report_timer = node.create_timer(
            5.0,  # Report every 5 seconds
            self._publish_performance_report
        )
        
        self.node.get_logger().info(
            f'Performance Monitor initialized - Target FPS: {target_fps}, '
            f'CPU threshold: {cpu_threshold}%, Memory threshold: {memory_threshold_mb}MB'
        )
    
    def register_alert_callback(self, alert_type: str, callback: Callable) -> None:
        """
        Register callback for performance alerts.
        
        Args:
            alert_type: Type of alert ('fps', 'cpu', 'memory')
            callback: Function to call when alert is triggered
        """
        self.alert_callbacks[alert_type] = callback
    
    def start_frame_processing(self) -> float:
        """
        Mark the start of frame processing.
        
        Returns:
            Timestamp for measuring processing time
        """
        current_time = time.time()
        
        # Calculate frame interval
        if self.last_frame_time > 0:
            frame_interval = current_time - self.last_frame_time
            self.frame_times.append(frame_interval)
        
        self.last_frame_time = current_time
        return current_time
    
    def end_frame_processing(self, start_timestamp: float, detection_count: int = 0) -> None:
        """
        Mark the end of frame processing and update metrics.
        
        Args:
            start_timestamp: Timestamp from start_frame_processing()
            detection_count: Number of objects detected in this frame
        """
        end_time = time.time()
        processing_time = (end_time - start_timestamp) * 1000  # Convert to ms
        
        self.processing_times.append(processing_time)
        self.frames_processed += 1
        self.detection_count += detection_count
        
        # Check for performance alerts
        self._check_performance_alerts()
    
    def report_dropped_frame(self) -> None:
        """Report a dropped frame."""
        self.frames_dropped += 1
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """
        Get current performance metrics.
        
        Returns:
            PerformanceMetrics object with current values
        """
        # Calculate frame rate
        if len(self.frame_times) > 1:
            avg_frame_interval = sum(self.frame_times) / len(self.frame_times)
            frame_rate = 1.0 / avg_frame_interval if avg_frame_interval > 0 else 0.0
        else:
            frame_rate = 0.0
        
        # Calculate average processing time
        avg_processing_time = (
            sum(self.processing_times) / len(self.processing_times)
            if self.processing_times else 0.0
        )
        
        return PerformanceMetrics(
            frame_rate=frame_rate,
            cpu_usage=self.cpu_percent,
            memory_usage=self.memory_usage_mb / 1024.0,  # Convert to GB
            memory_usage_mb=self.memory_usage_mb,
            processing_time_ms=avg_processing_time,
            frames_processed=self.frames_processed,
            frames_dropped=self.frames_dropped,
            detection_count=self.detection_count
        )
    
    def _monitor_system_resources(self) -> None:
        """Monitor system resources in background thread."""
        while self.monitoring_active:
            try:
                # Update CPU usage (averaged over 1 second)
                self.cpu_percent = self.process.cpu_percent(interval=1.0)
                
                # Update memory usage
                memory_info = self.process.memory_info()
                self.memory_usage_mb = memory_info.rss / 1024 / 1024  # Convert to MB
                
            except Exception as e:
                self.node.get_logger().error(f'Error monitoring system resources: {e}')
                time.sleep(1.0)
    
    def _check_performance_alerts(self) -> None:
        """Check performance metrics and trigger alerts if thresholds are exceeded."""
        metrics = self.get_current_metrics()
        
        # Check frame rate alert
        if metrics.frame_rate < self.target_fps * 0.8:  # 80% of target
            if 'fps' in self.alert_callbacks:
                self.alert_callbacks['fps'](metrics.frame_rate, self.target_fps)
            
            self.node.get_logger().warn(
                f'Low frame rate detected: {metrics.frame_rate:.1f} FPS '
                f'(target: {self.target_fps} FPS)',
                throttle_duration_sec=10.0
            )
        
        # Check CPU usage alert
        if metrics.cpu_usage > self.cpu_threshold:
            if 'cpu' in self.alert_callbacks:
                self.alert_callbacks['cpu'](metrics.cpu_usage, self.cpu_threshold)
            
            self.node.get_logger().warn(
                f'High CPU usage detected: {metrics.cpu_usage:.1f}% '
                f'(threshold: {self.cpu_threshold}%)',
                throttle_duration_sec=10.0
            )
        
        # Check memory usage alert
        if metrics.memory_usage_mb > self.memory_threshold_mb:
            if 'memory' in self.alert_callbacks:
                self.alert_callbacks['memory'](metrics.memory_usage_mb, self.memory_threshold_mb)
            
            self.node.get_logger().warn(
                f'High memory usage detected: {metrics.memory_usage_mb:.1f} MB '
                f'(threshold: {self.memory_threshold_mb} MB)',
                throttle_duration_sec=10.0
            )
    
    def _publish_performance_report(self) -> None:
        """Publish performance diagnostics report."""
        try:
            metrics = self.get_current_metrics()
            
            # Create diagnostic array
            diagnostic_array = DiagnosticArray()
            diagnostic_array.header.stamp = self.node.get_clock().now().to_msg()
            
            # Create diagnostic status for vision detection performance
            status = DiagnosticStatus()
            status.name = 'vision_detection_performance'
            status.hardware_id = 'vision_detection_node'
            
            # Determine overall status level
            if (metrics.frame_rate >= self.target_fps * 0.9 and 
                metrics.cpu_usage < self.cpu_threshold * 0.9 and
                metrics.memory_usage_mb < self.memory_threshold_mb * 0.9):
                status.level = DiagnosticStatus.OK
                status.message = 'Performance within normal parameters'
            elif (metrics.frame_rate >= self.target_fps * 0.7 and 
                  metrics.cpu_usage < self.cpu_threshold and
                  metrics.memory_usage_mb < self.memory_threshold_mb):
                status.level = DiagnosticStatus.WARN
                status.message = 'Performance degraded but acceptable'
            else:
                status.level = DiagnosticStatus.ERROR
                status.message = 'Performance below acceptable thresholds'
            
            # Add performance metrics as key-value pairs
            status.values = [
                KeyValue(key='frame_rate_fps', value=f'{metrics.frame_rate:.2f}'),
                KeyValue(key='target_fps', value=f'{self.target_fps:.2f}'),
                KeyValue(key='cpu_usage_percent', value=f'{metrics.cpu_usage:.2f}'),
                KeyValue(key='memory_usage_mb', value=f'{metrics.memory_usage_mb:.2f}'),
                KeyValue(key='processing_time_ms', value=f'{metrics.processing_time_ms:.2f}'),
                KeyValue(key='frames_processed', value=str(metrics.frames_processed)),
                KeyValue(key='frames_dropped', value=str(metrics.frames_dropped)),
                KeyValue(key='total_detections', value=str(metrics.detection_count)),
            ]
            
            # Calculate uptime
            uptime = time.time() - self.start_time
            status.values.append(KeyValue(key='uptime_seconds', value=f'{uptime:.1f}'))
            
            # Calculate detection rate
            if uptime > 0:
                detection_rate = metrics.detection_count / uptime
                status.values.append(KeyValue(key='detections_per_second', value=f'{detection_rate:.2f}'))
            
            diagnostic_array.status.append(status)
            
            # Publish diagnostics
            self.diagnostic_publisher.publish(diagnostic_array)
            
            # Log summary periodically
            if self.frames_processed % 150 == 0:  # Every ~30 seconds at 5fps reporting
                self.node.get_logger().info(
                    f'Performance Summary - FPS: {metrics.frame_rate:.1f}, '
                    f'CPU: {metrics.cpu_usage:.1f}%, Memory: {metrics.memory_usage_mb:.1f}MB, '
                    f'Processed: {metrics.frames_processed}, Dropped: {metrics.frames_dropped}'
                )
        
        except Exception as e:
            self.node.get_logger().error(f'Error publishing performance report: {e}')
    
    def shutdown(self) -> None:
        """Shutdown the performance monitor."""
        self.monitoring_active = False
        
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        # Final performance report
        metrics = self.get_current_metrics()
        uptime = time.time() - self.start_time
        
        self.node.get_logger().info(
            f'Performance Monitor Shutdown Summary:\n'
            f'  Uptime: {uptime:.1f}s\n'
            f'  Frames processed: {metrics.frames_processed}\n'
            f'  Frames dropped: {metrics.frames_dropped}\n'
            f'  Average FPS: {metrics.frame_rate:.2f}\n'
            f'  Total detections: {metrics.detection_count}\n'
            f'  Final CPU usage: {metrics.cpu_usage:.1f}%\n'
            f'  Final memory usage: {metrics.memory_usage_mb:.1f}MB'
        )

def main(args=None):
    """Main entry point for standalone performance monitor node."""
    rclpy.init(args=args)
    
    # Create a simple node for standalone monitoring
    node = Node('system_performance_monitor')
    
    # Declare parameters
    node.declare_parameter('target_fps', 10.0)
    node.declare_parameter('cpu_threshold', 80.0)
    node.declare_parameter('memory_threshold_mb', 500.0)
    node.declare_parameter('monitoring_period', 1.0)
    node.declare_parameter('alert_cooldown', 10.0)
    
    # Get parameters
    target_fps = node.get_parameter('target_fps').get_parameter_value().double_value
    cpu_threshold = node.get_parameter('cpu_threshold').get_parameter_value().double_value
    memory_threshold_mb = node.get_parameter('memory_threshold_mb').get_parameter_value().double_value
    monitoring_period = node.get_parameter('monitoring_period').get_parameter_value().double_value
    alert_cooldown = node.get_parameter('alert_cooldown').get_parameter_value().double_value
    
    # Create performance monitor
    monitor = PerformanceMonitor(
        node=node,
        target_fps=target_fps,
        cpu_threshold=cpu_threshold,
        memory_threshold_mb=memory_threshold_mb
    )
    
    node.get_logger().info(
        f'System Performance Monitor started - '
        f'Target FPS: {target_fps}, CPU Threshold: {cpu_threshold}%, '
        f'Memory Threshold: {memory_threshold_mb}MB'
    )
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Performance monitor interrupted by user')
    finally:
        monitor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()