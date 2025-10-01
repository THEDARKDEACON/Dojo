#!/usr/bin/env python3
"""
Perception Integrator Node

This node integrates data from multiple perception sources:
- Camera feed and object detection
- LiDAR point cloud data
- AI model outputs

It creates a unified representation of the environment with sensor fusion.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, PointCloud2, CameraInfo, LaserScan
from sensor_msgs_py import point_cloud2
from visualization_msgs.msg import MarkerArray, Marker
from geometry_msgs.msg import Point, Pose, Quaternion, Vector3, TransformStamped, PointStamped
from std_msgs.msg import Header, ColorRGBA, Float32MultiArray
import numpy as np
from cv_bridge import CvBridge
import tf2_ros
from tf2_ros import TransformBroadcaster, Buffer, TransformListener
import message_filters
from rclpy.qos import qos_profile_sensor_data
import struct
from sklearn.cluster import DBSCAN
from scipy.spatial import distance
import threading
import time

class Object3D:
    """Represents a 3D object with position, velocity, and classification."""
    def __init__(self, position, classification, confidence, timestamp):
        self.position = np.array(position)  # [x, y, z]
        self.velocity = np.array([0.0, 0.0, 0.0])  # [vx, vy, vz]
        self.classification = classification
        self.confidence = confidence
        self.last_updated = timestamp
        self.id = hash(time.time())  # Simple unique ID
        self.points = []  # LiDAR points associated with this object

class PerceptionIntegrator(Node):
    """
    Integrates data from multiple perception sources to create a unified
    representation of the environment with sensor fusion.
    """
    
    def __init__(self):
        super().__init__('perception_integrator')
        
        # Initialize CV bridge
        self.bridge = CvBridge()
        
        # TF2 setup
        self.tf_broadcaster = TransformBroadcaster(self)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        # Parameters
        self.declare_parameter('object_timeout', 1.0)  # seconds
        self.declare_parameter('min_cluster_size', 10)
        self.declare_parameter('max_cluster_distance', 0.5)  # meters
        
        # Object tracking
        self.tracked_objects = {}
        self.object_id_counter = 0
        self.lock = threading.Lock()
        
        # Subscribers with message filters for time synchronization
        self.object_detection_sub = self.create_subscription(
            MarkerArray,
            '/perception/object_detections/markers',
            self.object_detection_callback,
            10
        )
        
        self.lidar_sub = self.create_subscription(
            PointCloud2 if self.get_parameter('use_pointcloud', True).value else LaserScan,
            '/scan' if not self.get_parameter('use_pointcloud', True).value else '/points2',
            self.lidar_callback,
            qos_profile_sensor_data
        )
        
        # Publishers
        self.integrated_markers_pub = self.create_publisher(
            MarkerArray,
            '/perception/integrated/markers',
            10
        )
        
        self.object_list_pub = self.create_publisher(
            Float32MultiArray,
            '/perception/objects',
            10
        )
        
        # Timer for periodic updates
        self.timer = self.create_timer(0.1, self.timer_callback)
        
        self.get_logger().info('Perception Integrator Node initialized')
    
    def object_detection_callback(self, msg):
        """Process incoming object detection markers and update tracked objects."""
        current_time = self.get_clock().now().nanoseconds / 1e9
        
        with self.lock:
            # Process each detection
            for marker in msg.markers:
                if marker.ns == 'detections' and marker.type == Marker.CUBE:
                    position = [
                        marker.pose.position.x,
                        marker.pose.position.y,
                        marker.pose.position.z
                    ]
                    
                    # Find closest existing object or create new one
                    obj_id, min_dist = self._find_closest_object(position, current_time)
                    
                    if min_dist < 0.5:  # Threshold for association
                        # Update existing object
                        obj = self.tracked_objects[obj_id]
                        obj.position = position
                        obj.classification = marker.text
                        obj.confidence = marker.color.a
                        obj.last_updated = current_time
                    else:
                        # Create new object
                        obj_id = f'obj_{self.object_id_counter}'
                        self.object_id_counter += 1
                        self.tracked_objects[obj_id] = Object3D(
                            position=position,
                            classification=marker.text,
                            confidence=marker.color.a,
                            timestamp=current_time
                        )
    
    def lidar_callback(self, msg):
        """Process LiDAR data and associate points with detected objects."""
        current_time = self.get_clock().now().nanoseconds / 1e9
        
        try:
            # Convert ROS message to point cloud
            if hasattr(msg, 'ranges'):  # LaserScan
                points = self._laser_scan_to_points(msg)
            else:  # PointCloud2
                points = self._pointcloud2_to_points(msg)
                
            if len(points) == 0:
                return
                
            # Cluster points using DBSCAN
            clustering = DBSCAN(
                eps=self.get_parameter('max_cluster_distance').value,
                min_samples=self.get_parameter('min_cluster_size').value
            ).fit(points[:, :3])
            
            # Update object tracking with LiDAR clusters
            self._update_objects_with_lidar(points, clustering.labels_, current_time)
            
        except Exception as e:
            self.get_logger().error(f'Error processing LiDAR data: {str(e)}')
    
    def _update_objects_with_lidar(self, points, labels, timestamp):
        """Update tracked objects with LiDAR cluster information."""
        with self.lock:
            # Reset points for all objects
            for obj in self.tracked_objects.values():
                obj.points = []
            
            # Assign points to objects
            unique_labels = np.unique(labels[labels >= 0])  # Ignore noise (-1)
            for label in unique_labels:
                cluster_points = points[labels == label]
                if len(cluster_points) == 0:
                    continue
                    
                # Calculate cluster center
                center = np.mean(cluster_points, axis=0)
                
                # Find closest object
                obj_id, _ = self._find_closest_object(center, timestamp)
                if obj_id in self.tracked_objects:
                    self.tracked_objects[obj_id].points = cluster_points
    
    def _find_closest_object(self, position, timestamp, max_distance=1.0):
        """Find the closest object to the given position within max_distance."""
        min_dist = float('inf')
        closest_id = None
        position = np.array(position)
        
        for obj_id, obj in self.tracked_objects.items():
            # Skip objects that haven't been updated recently
            if timestamp - obj.last_updated > self.get_parameter('object_timeout').value:
                continue
                
            dist = np.linalg.norm(position - obj.position)
            if dist < min_dist and dist < max_distance:
                min_dist = dist
                closest_id = obj_id
                
        return closest_id, min_dist if closest_id is not None else float('inf')
    
    def _laser_scan_to_points(self, scan):
        """Convert LaserScan message to 3D points."""
        points = []
        angle = scan.angle_min
        
        for i, r in enumerate(scan.ranges):
            if scan.range_min < r < scan.range_max:
                x = r * np.cos(angle)
                y = r * np.sin(angle)
                points.append([x, y, 0.0])
            angle += scan.angle_increment
            
        return np.array(points)
    
    def _pointcloud2_to_points(self, cloud):
        """Convert PointCloud2 message to numpy array."""
        # Read XYZ coordinates from point cloud
        points = []
        for p in point_cloud2.read_points(cloud, field_names=("x", "y", "z"), skip_nans=True):
            points.append([p[0], p[1], p[2]])
        return np.array(points)
    
    def timer_callback(self):
        """Periodic callback to update object tracking and publish results."""
        current_time = self.get_clock().now().nanoseconds / 1e9
        
        # Clean up old objects
        self._cleanup_old_objects(current_time)
        
        # Publish visualization markers
        self._publish_markers()
        
        # Publish object list for other nodes
        self._publish_object_list()
    
    def _cleanup_old_objects(self, current_time):
        """Remove objects that haven't been updated recently."""
        timeout = self.get_parameter('object_timeout').value
        with self.lock:
            to_remove = [
                obj_id for obj_id, obj in self.tracked_objects.items()
                if current_time - obj.last_updated > timeout
            ]
            for obj_id in to_remove:
                del self.tracked_objects[obj_id]
    
    def _publish_markers(self):
        """Publish visualization markers for all tracked objects."""
        marker_array = MarkerArray()
        
        with self.lock:
            for i, (obj_id, obj) in enumerate(self.tracked_objects.items()):
                # Create marker for object
                marker = Marker()
                marker.header.frame_id = 'base_link'
                marker.header.stamp = self.get_clock().now().to_msg()
                marker.ns = 'objects'
                marker.id = i
                marker.type = Marker.CUBE
                marker.action = Marker.ADD
                marker.pose.position.x = obj.position[0]
                marker.pose.position.y = obj.position[1]
                marker.pose.position.z = obj.position[2]
                marker.pose.orientation.w = 1.0
                
                # Set size based on object points or default
                if len(obj.points) > 0:
                    points = np.array(obj.points)
                    min_pt = np.min(points, axis=0)
                    max_pt = np.max(points, axis=0)
                    marker.scale.x = max(0.1, max_pt[0] - min_pt[0])
                    marker.scale.y = max(0.1, max_pt[1] - min_pt[1])
                    marker.scale.z = max(0.1, max_pt[2] - min_pt[2] if len(max_pt) > 2 else 0.2)
                else:
                    marker.scale.x = 0.2
                    marker.scale.y = 0.2
                    marker.scale.z = 0.2
                
                # Set color based on classification
                marker.color = self._get_color_for_class(obj.classification)
                marker.color.a = 0.7  # Semi-transparent
                
                # Add text label
                text_marker = Marker()
                text_marker.header = marker.header
                text_marker.ns = 'labels'
                text_marker.id = i
                text_marker.type = Marker.TEXT_VIEW_FACING
                text_marker.action = Marker.ADD
                text_marker.pose.position = marker.pose.position
                text_marker.pose.position.z += marker.scale.z/2 + 0.1
                text_marker.scale.z = 0.15  # Text size
                text_marker.color.r = 1.0
                text_marker.color.g = 1.0
                text_marker.color.b = 1.0
                text_marker.color.a = 1.0
                text_marker.text = f"{obj.classification} ({obj.confidence:.2f})"
                
                marker_array.markers.append(marker)
                marker_array.markers.append(text_marker)
        
        self.integrated_markers_pub.publish(marker_array)
    
    def _get_color_for_class(self, class_name):
        """Get a consistent color for each object class."""
        color = ColorRGBA()
        # Simple hash-based color assignment
        hue = hash(class_name) % 360 / 360.0
        rgb = self._hsv_to_rgb(hue, 0.8, 0.9)
        color.r = rgb[0]
        color.g = rgb[1]
        color.b = rgb[2]
        return color
    
    def _hsv_to_rgb(self, h, s, v):
        """Convert HSV to RGB color."""
        h_i = int(h * 6)
        f = h * 6 - h_i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        
        if h_i == 0: r, g, b = v, t, p
        elif h_i == 1: r, g, b = q, v, p
        elif h_i == 2: r, g, b = p, v, t
        elif h_i == 3: r, g, b = p, q, v
        elif h_i == 4: r, g, b = t, p, v
        else: r, g, b = v, p, q
            
        return (r, g, b)
    
    def _publish_object_list(self):
        """Publish a list of detected objects with their properties."""
        obj_list = Float32MultiArray()
        
        with self.lock:
            for obj in self.tracked_objects.values():
                # Format: [x, y, z, class_id, confidence]
                # Note: In a real implementation, you'd want to map class names to IDs
                obj_list.data.extend([
                    obj.position[0],  # x
                    obj.position[1],  # y
                    obj.position[2],  # z
                    hash(obj.classification) % 1000,  # Simple class ID
                    obj.confidence    # Detection confidence
                ])
        
        self.object_list_pub.publish(obj_list)

def main(args=None):
    rclpy.init(args=args)
    node = PerceptionIntegrator()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
