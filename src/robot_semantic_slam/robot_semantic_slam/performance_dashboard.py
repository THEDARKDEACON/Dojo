#!/usr/bin/env python3
"""
Performance Dashboard Node - Real-time system monitoring and metrics
Dedicated node for comprehensive performance tracking separate from visualization
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from nav_msgs.msg import Path, OccupancyGrid
from geometry_msgs.msg import Twist
from visualization_msgs.msg import MarkerArray, Marker
from std_msgs.msg import ColorRGBA
import psutil
import json
import time
from typing import Dict, Optional
from collections import deque

class PerformanceDashboardNode(Node):
    """Dedicated performance monitoring and dashboard node"""
    
    def __init__(self):
        super().__init__('performance_dashboard')
        
        # Declare parameters
        self.declare_parameter('update_rate', 1.0)  # Hz
        self.declare_parameter('cpu_warning_threshold', 80.0)  # %
        self.declare_parameter('cpu_critical_threshold', 90.0)  # %
        self.declare_parameter('memory_warning_threshold', 80.0)  # %
        self.declare_parameter('memory_critical_threshold', 90.0)  # %
        
        # Get parameters
        update_rate = self.get_parameter('update_rate').value
        self.cpu_warning = self.get_parameter('cpu_warning_threshold').value
        self.cpu_critical = self.get_parameter('cpu_critical_threshold').value
        self.memory_warning = self.get_parameter('memory_warning_threshold').value
        self.memory_critical = self.get_parameter('memory_critical_threshold').value
        
        # Performance metrics
        self.metrics = {
            'cpu_usage': 0.0,
            'memory_usage': 0.0,
            'memory_usage_mb': 0.0,
            'disk_usage': 0.0,
            'network_bandwidth': 0.0,
            'detection_rate': 0.0,
            'navigation_efficiency': 0.0,
            'mapping_coverage': 0.0,
            'safety_level': 0,
            'active_threats': 0,
            'objects_detected': 0,
            'goal_distance': 0.0,
            'current_velocity': 0.0
        }
        
        # Data tracking
        self.semantic_objects = {}
        self.current_map: Optional[OccupancyGrid] = None
        self.current_path: Optional[Path] = None
        self.current_velocity: Optional[Twist] = None
        self.safety_status = {}
        self.current_alerts = []  # Track active alerts for visualization
        
        # Detection rate tracking
        self.detection_timestamps = deque(maxlen=100)
        self.last_object_count = 0
        
        # Network tracking
        self.last_net_io = psutil.net_io_counters()
        self.last_net_time = time.time()
        
        # Publishers
        self.dashboard_pub = self.create_publisher(
            MarkerArray, '/performance_dashboard', 10
        )
        self.metrics_pub = self.create_publisher(
            String, '/performance_metrics_json', 10
        )
        self.alerts_pub = self.create_publisher(
            String, '/performance_alerts', 10
        )
        
        # Subscribers
        self.semantic_map_sub = self.create_subscription(
            String, '/semantic_map', self.semantic_map_callback, 10
        )
        self.plan_sub = self.create_subscription(
            Path, '/plan', self.plan_callback, 10
        )
        self.cmd_vel_sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_vel_callback, 10
        )
        self.safety_sub = self.create_subscription(
            String, '/safety_status', self.safety_callback, 10
        )
        self.map_sub = self.create_subscription(
            OccupancyGrid, '/map', self.map_callback, 10
        )
        
        # Timer for periodic updates
        self.timer = self.create_timer(1.0 / update_rate, self.update_dashboard)
        
        self.get_logger().info(
            f"📊 Performance Dashboard initialized - "
            f"Update rate: {update_rate}Hz, "
            f"CPU warning: {self.cpu_warning}%, "
            f"Memory warning: {self.memory_warning}%"
        )
    
    def semantic_map_callback(self, msg: String):
        """Process semantic map updates"""
        try:
            data = json.loads(msg.data)
            self.semantic_objects = data.get('objects', {})
            
            # Track detection rate
            current_count = len(self.semantic_objects)
            if current_count > self.last_object_count:
                self.detection_timestamps.append(time.time())
            self.last_object_count = current_count
            
        except json.JSONDecodeError:
            self.get_logger().warn("Failed to parse semantic map data")
    
    def plan_callback(self, msg: Path):
        """Process navigation plan updates"""
        self.current_path = msg
    
    def cmd_vel_callback(self, msg: Twist):
        """Process velocity commands"""
        self.current_velocity = msg
    
    def safety_callback(self, msg: String):
        """Process safety status updates"""
        try:
            self.safety_status = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().warn("Failed to parse safety status")
    
    def map_callback(self, msg: OccupancyGrid):
        """Process map updates"""
        self.current_map = msg
    
    def update_dashboard(self):
        """Update all metrics and publish dashboard"""
        # Update system metrics
        self.update_system_metrics()
        
        # Update robotics metrics
        self.update_robotics_metrics()
        
        # Check for alerts
        self.check_alerts()
        
        # Publish metrics
        self.publish_metrics()
        
        # Publish dashboard visualization
        self.publish_dashboard_markers()
    
    def update_system_metrics(self):
        """Update system resource metrics"""
        # CPU usage
        self.metrics['cpu_usage'] = psutil.cpu_percent(interval=None)
        
        # Memory usage
        memory = psutil.virtual_memory()
        self.metrics['memory_usage'] = memory.percent
        self.metrics['memory_usage_mb'] = memory.used / (1024 * 1024)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        self.metrics['disk_usage'] = disk.percent
        
        # Network bandwidth (Mbps)
        current_net_io = psutil.net_io_counters()
        current_time = time.time()
        time_delta = current_time - self.last_net_time
        
        if time_delta > 0:
            bytes_sent = current_net_io.bytes_sent - self.last_net_io.bytes_sent
            bytes_recv = current_net_io.bytes_recv - self.last_net_io.bytes_recv
            total_bytes = bytes_sent + bytes_recv
            
            # Convert to Mbps
            self.metrics['network_bandwidth'] = (total_bytes * 8) / (time_delta * 1_000_000)
        
        self.last_net_io = current_net_io
        self.last_net_time = current_time
    
    def update_robotics_metrics(self):
        """Update robotics-specific metrics"""
        # Detection rate (detections per second)
        if self.detection_timestamps:
            current_time = time.time()
            recent_detections = [
                t for t in self.detection_timestamps 
                if current_time - t < 10.0  # Last 10 seconds
            ]
            self.metrics['detection_rate'] = len(recent_detections) / 10.0
        
        # Objects detected
        self.metrics['objects_detected'] = len(self.semantic_objects)
        
        # Mapping coverage
        if self.current_map:
            total_cells = len(self.current_map.data)
            if total_cells > 0:
                known_cells = sum(1 for cell in self.current_map.data if cell != -1)
                self.metrics['mapping_coverage'] = (known_cells / total_cells) * 100.0
        
        # Navigation efficiency (based on path smoothness)
        if self.current_path and len(self.current_path.poses) > 2:
            # Calculate path smoothness
            total_angle_change = 0.0
            for i in range(1, len(self.current_path.poses) - 1):
                # Simple angle change calculation
                p1 = self.current_path.poses[i-1].pose.position
                p2 = self.current_path.poses[i].pose.position
                p3 = self.current_path.poses[i+1].pose.position
                
                import math
                angle1 = math.atan2(p2.y - p1.y, p2.x - p1.x)
                angle2 = math.atan2(p3.y - p2.y, p3.x - p2.x)
                angle_diff = abs(angle2 - angle1)
                
                # Normalize to [0, pi]
                if angle_diff > math.pi:
                    angle_diff = 2 * math.pi - angle_diff
                
                total_angle_change += angle_diff
            
            # Efficiency: smoother path = higher efficiency
            avg_angle_change = total_angle_change / (len(self.current_path.poses) - 2)
            self.metrics['navigation_efficiency'] = max(0, 100 * (1.0 - avg_angle_change / math.pi))
        
        # Current velocity
        if self.current_velocity:
            import math
            self.metrics['current_velocity'] = math.sqrt(
                self.current_velocity.linear.x ** 2 + 
                self.current_velocity.linear.y ** 2
            )
        
        # Goal distance
        if self.current_path and len(self.current_path.poses) > 0:
            # Distance to goal (last pose in path)
            goal_pose = self.current_path.poses[-1].pose.position
            start_pose = self.current_path.poses[0].pose.position
            import math
            self.metrics['goal_distance'] = math.sqrt(
                (goal_pose.x - start_pose.x) ** 2 + 
                (goal_pose.y - start_pose.y) ** 2
            )
        
        # Safety metrics
        if self.safety_status:
            self.metrics['safety_level'] = self.safety_status.get('safety_level', 0)
            self.metrics['active_threats'] = self.safety_status.get('active_threats', 0)
    
    def check_alerts(self):
        """Check metrics against thresholds and generate alerts"""
        alerts = []
        
        # CPU alerts
        if self.metrics['cpu_usage'] >= self.cpu_critical:
            alerts.append({
                'level': 'CRITICAL',
                'metric': 'CPU',
                'value': self.metrics['cpu_usage'],
                'message': f"CPU usage critical: {self.metrics['cpu_usage']:.1f}%"
            })
        elif self.metrics['cpu_usage'] >= self.cpu_warning:
            alerts.append({
                'level': 'WARNING',
                'metric': 'CPU',
                'value': self.metrics['cpu_usage'],
                'message': f"CPU usage high: {self.metrics['cpu_usage']:.1f}%"
            })
        
        # Memory alerts
        if self.metrics['memory_usage'] >= self.memory_critical:
            alerts.append({
                'level': 'CRITICAL',
                'metric': 'Memory',
                'value': self.metrics['memory_usage'],
                'message': f"Memory usage critical: {self.metrics['memory_usage']:.1f}%"
            })
        elif self.metrics['memory_usage'] >= self.memory_warning:
            alerts.append({
                'level': 'WARNING',
                'metric': 'Memory',
                'value': self.metrics['memory_usage'],
                'message': f"Memory usage high: {self.metrics['memory_usage']:.1f}%"
            })
        
        # Safety alerts
        if self.metrics['active_threats'] > 0:
            alerts.append({
                'level': 'WARNING',
                'metric': 'Safety',
                'value': self.metrics['active_threats'],
                'message': f"Active threats detected: {self.metrics['active_threats']}"
            })
        
        # Store current alerts for visualization
        self.current_alerts = alerts
        
        # Publish alerts
        if alerts:
            alert_msg = String()
            alert_msg.data = json.dumps(alerts)
            self.alerts_pub.publish(alert_msg)
            
            # Log critical alerts
            for alert in alerts:
                if alert['level'] == 'CRITICAL':
                    self.get_logger().error(f"🚨 {alert['message']}")
                elif alert['level'] == 'WARNING':
                    self.get_logger().warn(f"⚠️  {alert['message']}")
    
    def publish_metrics(self):
        """Publish metrics as JSON"""
        metrics_msg = String()
        metrics_data = {
            'timestamp': self.get_clock().now().to_msg().sec,
            'metrics': self.metrics
        }
        metrics_msg.data = json.dumps(metrics_data)
        self.metrics_pub.publish(metrics_msg)
    
    def publish_dashboard_markers(self):
        """Publish dashboard visualization markers for RViz"""
        markers = MarkerArray()
        
        # Create dashboard panel
        panel_marker = self.create_dashboard_panel()
        markers.markers.append(panel_marker)
        
        # Create metric text markers
        text_markers = self.create_metric_text_markers()
        markers.markers.extend(text_markers)
        
        # Create progress bars for percentage metrics
        progress_bars = self.create_progress_bars()
        markers.markers.extend(progress_bars)
        
        # Create visual alert indicators
        alert_markers = self.create_alert_indicators()
        markers.markers.extend(alert_markers)
        
        self.dashboard_pub.publish(markers)
    
    def create_dashboard_panel(self) -> Marker:
        """Create background panel for dashboard"""
        marker = Marker()
        marker.header.frame_id = "map"
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "dashboard_panel"
        marker.id = 0
        marker.type = Marker.CUBE
        marker.action = Marker.ADD
        
        # Position in top-right of view
        marker.pose.position.x = 5.0
        marker.pose.position.y = 5.0
        marker.pose.position.z = 2.0
        marker.pose.orientation.w = 1.0
        
        # Size
        marker.scale.x = 3.0
        marker.scale.y = 0.1
        marker.scale.z = 2.5
        
        # Semi-transparent dark background
        marker.color.r = 0.1
        marker.color.g = 0.1
        marker.color.b = 0.1
        marker.color.a = 0.7
        
        return marker
    
    def create_metric_text_markers(self) -> list:
        """Create text markers for each metric"""
        markers = []
        
        # Dashboard title
        title_marker = self.create_text_marker(
            1, "PERFORMANCE DASHBOARD", 
            5.0, 5.0, 3.0, 
            0.15, ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)
        )
        markers.append(title_marker)
        
        # System Health Section
        y_offset = 2.7
        markers.append(self.create_text_marker(
            2, "System Health:", 5.0, 5.0, y_offset, 0.1,
            ColorRGBA(r=0.8, g=0.8, b=1.0, a=1.0)
        ))
        
        y_offset -= 0.2
        cpu_color = self.get_metric_color(
            self.metrics['cpu_usage'], self.cpu_warning, self.cpu_critical
        )
        markers.append(self.create_text_marker(
            3, f"  CPU: {self.metrics['cpu_usage']:.1f}%", 
            5.0, 5.0, y_offset, 0.08, cpu_color
        ))
        
        y_offset -= 0.15
        mem_color = self.get_metric_color(
            self.metrics['memory_usage'], self.memory_warning, self.memory_critical
        )
        markers.append(self.create_text_marker(
            4, f"  Memory: {self.metrics['memory_usage']:.1f}% ({self.metrics['memory_usage_mb']:.0f}MB)", 
            5.0, 5.0, y_offset, 0.08, mem_color
        ))
        
        y_offset -= 0.15
        markers.append(self.create_text_marker(
            5, f"  Network: {self.metrics['network_bandwidth']:.2f} Mbps", 
            5.0, 5.0, y_offset, 0.08, ColorRGBA(r=0.7, g=0.7, b=0.7, a=1.0)
        ))
        
        # Navigation Section
        y_offset -= 0.3
        markers.append(self.create_text_marker(
            6, "Navigation:", 5.0, 5.0, y_offset, 0.1,
            ColorRGBA(r=0.8, g=1.0, b=0.8, a=1.0)
        ))
        
        y_offset -= 0.2
        markers.append(self.create_text_marker(
            7, f"  Efficiency: {self.metrics['navigation_efficiency']:.1f}%", 
            5.0, 5.0, y_offset, 0.08, ColorRGBA(r=0.7, g=0.7, b=0.7, a=1.0)
        ))
        
        y_offset -= 0.15
        markers.append(self.create_text_marker(
            8, f"  Goal Distance: {self.metrics['goal_distance']:.2f}m", 
            5.0, 5.0, y_offset, 0.08, ColorRGBA(r=0.7, g=0.7, b=0.7, a=1.0)
        ))
        
        y_offset -= 0.15
        markers.append(self.create_text_marker(
            9, f"  Velocity: {self.metrics['current_velocity']:.2f}m/s", 
            5.0, 5.0, y_offset, 0.08, ColorRGBA(r=0.7, g=0.7, b=0.7, a=1.0)
        ))
        
        # Perception Section
        y_offset -= 0.3
        markers.append(self.create_text_marker(
            10, "Perception:", 5.0, 5.0, y_offset, 0.1,
            ColorRGBA(r=1.0, g=0.8, b=0.8, a=1.0)
        ))
        
        y_offset -= 0.2
        markers.append(self.create_text_marker(
            11, f"  Objects: {self.metrics['objects_detected']}", 
            5.0, 5.0, y_offset, 0.08, ColorRGBA(r=0.7, g=0.7, b=0.7, a=1.0)
        ))
        
        y_offset -= 0.15
        markers.append(self.create_text_marker(
            12, f"  Detection Rate: {self.metrics['detection_rate']:.2f}/s", 
            5.0, 5.0, y_offset, 0.08, ColorRGBA(r=0.7, g=0.7, b=0.7, a=1.0)
        ))
        
        y_offset -= 0.15
        markers.append(self.create_text_marker(
            13, f"  Map Coverage: {self.metrics['mapping_coverage']:.1f}%", 
            5.0, 5.0, y_offset, 0.08, ColorRGBA(r=0.7, g=0.7, b=0.7, a=1.0)
        ))
        
        # Safety Section
        y_offset -= 0.3
        markers.append(self.create_text_marker(
            14, "Safety:", 5.0, 5.0, y_offset, 0.1,
            ColorRGBA(r=1.0, g=1.0, b=0.8, a=1.0)
        ))
        
        y_offset -= 0.2
        safety_color = ColorRGBA(r=0.0, g=1.0, b=0.0, a=1.0) if self.metrics['active_threats'] == 0 else ColorRGBA(r=1.0, g=0.0, b=0.0, a=1.0)
        markers.append(self.create_text_marker(
            15, f"  Active Threats: {self.metrics['active_threats']}", 
            5.0, 5.0, y_offset, 0.08, safety_color
        ))
        
        return markers
    
    def create_text_marker(self, marker_id: int, text: str, x: float, y: float, z: float, 
                          scale: float, color: ColorRGBA) -> Marker:
        """Create a text marker"""
        marker = Marker()
        marker.header.frame_id = "map"
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "dashboard_text"
        marker.id = marker_id
        marker.type = Marker.TEXT_VIEW_FACING
        marker.action = Marker.ADD
        
        marker.pose.position.x = x
        marker.pose.position.y = y
        marker.pose.position.z = z
        marker.pose.orientation.w = 1.0
        
        marker.scale.z = scale
        marker.color = color
        marker.text = text
        
        return marker
    
    def get_metric_color(self, value: float, warning: float, critical: float) -> ColorRGBA:
        """Get color based on metric thresholds"""
        if value >= critical:
            return ColorRGBA(r=1.0, g=0.0, b=0.0, a=1.0)  # Red
        elif value >= warning:
            return ColorRGBA(r=1.0, g=0.65, b=0.0, a=1.0)  # Orange
        else:
            return ColorRGBA(r=0.0, g=1.0, b=0.0, a=1.0)  # Green
    
    def create_progress_bars(self) -> list:
        """Create visual progress bars for percentage metrics"""
        markers = []
        base_id = 100  # Start IDs at 100 to avoid conflicts with text markers
        
        # Progress bar configuration
        bar_width = 1.0
        bar_height = 0.08
        bar_x = 6.2  # To the right of text
        
        # CPU progress bar
        y_offset = 2.5
        cpu_bar = self.create_progress_bar(
            base_id, bar_x, 5.0, y_offset,
            bar_width, bar_height,
            self.metrics['cpu_usage'] / 100.0,
            self.get_metric_color(self.metrics['cpu_usage'], self.cpu_warning, self.cpu_critical)
        )
        markers.extend(cpu_bar)
        
        # Memory progress bar
        y_offset = 2.35
        mem_bar = self.create_progress_bar(
            base_id + 2, bar_x, 5.0, y_offset,
            bar_width, bar_height,
            self.metrics['memory_usage'] / 100.0,
            self.get_metric_color(self.metrics['memory_usage'], self.memory_warning, self.memory_critical)
        )
        markers.extend(mem_bar)
        
        # Navigation efficiency progress bar
        y_offset = 1.75
        nav_bar = self.create_progress_bar(
            base_id + 4, bar_x, 5.0, y_offset,
            bar_width, bar_height,
            self.metrics['navigation_efficiency'] / 100.0,
            ColorRGBA(r=0.0, g=0.7, b=1.0, a=0.8)  # Blue for navigation
        )
        markers.extend(nav_bar)
        
        # Mapping coverage progress bar
        y_offset = 1.0
        map_bar = self.create_progress_bar(
            base_id + 6, bar_x, 5.0, y_offset,
            bar_width, bar_height,
            self.metrics['mapping_coverage'] / 100.0,
            ColorRGBA(r=0.0, g=1.0, b=0.5, a=0.8)  # Green-cyan for mapping
        )
        markers.extend(map_bar)
        
        return markers
    
    def create_progress_bar(self, base_id: int, x: float, y: float, z: float,
                           width: float, height: float, fill_ratio: float,
                           color: ColorRGBA) -> list:
        """Create a progress bar with background and filled portion"""
        markers = []
        
        # Clamp fill_ratio to [0, 1]
        fill_ratio = max(0.0, min(1.0, fill_ratio))
        
        # Background bar (gray)
        bg_marker = Marker()
        bg_marker.header.frame_id = "map"
        bg_marker.header.stamp = self.get_clock().now().to_msg()
        bg_marker.ns = "progress_bars_bg"
        bg_marker.id = base_id
        bg_marker.type = Marker.CUBE
        bg_marker.action = Marker.ADD
        
        bg_marker.pose.position.x = x
        bg_marker.pose.position.y = y
        bg_marker.pose.position.z = z
        bg_marker.pose.orientation.w = 1.0
        
        bg_marker.scale.x = width
        bg_marker.scale.y = 0.02
        bg_marker.scale.z = height
        
        bg_marker.color.r = 0.3
        bg_marker.color.g = 0.3
        bg_marker.color.b = 0.3
        bg_marker.color.a = 0.5
        
        markers.append(bg_marker)
        
        # Filled portion (colored based on value)
        if fill_ratio > 0.01:  # Only show if there's something to display
            fill_marker = Marker()
            fill_marker.header.frame_id = "map"
            fill_marker.header.stamp = self.get_clock().now().to_msg()
            fill_marker.ns = "progress_bars_fill"
            fill_marker.id = base_id + 1
            fill_marker.type = Marker.CUBE
            fill_marker.action = Marker.ADD
            
            # Position filled portion to grow from left
            fill_width = width * fill_ratio
            fill_marker.pose.position.x = x - (width - fill_width) / 2.0
            fill_marker.pose.position.y = y
            fill_marker.pose.position.z = z
            fill_marker.pose.orientation.w = 1.0
            
            fill_marker.scale.x = fill_width
            fill_marker.scale.y = 0.03
            fill_marker.scale.z = height
            
            fill_marker.color = color
            
            markers.append(fill_marker)
        
        return markers
    
    def create_alert_indicators(self) -> list:
        """Create visual alert indicators in RViz"""
        markers = []
        
        if not self.current_alerts:
            return markers
        
        # Determine highest alert level
        has_critical = any(alert['level'] == 'CRITICAL' for alert in self.current_alerts)
        has_warning = any(alert['level'] == 'WARNING' for alert in self.current_alerts)
        
        # Create pulsing alert beacon above dashboard
        beacon_marker = Marker()
        beacon_marker.header.frame_id = "map"
        beacon_marker.header.stamp = self.get_clock().now().to_msg()
        beacon_marker.ns = "alert_beacon"
        beacon_marker.id = 200
        beacon_marker.type = Marker.SPHERE
        beacon_marker.action = Marker.ADD
        
        # Position above dashboard
        beacon_marker.pose.position.x = 5.0
        beacon_marker.pose.position.y = 5.0
        beacon_marker.pose.position.z = 3.5
        beacon_marker.pose.orientation.w = 1.0
        
        # Size based on alert level
        if has_critical:
            beacon_marker.scale.x = 0.5
            beacon_marker.scale.y = 0.5
            beacon_marker.scale.z = 0.5
            beacon_marker.color = ColorRGBA(r=1.0, g=0.0, b=0.0, a=0.9)  # Red
        else:
            beacon_marker.scale.x = 0.3
            beacon_marker.scale.y = 0.3
            beacon_marker.scale.z = 0.3
            beacon_marker.color = ColorRGBA(r=1.0, g=0.65, b=0.0, a=0.8)  # Orange
        
        markers.append(beacon_marker)
        
        # Create alert text banner
        alert_text = f"⚠️  {len(self.current_alerts)} ALERT(S) ACTIVE"
        if has_critical:
            alert_text = f"🚨 CRITICAL ALERT"
        
        banner_marker = Marker()
        banner_marker.header.frame_id = "map"
        banner_marker.header.stamp = self.get_clock().now().to_msg()
        banner_marker.ns = "alert_banner"
        banner_marker.id = 201
        banner_marker.type = Marker.TEXT_VIEW_FACING
        banner_marker.action = Marker.ADD
        
        banner_marker.pose.position.x = 5.0
        banner_marker.pose.position.y = 5.0
        banner_marker.pose.position.z = 3.8
        banner_marker.pose.orientation.w = 1.0
        
        banner_marker.scale.z = 0.2
        banner_marker.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)
        banner_marker.text = alert_text
        
        markers.append(banner_marker)
        
        # Create alert detail markers (list of active alerts)
        y_offset = 3.3
        for idx, alert in enumerate(self.current_alerts[:3]):  # Show max 3 alerts
            detail_marker = Marker()
            detail_marker.header.frame_id = "map"
            detail_marker.header.stamp = self.get_clock().now().to_msg()
            detail_marker.ns = "alert_details"
            detail_marker.id = 202 + idx
            detail_marker.type = Marker.TEXT_VIEW_FACING
            detail_marker.action = Marker.ADD
            
            detail_marker.pose.position.x = 5.0
            detail_marker.pose.position.y = 5.0
            detail_marker.pose.position.z = y_offset
            detail_marker.pose.orientation.w = 1.0
            
            detail_marker.scale.z = 0.08
            
            # Color based on alert level
            if alert['level'] == 'CRITICAL':
                detail_marker.color = ColorRGBA(r=1.0, g=0.0, b=0.0, a=1.0)
                icon = "🚨"
            else:
                detail_marker.color = ColorRGBA(r=1.0, g=0.65, b=0.0, a=1.0)
                icon = "⚠️"
            
            detail_marker.text = f"{icon} {alert['metric']}: {alert['value']:.1f}"
            
            markers.append(detail_marker)
            y_offset -= 0.12
        
        return markers

def main(args=None):
    rclpy.init(args=args)
    node = PerformanceDashboardNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
