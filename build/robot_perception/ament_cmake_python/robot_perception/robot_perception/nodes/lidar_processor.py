#!/usr/bin/env python3
"""
LiDAR Processor Node

This node processes LiDAR scan data to detect obstacles, perform clustering,
and publish point clouds and markers for visualization.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, PointCloud2, PointField
from sensor_msgs_py import point_cloud2
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point, Pose, Quaternion, Vector3, TransformStamped
from std_msgs.msg import ColorRGBA, Header
import numpy as np
import math
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy
import tf2_ros
from tf2_ros import TransformBroadcaster
import tf2_geometry_msgs

class LidarProcessor(Node):
    """Process LiDAR data for obstacle detection and tracking."""
    
    def __init__(self):
        super().__init__('lidar_processor')
        
        # Declare parameters
        self.declare_parameters(
            namespace='',
            parameters=[
                ('enabled', True),
                ('scan_topic', '/scan'),
                ('pointcloud_topic', '/perception/points'),
                ('queue_size', 10),
                ('min_range', 0.1),
                ('max_range', 10.0),
                ('angle_min', -3.14159),
                ('angle_max', 3.14159),
                ('cluster_tolerance', 0.2),
                ('min_cluster_size', 3),
                ('max_cluster_size', 100),
                ('remove_ground', True),
                ('ground_threshold', 0.1),
                ('publish_markers', True),
                ('marker_topic', '/perception/lidar_markers'),
                ('base_frame', 'base_footprint'),
                ('lidar_frame', 'laser'),
                ('debug', False)
            ]
        )
        
        # Get parameters
        self.enabled = self.get_parameter('enabled').value
        self.scan_topic = self.get_parameter('scan_topic').value
        self.pointcloud_topic = self.get_parameter('pointcloud_topic').value
        self.queue_size = self.get_parameter('queue_size').value
        self.min_range = self.get_parameter('min_range').value
        self.max_range = self.get_parameter('max_range').value
        self.angle_min = self.get_parameter('angle_min').value
        self.angle_max = self.get_parameter('angle_max').value
        self.cluster_tolerance = self.get_parameter('cluster_tolerance').value
        self.min_cluster_size = self.get_parameter('min_cluster_size').value
        self.max_cluster_size = self.get_parameter('max_cluster_size').value
        self.remove_ground = self.get_parameter('remove_ground').value
        self.ground_threshold = self.get_parameter('ground_threshold').value
        self.publish_markers = self.get_parameter('publish_markers').value
        self.marker_topic = self.get_parameter('marker_topic').value
        self.base_frame = self.get_parameter('base_frame').value
        self.lidar_frame = self.get_parameter('lidar_frame').value
        self.debug = self.get_parameter('debug').value
        
        # Initialize TF buffer and listener
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # Set up QoS profile for point cloud publishing
        qos_profile = QoSProfile(
            depth=self.queue_size,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE
        )
        
        # Publishers
        self.pointcloud_pub = self.create_publisher(
            PointCloud2,
            self.pointcloud_topic,
            qos_profile=qos_profile
        )
        
        self.marker_pub = self.create_publisher(
            MarkerArray,
            self.marker_topic,
            qos_profile=10
        )
        
        # Subscribers
        self.scan_sub = self.create_subscription(
            LaserScan,
            self.scan_topic,
            self.scan_callback,
            qos_profile=10
        )
        
        self.get_logger().info('LiDAR Processor initialized')
    
    def scan_callback(self, scan_msg):
        """Process incoming laser scan messages."""
        if not self.enabled:
            return
        
        try:
            # Convert scan to cartesian coordinates
            points = self.scan_to_points(scan_msg)
            
            # Filter points by range
            points = self.filter_points(points)
            
            # Remove ground points if enabled
            if self.remove_ground:
                points = self.remove_ground_plane(points)
            
            # Cluster points
            clusters = self.euclidean_clustering(points)
            
            # Publish point cloud
            self.publish_pointcloud(points, scan_msg.header)
            
            # Publish markers for visualization
            if self.publish_markers:
                self.publish_cluster_markers(clusters, scan_msg.header)
                
        except Exception as e:
            self.get_logger().error(f'Error processing scan: {str(e)}', throttle_duration_sec=1.0)
    
    def scan_to_points(self, scan_msg):
        """Convert LaserScan message to list of (x, y) points."""
        points = []
        angle = scan_msg.angle_min
        
        for i, r in enumerate(scan_msg.ranges):
            # Skip invalid measurements
            if math.isnan(r) or r < scan_msg.range_min or r > scan_msg.range_max:
                angle += scan_msg.angle_increment
                continue
                
            # Convert polar to cartesian
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            points.append((x, y, 0.0))  # 2D LiDAR has z=0
            
            angle += scan_msg.angle_increment
            
        return np.array(points)
    
    def filter_points(self, points):
        """Filter points by range and angle."""
        if len(points) == 0:
            return points
            
        # Calculate distances from origin
        distances = np.linalg.norm(points[:, :2], axis=1)
        
        # Filter by range
        mask = (distances >= self.min_range) & (distances <= self.max_range)
        filtered_points = points[mask]
        
        # Filter by angle (if needed)
        if self.angle_min != -math.pi or self.angle_max != math.pi:
            angles = np.arctan2(filtered_points[:, 1], filtered_points[:, 0])
            angle_mask = (angles >= self.angle_min) & (angles <= self.angle_max)
            filtered_points = filtered_points[angle_mask]
            
        return filtered_points
    
    def remove_ground_plane(self, points):
        """Remove ground plane points using simple height thresholding."""
        if len(points) == 0:
            return points
            
        # For 2D LiDAR, we can use a simple height threshold
        # For 3D LiDAR, you might want to use RANSAC or similar
        return points[abs(points[:, 2]) > self.ground_threshold]
    
    def euclidean_clustering(self, points):
        """Cluster points using Euclidean distance."""
        if len(points) == 0:
            return []
            
        from sklearn.cluster import DBSCAN
        
        # Convert to 2D for clustering (ignore z for 2D LiDAR)
        points_2d = points[:, :2]
        
        # DBSCAN clustering
        clustering = DBSCAN(
            eps=self.cluster_tolerance,
            min_samples=self.min_cluster_size
        ).fit(points_2d)
        
        # Get cluster labels
        labels = clustering.labels_
        
        # Group points by cluster
        clusters = []
        for label in np.unique(labels):
            if label == -1:  # Skip noise
                continue
                
            cluster_points = points[labels == label]
            
            # Skip clusters that are too large
            if len(cluster_points) > self.max_cluster_size:
                continue
                
            clusters.append(cluster_points)
            
        return clusters
    
    def publish_pointcloud(self, points, header):
        """Publish point cloud for visualization."""
        if len(points) == 0 or not self.pointcloud_pub.get_subscription_count() > 0:
            return
            
        # Create PointCloud2 message
        fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
        ]
        
        # Convert points to list of tuples
        point_list = [tuple(p) for p in points]
        
        # Create PointCloud2 message
        cloud = point_cloud2.create_cloud(
            header=header,
            fields=fields,
            points=point_list
        )
        
        # Publish point cloud
        self.pointcloud_pub.publish(cloud)
    
    def publish_cluster_markers(self, clusters, header):
        """Publish markers for clusters."""
        if not clusters or not self.marker_pub.get_subscription_count() > 0:
            return
            
        marker_array = MarkerArray()
        
        for i, cluster in enumerate(clusters):
            # Skip empty clusters
            if len(cluster) == 0:
                continue
                
            # Calculate cluster centroid and bounds
            centroid = np.mean(cluster, axis=0)
            min_pt = np.min(cluster, axis=0)
            max_pt = np.max(cluster, axis=0)
            
            # Create marker for cluster
            marker = Marker()
            marker.header = header
            marker.header.frame_id = self.lidar_frame
            marker.ns = 'clusters'
            marker.id = i
            marker.type = Marker.CUBE
            marker.action = Marker.ADD
            
            # Set marker position and orientation
            marker.pose.position.x = float(centroid[0])
            marker.pose.position.y = float(centroid[1])
            marker.pose.position.z = float(centroid[2])
            marker.pose.orientation.w = 1.0
            
            # Set marker scale (size)
            marker.scale.x = float(max_pt[0] - min_pt[0])
            marker.scale.y = float(max_pt[1] - min_pt[1])
            marker.scale.z = 0.1  # Small height for 2D visualization
            
            # Set marker color (red, semi-transparent)
            marker.color.r = 1.0
            marker.color.g = 0.0
            marker.color.b = 0.0
            marker.color.a = 0.5
            
            marker.lifetime = rclpy.duration.Duration(seconds=0.1).to_msg()
            
            marker_array.markers.append(marker)
        
        # Publish markers
        self.marker_pub.publish(marker_array)

def main(args=None):
    rclpy.init(args=args)
    node = LidarProcessor()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
