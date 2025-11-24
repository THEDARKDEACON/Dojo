#!/usr/bin/env python3
"""
Enhanced 3D Visualization System - Real-time performance dashboard and 3D mapping
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, Image
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid, Path
from std_msgs.msg import String, Float32MultiArray
from visualization_msgs.msg import Marker, MarkerArray
import numpy as np
import json
from typing import Dict, List
import time

class EnhancedVisualizerNode(Node):
    """Advanced 3D visualization with performance monitoring"""
    
    def __init__(self):
        super().__init__('enhanced_visualizer')
        
        # Performance metrics
        self.metrics = {
            'fps': 0.0,
            'cpu_usage': 0.0,
            'memory_usage': 0.0,
            'navigation_efficiency': 0.0,
            'detection_rate': 0.0,
            'mapping_coverage': 0.0
        }
        
        # Publishers
        self.marker_pub = self.create_publisher(MarkerArray, '/semantic_markers', 10)
        self.performance_pub = self.create_publisher(Float32MultiArray, '/performance_metrics', 10)
        self.dashboard_pub = self.create_publisher(String, '/dashboard_data', 10)
        
        # Subscribers
        self.semantic_map_sub = self.create_subscription(String, '/semantic_map', self.semantic_map_callback, 10)
        self.pose_sub = self.create_subscription(PoseStamped, '/robot_pose', self.pose_callback, 10)
        self.map_sub = self.create_subscription(OccupancyGrid, '/map', self.map_callback, 10)
        self.path_sub = self.create_subscription(Path, '/plan', self.path_callback, 10)
        
        # Visualization data
        self.semantic_objects = {}
        self.robot_path = []
        self.current_pose = None
        self.current_map = None
        
        # Performance tracking
        self.frame_times = []
        self.last_frame_time = time.time()
        
        # Timers
        self.viz_timer = self.create_timer(0.1, self.update_visualization)  # 10 Hz
        self.metrics_timer = self.create_timer(1.0, self.update_metrics)    # 1 Hz
        
        self.get_logger().info("🎨 Enhanced 3D Visualizer initialized - Real-time dashboard active!")
    
    def semantic_map_callback(self, msg: String):
        """Process semantic map updates"""
        try:
            data = json.loads(msg.data)
            self.semantic_objects = data.get('objects', {})
        except json.JSONDecodeError:
            self.get_logger().warn("Failed to parse semantic map data")
    
    def pose_callback(self, msg: PoseStamped):
        """Track robot pose for path visualization"""
        self.current_pose = msg
        
        # Add to path history (keep last 1000 points)
        pose_point = [msg.pose.position.x, msg.pose.position.y, msg.pose.position.z]
        self.robot_path.append(pose_point)
        if len(self.robot_path) > 1000:
            self.robot_path.pop(0)
    
    def map_callback(self, msg: OccupancyGrid):
        """Process map updates for coverage calculation"""
        self.current_map = msg
    
    def path_callback(self, msg: Path):
        """Process planned path for visualization"""
        # Could visualize planned vs actual path
        pass
    
    def update_visualization(self):
        """Update 3D visualization markers"""
        markers = MarkerArray()
        marker_id = 0
        
        # Clear previous markers
        clear_marker = Marker()
        clear_marker.action = Marker.DELETEALL
        markers.markers.append(clear_marker)
        
        # Visualize semantic objects
        for obj_id, obj_data in self.semantic_objects.items():
            marker = self.create_object_marker(obj_id, obj_data, marker_id)
            markers.markers.append(marker)
            marker_id += 1
        
        # Visualize robot path
        if len(self.robot_path) > 1:
            path_marker = self.create_path_marker(marker_id)
            markers.markers.append(path_marker)
            marker_id += 1
        
        # Visualize performance zones
        if self.current_pose:
            perf_marker = self.create_performance_marker(marker_id)
            markers.markers.append(perf_marker)
        
        self.marker_pub.publish(markers)
        
        # Update FPS
        current_time = time.time()
        frame_time = current_time - self.last_frame_time
        self.frame_times.append(frame_time)
        if len(self.frame_times) > 30:  # Keep last 30 frames
            self.frame_times.pop(0)
        self.last_frame_time = current_time
    
    def create_object_marker(self, obj_id: str, obj_data: Dict, marker_id: int) -> Marker:
        """Create 3D marker for detected object"""
        marker = Marker()
        marker.header.frame_id = "map"
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "semantic_objects"
        marker.id = marker_id
        marker.type = Marker.CYLINDER
        marker.action = Marker.ADD
        
        # Position
        marker.pose.position.x = obj_data['x']
        marker.pose.position.y = obj_data['y']
        marker.pose.position.z = 0.5  # Half meter height
        marker.pose.orientation.w = 1.0
        
        # Scale based on confidence
        confidence = obj_data.get('confidence', 0.5)
        marker.scale.x = 0.3 + confidence * 0.2  # 0.3-0.5m diameter
        marker.scale.y = 0.3 + confidence * 0.2
        marker.scale.z = 1.0
        
        # Color based on object class
        marker.color = self.get_object_color(obj_data['class'])
        marker.color.a = 0.7 + confidence * 0.3  # Transparency based on confidence
        
        # Add text label
        marker.text = f"{obj_data['class']}\n{confidence:.2f}"
        
        return marker
    
    def create_path_marker(self, marker_id: int) -> Marker:
        """Create path visualization marker"""
        marker = Marker()
        marker.header.frame_id = "map"
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "robot_path"
        marker.id = marker_id
        marker.type = Marker.LINE_STRIP
        marker.action = Marker.ADD
        
        # Path points
        for point in self.robot_path:
            p = marker.points.add() if hasattr(marker.points, 'add') else marker.points.append()
            p.x = point[0]
            p.y = point[1]
            p.z = 0.1  # Slightly above ground
        
        # Style
        marker.scale.x = 0.05  # Line width
        marker.color.r = 0.0
        marker.color.g = 0.5
        marker.color.b = 1.0
        marker.color.a = 0.8
        
        return marker
    
    def create_performance_marker(self, marker_id: int) -> Marker:
        """Create performance indicator around robot"""
        marker = Marker()
        marker.header.frame_id = "map"
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "performance"
        marker.id = marker_id
        marker.type = Marker.CYLINDER
        marker.action = Marker.ADD
        
        # Position at robot
        marker.pose.position.x = self.current_pose.pose.position.x
        marker.pose.position.y = self.current_pose.pose.position.y
        marker.pose.position.z = 0.01
        marker.pose.orientation.w = 1.0
        
        # Scale based on overall performance
        overall_perf = (self.metrics['navigation_efficiency'] + 
                       self.metrics['detection_rate'] + 
                       self.metrics['mapping_coverage']) / 3.0
        
        marker.scale.x = 1.0 + overall_perf
        marker.scale.y = 1.0 + overall_perf
        marker.scale.z = 0.02
        
        # Color based on performance (green = good, red = poor)
        marker.color.r = 1.0 - overall_perf
        marker.color.g = overall_perf
        marker.color.b = 0.0
        marker.color.a = 0.3
        
        return marker
    
    def get_object_color(self, class_name: str):
        """Get color for object class"""
        colors = {
            'person': {'r': 1.0, 'g': 0.0, 'b': 0.0},      # Red
            'chair': {'r': 0.0, 'g': 1.0, 'b': 0.0},       # Green
            'table': {'r': 0.0, 'g': 0.0, 'b': 1.0},       # Blue
            'bottle': {'r': 1.0, 'g': 1.0, 'b': 0.0},      # Yellow
            'cup': {'r': 1.0, 'g': 0.0, 'b': 1.0},         # Magenta
            'book': {'r': 0.0, 'g': 1.0, 'b': 1.0},        # Cyan
        }
        
        color = colors.get(class_name.lower(), {'r': 0.5, 'g': 0.5, 'b': 0.5})  # Default gray
        
        marker_color = type('Color', (), {})()
        marker_color.r = color['r']
        marker_color.g = color['g']
        marker_color.b = color['b']
        
        return marker_color
    
    def update_metrics(self):
        """Calculate and publish performance metrics"""
        # Calculate FPS
        if self.frame_times:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            self.metrics['fps'] = 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
        
        # Calculate detection rate (objects per minute)
        total_detections = sum(obj.get('detections', 0) for obj in self.semantic_objects.values())
        self.metrics['detection_rate'] = min(total_detections / 60.0, 1.0)  # Normalized
        
        # Calculate mapping coverage (simplified)
        if self.current_map:
            total_cells = len(self.current_map.data)
            known_cells = sum(1 for cell in self.current_map.data if cell != -1)
            self.metrics['mapping_coverage'] = known_cells / total_cells if total_cells > 0 else 0.0
        
        # Navigation efficiency (simplified - based on path smoothness)
        if len(self.robot_path) > 10:
            # Calculate path smoothness as efficiency metric
            path_changes = 0
            for i in range(1, len(self.robot_path)):
                if i < len(self.robot_path) - 1:
                    # Calculate angle change
                    v1 = np.array(self.robot_path[i]) - np.array(self.robot_path[i-1])
                    v2 = np.array(self.robot_path[i+1]) - np.array(self.robot_path[i])
                    if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                        angle_change = np.arccos(np.clip(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)), -1, 1))
                        path_changes += angle_change
            
            # Normalize (smoother path = higher efficiency)
            self.metrics['navigation_efficiency'] = max(0, 1.0 - path_changes / len(self.robot_path))
        
        # Publish metrics
        metrics_msg = Float32MultiArray()
        metrics_msg.data = [
            self.metrics['fps'],
            self.metrics['cpu_usage'],
            self.metrics['memory_usage'],
            self.metrics['navigation_efficiency'],
            self.metrics['detection_rate'],
            self.metrics['mapping_coverage']
        ]
        self.performance_pub.publish(metrics_msg)
        
        # Publish dashboard data
        dashboard_data = {
            'timestamp': self.get_clock().now().to_msg().sec,
            'metrics': self.metrics,
            'objects_detected': len(self.semantic_objects),
            'path_length': len(self.robot_path),
            'status': 'active' if self.current_pose else 'inactive'
        }
        
        dashboard_msg = String()
        dashboard_msg.data = json.dumps(dashboard_data)
        self.dashboard_pub.publish(dashboard_msg)
        
        # Log performance summary
        self.get_logger().info(
            f"📊 Performance: FPS={self.metrics['fps']:.1f}, "
            f"Objects={len(self.semantic_objects)}, "
            f"Nav Eff={self.metrics['navigation_efficiency']:.2f}, "
            f"Coverage={self.metrics['mapping_coverage']:.2f}"
        )

def main(args=None):
    rclpy.init(args=args)
    node = EnhancedVisualizerNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down enhanced visualizer...')
    except Exception as e:
        node.get_logger().error(f'Error in enhanced visualizer: {e}')
    finally:
        node.destroy_node()
        # Don't call rclpy.shutdown() - let launch system handle it

if __name__ == '__main__':
    main()