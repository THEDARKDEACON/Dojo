#!/usr/bin/env python3
"""
PointCloud Processor - 3D Point Cloud Visualization
Converts 2D LaserScan data to 3D PointCloud2 for RViz visualization
Includes scan accumulation for dense mapping with TF2 transformation and voxel filtering
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, PointCloud2, PointField
from geometry_msgs.msg import PoseStamped, TransformStamped
import numpy as np
import struct
from typing import List, Dict, Tuple
import time
from collections import deque
import tf2_ros
from tf2_ros import TransformException
import tf2_geometry_msgs

class PointCloudProcessor(Node):
    """Convert LaserScan to PointCloud2 for 3D visualization"""
    
    def __init__(self):
        super().__init__('pointcloud_processor')
        
        # Declare parameters
        self.declare_parameter('update_rate', 10.0)  # Hz
        self.declare_parameter('z_height', 0.3)  # Default height for 2D scan
        self.declare_parameter('point_size', 0.05)  # Point size in meters
        
        # Task 3.2: Scan accumulation parameters (optimized for performance)
        self.declare_parameter('accumulation_time', 8.0)  # seconds (reduced from 10s)
        self.declare_parameter('voxel_size', 0.08)  # meters (increased for more aggressive downsampling)
        self.declare_parameter('max_points', 500000)  # Maximum points in dense map (reduced from 1M)
        self.declare_parameter('enable_accumulation', True)  # Enable dense mapping
        self.declare_parameter('cleanup_frequency', 2.0)  # Hz for cleanup (optimized)
        
        # Task 3.3: Height-based color mapping parameters
        self.declare_parameter('color_mode', 'height')  # 'height', 'intensity', or 'fixed'
        self.declare_parameter('min_height', -0.5)  # Minimum height for color mapping (red)
        self.declare_parameter('max_height', 2.0)  # Maximum height for color mapping (violet)
        self.declare_parameter('color_scheme', 'rainbow')  # 'rainbow', 'jet', 'hot', 'cool'
        
        # Get parameters
        self.update_rate = self.get_parameter('update_rate').value
        self.z_height = self.get_parameter('z_height').value
        self.point_size = self.get_parameter('point_size').value
        self.accumulation_time = self.get_parameter('accumulation_time').value
        self.voxel_size = self.get_parameter('voxel_size').value
        self.max_points = self.get_parameter('max_points').value
        self.enable_accumulation = self.get_parameter('enable_accumulation').value
        self.color_mode = self.get_parameter('color_mode').value
        self.min_height = self.get_parameter('min_height').value
        self.max_height = self.get_parameter('max_height').value
        self.color_scheme = self.get_parameter('color_scheme').value
        
        # State
        self.current_scan = None
        self.current_pose = None
        self.last_publish_time = time.time()
        
        # Scan accumulation state
        self.accumulated_scans = deque()  # Store (timestamp, points_in_map_frame)
        self.voxel_grid = {}  # Voxel grid for downsampling: {voxel_key: point}
        
        # TF2 for coordinate transformations
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        
        # Publishers
        self.pointcloud_pub = self.create_publisher(
            PointCloud2, '/pointcloud', 10)
        self.dense_map_pub = self.create_publisher(
            PointCloud2, '/dense_map', 10)
        
        # Subscribers
        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10)
        self.pose_sub = self.create_subscription(
            PoseStamped, '/robot_pose', self.pose_callback, 10)
        
        # Timer for publishing at fixed rate
        publish_period = 1.0 / self.update_rate
        self.publish_timer = self.create_timer(publish_period, self.publish_pointcloud)
        
        # Timer for dense map cleanup (optimized frequency)
        if self.enable_accumulation:
            cleanup_freq = self.get_parameter('cleanup_frequency').value
            self.cleanup_timer = self.create_timer(1.0 / cleanup_freq, self.cleanup_old_scans)
        
        self.get_logger().info(f"🌐 PointCloud Processor initialized")
        self.get_logger().info(f"   Update rate: {self.update_rate} Hz")
        self.get_logger().info(f"   Z height: {self.z_height}m")
        self.get_logger().info(f"   Publishing to: /pointcloud")
        
        if self.enable_accumulation:
            self.get_logger().info(f"   Dense mapping enabled:")
            self.get_logger().info(f"     Accumulation time: {self.accumulation_time}s")
            self.get_logger().info(f"     Voxel size: {self.voxel_size}m")
            self.get_logger().info(f"     Max points: {self.max_points}")
            self.get_logger().info(f"     Publishing to: /dense_map")
        
        self.get_logger().info(f"   Color mapping:")
        self.get_logger().info(f"     Mode: {self.color_mode}")
        self.get_logger().info(f"     Scheme: {self.color_scheme}")
        if self.color_mode == 'height':
            self.get_logger().info(f"     Height range: {self.min_height}m to {self.max_height}m")
    
    def scan_callback(self, msg: LaserScan):
        """Store latest scan data and accumulate for dense mapping"""
        self.current_scan = msg
        
        # Task 3.2: Accumulate scans for dense mapping
        if self.enable_accumulation:
            self.accumulate_scan(msg)
    
    def pose_callback(self, msg: PoseStamped):
        """Store latest pose data"""
        self.current_pose = msg
    
    def publish_pointcloud(self):
        """Convert LaserScan to PointCloud2 and publish"""
        if self.current_scan is None:
            return
        
        try:
            # Convert scan to pointcloud
            pointcloud = self.laserscan_to_pointcloud2(self.current_scan)
            
            # Publish
            self.pointcloud_pub.publish(pointcloud)
            
            # Update timing
            current_time = time.time()
            actual_rate = 1.0 / (current_time - self.last_publish_time) if self.last_publish_time else 0
            self.last_publish_time = current_time
            
            # Log occasionally
            if int(current_time) % 5 == 0:  # Every 5 seconds
                point_count = len(self.current_scan.ranges)
                self.get_logger().debug(
                    f"Published pointcloud: {point_count} points at {actual_rate:.1f} Hz")
                
        except Exception as e:
            self.get_logger().error(f"Error publishing pointcloud: {e}")
    
    def laserscan_to_pointcloud2(self, scan: LaserScan) -> PointCloud2:
        """
        Convert LaserScan message to PointCloud2
        
        Args:
            scan: LaserScan message
            
        Returns:
            PointCloud2 message with XYZ and RGB fields
        """
        # Extract scan parameters
        angle_min = scan.angle_min
        angle_increment = scan.angle_increment
        ranges = scan.ranges
        intensities = scan.intensities if scan.intensities else [1.0] * len(ranges)
        
        # Convert to 3D points
        points = []
        for i, (r, intensity) in enumerate(zip(ranges, intensities)):
            # Skip invalid readings
            if r < scan.range_min or r > scan.range_max:
                continue
            
            # Calculate angle
            angle = angle_min + i * angle_increment
            
            # Convert polar to Cartesian (in robot frame)
            x = r * np.cos(angle)
            y = r * np.sin(angle)
            z = self.z_height  # Fixed height for 2D scan
            
            # Task 3.3: Apply color mapping based on mode
            rgb = self.get_point_color(x, y, z, intensity)
            
            points.append([x, y, z, rgb])
        
        # Create PointCloud2 message
        pointcloud = self.create_pointcloud2(points, scan.header)
        
        return pointcloud
    
    def create_pointcloud2(self, points: List, header) -> PointCloud2:
        """
        Create PointCloud2 message from points
        
        Args:
            points: List of [x, y, z, rgb] points
            header: Header for the pointcloud
            
        Returns:
            PointCloud2 message
        """
        # Define fields
        fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
            PointField(name='rgb', offset=12, datatype=PointField.UINT32, count=1),
        ]
        
        # Create PointCloud2 message
        pointcloud = PointCloud2()
        pointcloud.header = header
        pointcloud.header.frame_id = 'base_link'  # Points in robot frame
        pointcloud.height = 1
        pointcloud.width = len(points)
        pointcloud.is_bigendian = False
        pointcloud.point_step = 16  # 4 floats * 4 bytes
        pointcloud.row_step = pointcloud.point_step * pointcloud.width
        pointcloud.is_dense = True
        pointcloud.fields = fields
        
        # Pack point data
        buffer = []
        for point in points:
            buffer.append(struct.pack('fffi', point[0], point[1], point[2], point[3]))
        
        pointcloud.data = b''.join(buffer)
        
        return pointcloud

    def accumulate_scan(self, scan: LaserScan):
        """
        Accumulate scan in map frame for dense mapping
        
        Args:
            scan: LaserScan message to accumulate
        """
        try:
            # Transform scan to map frame
            points_in_map = self.transform_scan_to_map(scan)
            
            if points_in_map:
                # Store with timestamp
                current_time = time.time()
                self.accumulated_scans.append((current_time, points_in_map))
                
                # Add to voxel grid
                self.add_to_voxel_grid(points_in_map)
                
                # Log occasionally
                if len(self.accumulated_scans) % 10 == 0:
                    self.get_logger().debug(
                        f"Accumulated {len(self.accumulated_scans)} scans, "
                        f"voxel grid: {len(self.voxel_grid)} points")
                    
        except Exception as e:
            self.get_logger().debug(f"Error accumulating scan: {e}")
    
    def transform_scan_to_map(self, scan: LaserScan) -> List[Tuple[float, float, float, int]]:
        """
        Transform LaserScan points to map frame using TF2
        
        Args:
            scan: LaserScan message
            
        Returns:
            List of (x, y, z, rgb) points in map frame
        """
        try:
            # Get transform from laser frame to map frame
            transform = self.tf_buffer.lookup_transform(
                'map',
                scan.header.frame_id,
                scan.header.stamp,
                timeout=rclpy.duration.Duration(seconds=0.1)
            )
            
            # Extract scan parameters
            angle_min = scan.angle_min
            angle_increment = scan.angle_increment
            ranges = scan.ranges
            intensities = scan.intensities if scan.intensities else [1.0] * len(ranges)
            
            # Convert to points in laser frame, then transform to map frame
            points_in_map = []
            for i, (r, intensity) in enumerate(zip(ranges, intensities)):
                # Skip invalid readings
                if r < scan.range_min or r > scan.range_max:
                    continue
                
                # Calculate angle
                angle = angle_min + i * angle_increment
                
                # Convert polar to Cartesian (in laser frame)
                x_laser = r * np.cos(angle)
                y_laser = r * np.sin(angle)
                z_laser = 0.0  # 2D scan at laser height
                
                # Transform to map frame
                x_map = (transform.transform.translation.x + 
                        x_laser * (1 - 2 * (transform.transform.rotation.y**2 + transform.transform.rotation.z**2)) +
                        y_laser * 2 * (transform.transform.rotation.x * transform.transform.rotation.y - 
                                     transform.transform.rotation.w * transform.transform.rotation.z))
                
                y_map = (transform.transform.translation.y +
                        x_laser * 2 * (transform.transform.rotation.x * transform.transform.rotation.y + 
                                     transform.transform.rotation.w * transform.transform.rotation.z) +
                        y_laser * (1 - 2 * (transform.transform.rotation.x**2 + transform.transform.rotation.z**2)))
                
                z_map = transform.transform.translation.z + z_laser
                
                # Color based on intensity
                color_value = int(intensity * 255)
                rgb = struct.unpack('I', struct.pack('BBBB', color_value, color_value, color_value, 255))[0]
                
                points_in_map.append((x_map, y_map, z_map, rgb))
            
            return points_in_map
            
        except TransformException as e:
            self.get_logger().debug(f"Transform failed: {e}")
            return []
    
    def add_to_voxel_grid(self, points: List[Tuple[float, float, float, int]]):
        """
        Add points to voxel grid for downsampling
        
        Args:
            points: List of (x, y, z, rgb) points
        """
        for point in points:
            # Calculate voxel key
            voxel_key = self.get_voxel_key(point[0], point[1], point[2])
            
            # Store point (overwrites if voxel already occupied)
            self.voxel_grid[voxel_key] = point
            
            # Limit total points
            if len(self.voxel_grid) > self.max_points:
                # Remove oldest voxel (simple FIFO)
                self.voxel_grid.pop(next(iter(self.voxel_grid)))
    
    def get_voxel_key(self, x: float, y: float, z: float) -> Tuple[int, int, int]:
        """
        Calculate voxel grid key for a point
        
        Args:
            x, y, z: Point coordinates
            
        Returns:
            Voxel key (ix, iy, iz)
        """
        ix = int(np.floor(x / self.voxel_size))
        iy = int(np.floor(y / self.voxel_size))
        iz = int(np.floor(z / self.voxel_size))
        return (ix, iy, iz)
    
    def cleanup_old_scans(self):
        """Remove scans older than accumulation_time"""
        current_time = time.time()
        cutoff_time = current_time - self.accumulation_time
        
        # Remove old scans
        while self.accumulated_scans and self.accumulated_scans[0][0] < cutoff_time:
            self.accumulated_scans.popleft()
        
        # Rebuild voxel grid from remaining scans
        if len(self.accumulated_scans) < len(self.voxel_grid) / 2:
            # Significant cleanup, rebuild voxel grid
            self.rebuild_voxel_grid()
    
    def rebuild_voxel_grid(self):
        """Rebuild voxel grid from accumulated scans"""
        self.voxel_grid.clear()
        
        for timestamp, points in self.accumulated_scans:
            self.add_to_voxel_grid(points)
        
        self.get_logger().debug(f"Rebuilt voxel grid: {len(self.voxel_grid)} points")
    
    def publish_pointcloud(self):
        """Convert LaserScan to PointCloud2 and publish both real-time and dense map"""
        # Publish real-time pointcloud
        if self.current_scan is not None:
            try:
                # Convert scan to pointcloud
                pointcloud = self.laserscan_to_pointcloud2(self.current_scan)
                
                # Publish
                self.pointcloud_pub.publish(pointcloud)
                
                # Update timing
                current_time = time.time()
                actual_rate = 1.0 / (current_time - self.last_publish_time) if self.last_publish_time else 0
                self.last_publish_time = current_time
                
                # Log occasionally
                if int(current_time) % 5 == 0:  # Every 5 seconds
                    point_count = len(self.current_scan.ranges)
                    self.get_logger().debug(
                        f"Published pointcloud: {point_count} points at {actual_rate:.1f} Hz")
                    
            except Exception as e:
                self.get_logger().error(f"Error publishing pointcloud: {e}")
        
        # Publish dense map
        if self.enable_accumulation and self.voxel_grid:
            try:
                dense_map = self.create_dense_map()
                self.dense_map_pub.publish(dense_map)
                
            except Exception as e:
                self.get_logger().error(f"Error publishing dense map: {e}")
    
    def create_dense_map(self) -> PointCloud2:
        """
        Create dense map PointCloud2 from voxel grid
        
        Returns:
            PointCloud2 message with accumulated points
        """
        # Convert voxel grid to point list
        points = list(self.voxel_grid.values())
        
        # Create header
        from std_msgs.msg import Header
        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = 'map'
        
        # Create PointCloud2
        pointcloud = self.create_pointcloud2(points, header)
        pointcloud.header.frame_id = 'map'  # Ensure map frame
        
        return pointcloud

def main(args=None):
    rclpy.init(args=args)
    node = PointCloudProcessor()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

    def get_point_color(self, x: float, y: float, z: float, intensity: float) -> int:
        """
        Get RGB color for a point based on color mode
        
        Args:
            x, y, z: Point coordinates
            intensity: Point intensity value
            
        Returns:
            RGB color as packed integer
        """
        if self.color_mode == 'height':
            return self.height_to_color(z)
        elif self.color_mode == 'intensity':
            return self.intensity_to_color(intensity)
        else:  # 'fixed' or default
            # Default gray color
            return struct.unpack('I', struct.pack('BBBB', 128, 128, 128, 255))[0]
    
    def height_to_color(self, z: float) -> int:
        """
        Convert height to RGB color using rainbow gradient
        
        Args:
            z: Height value
            
        Returns:
            RGB color as packed integer
        """
        # Normalize height to 0-1 range
        normalized = (z - self.min_height) / (self.max_height - self.min_height)
        normalized = max(0.0, min(1.0, normalized))  # Clamp to [0, 1]
        
        # Apply color scheme
        if self.color_scheme == 'rainbow':
            r, g, b = self.rainbow_gradient(normalized)
        elif self.color_scheme == 'jet':
            r, g, b = self.jet_gradient(normalized)
        elif self.color_scheme == 'hot':
            r, g, b = self.hot_gradient(normalized)
        elif self.color_scheme == 'cool':
            r, g, b = self.cool_gradient(normalized)
        else:
            r, g, b = self.rainbow_gradient(normalized)
        
        # Pack RGB into integer
        return struct.unpack('I', struct.pack('BBBB', int(r), int(g), int(b), 255))[0]
    
    def rainbow_gradient(self, value: float) -> Tuple[int, int, int]:
        """
        Rainbow color gradient: Red (low) -> Violet (high)
        
        Args:
            value: Normalized value [0, 1]
            
        Returns:
            (r, g, b) tuple with values [0, 255]
        """
        # Rainbow: Red -> Orange -> Yellow -> Green -> Blue -> Indigo -> Violet
        if value < 0.17:  # Red to Orange
            t = value / 0.17
            return (255, int(165 * t), 0)
        elif value < 0.33:  # Orange to Yellow
            t = (value - 0.17) / 0.16
            return (255, int(165 + 90 * t), 0)
        elif value < 0.5:  # Yellow to Green
            t = (value - 0.33) / 0.17
            return (int(255 * (1 - t)), 255, 0)
        elif value < 0.67:  # Green to Blue
            t = (value - 0.5) / 0.17
            return (0, int(255 * (1 - t)), int(255 * t))
        elif value < 0.83:  # Blue to Indigo
            t = (value - 0.67) / 0.16
            return (int(75 * t), 0, 255)
        else:  # Indigo to Violet
            t = (value - 0.83) / 0.17
            return (int(75 + 113 * t), 0, int(255 - 17 * t))
    
    def jet_gradient(self, value: float) -> Tuple[int, int, int]:
        """
        Jet color gradient (MATLAB-style)
        
        Args:
            value: Normalized value [0, 1]
            
        Returns:
            (r, g, b) tuple with values [0, 255]
        """
        if value < 0.25:
            r = 0
            g = 0
            b = int(255 * (0.5 + value * 2))
        elif value < 0.5:
            r = 0
            g = int(255 * ((value - 0.25) * 4))
            b = 255
        elif value < 0.75:
            r = int(255 * ((value - 0.5) * 4))
            g = 255
            b = int(255 * (1 - (value - 0.5) * 4))
        else:
            r = 255
            g = int(255 * (1 - (value - 0.75) * 4))
            b = 0
        
        return (r, g, b)
    
    def hot_gradient(self, value: float) -> Tuple[int, int, int]:
        """
        Hot color gradient (black -> red -> yellow -> white)
        
        Args:
            value: Normalized value [0, 1]
            
        Returns:
            (r, g, b) tuple with values [0, 255]
        """
        if value < 0.33:
            r = int(255 * (value / 0.33))
            g = 0
            b = 0
        elif value < 0.67:
            r = 255
            g = int(255 * ((value - 0.33) / 0.34))
            b = 0
        else:
            r = 255
            g = 255
            b = int(255 * ((value - 0.67) / 0.33))
        
        return (r, g, b)
    
    def cool_gradient(self, value: float) -> Tuple[int, int, int]:
        """
        Cool color gradient (cyan -> magenta)
        
        Args:
            value: Normalized value [0, 1]
            
        Returns:
            (r, g, b) tuple with values [0, 255]
        """
        r = int(255 * value)
        g = int(255 * (1 - value))
        b = 255
        
        return (r, g, b)
    
    def intensity_to_color(self, intensity: float) -> int:
        """
        Convert intensity to grayscale color
        
        Args:
            intensity: Intensity value [0, 1]
            
        Returns:
            RGB color as packed integer
        """
        color_value = int(intensity * 255)
        return struct.unpack('I', struct.pack('BBBB', color_value, color_value, color_value, 255))[0]
