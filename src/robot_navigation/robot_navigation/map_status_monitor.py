#!/usr/bin/env python3
"""
Map Status Monitor Node
Provides comprehensive error handling and fallback visualization for map display issues
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import PoseStamped, TransformStamped, Point
from visualization_msgs.msg import Marker, MarkerArray
from std_msgs.msg import ColorRGBA, Header
from tf2_ros import TransformListener, Buffer, LookupException, ConnectivityException, ExtrapolationException
import time
import math

class MapStatusMonitor(Node):
    def __init__(self):
        super().__init__('map_status_monitor')
        
        # Parameters
        self.declare_parameter('map_topic', '/map')
        self.declare_parameter('fallback_marker_topic', '/map_fallback_markers')
        self.declare_parameter('robot_pose_topic', '/robot_pose')
        self.declare_parameter('check_interval', 1.0)
        self.declare_parameter('map_timeout', 5.0)
        
        self.map_topic = self.get_parameter('map_topic').get_parameter_value().string_value
        self.fallback_marker_topic = self.get_parameter('fallback_marker_topic').get_parameter_value().string_value
        self.robot_pose_topic = self.get_parameter('robot_pose_topic').get_parameter_value().string_value
        self.check_interval = self.get_parameter('check_interval').get_parameter_value().double_value
        self.map_timeout = self.get_parameter('map_timeout').get_parameter_value().double_value
        
        # QoS profiles
        map_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )
        
        # TF2 setup
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        # Subscribers
        self.map_subscriber = self.create_subscription(
            OccupancyGrid,
            self.map_topic,
            self.map_callback,
            map_qos
        )
        
        # Publishers
        self.fallback_marker_publisher = self.create_publisher(
            MarkerArray,
            self.fallback_marker_topic,
            10
        )
        
        self.robot_pose_publisher = self.create_publisher(
            PoseStamped,
            self.robot_pose_topic,
            10
        )
        
        # State tracking
        self.last_map_time = None
        self.map_available = False
        self.coordinate_frames_valid = False
        self.robot_position = None
        
        # Timer for periodic checks
        self.status_timer = self.create_timer(
            self.check_interval,
            self.check_map_status
        )
        
        self.get_logger().info('Map status monitor started')
    
    def map_callback(self, msg):
        """Handle incoming map messages."""
        self.last_map_time = time.time()
        self.map_available = True
        
        # Validate coordinate frame
        if msg.header.frame_id == "map":
            self.coordinate_frames_valid = True
        else:
            self.get_logger().warn(
                f'Map frame_id is "{msg.header.frame_id}", expected "map". '
                'This may cause RViz display issues.'
            )
            self.coordinate_frames_valid = False
        
        self.get_logger().debug(f'Map received with frame_id: {msg.header.frame_id}')
    
    def check_map_status(self):
        """Periodically check map status and provide fallback visualization."""
        current_time = time.time()
        
        # Check if map data is available and recent
        map_is_stale = (
            self.last_map_time is None or 
            (current_time - self.last_map_time) > self.map_timeout
        )
        
        if map_is_stale or not self.map_available:
            self.provide_fallback_visualization()
        
        # Update robot pose for visualization
        self.update_robot_pose()
        
        # Check coordinate frame validity
        self.validate_coordinate_frames()
    
    def provide_fallback_visualization(self):
        """Provide fallback visualization when map is unavailable."""
        marker_array = MarkerArray()
        
        # Create grid marker as map substitute
        grid_marker = Marker()
        grid_marker.header = Header()
        grid_marker.header.stamp = self.get_clock().now().to_msg()
        grid_marker.header.frame_id = "map"
        grid_marker.ns = "fallback_grid"
        grid_marker.id = 0
        grid_marker.type = Marker.LINE_LIST
        grid_marker.action = Marker.ADD
        grid_marker.scale.x = 0.05  # Line width
        
        # Grid color (light gray)
        grid_marker.color = ColorRGBA()
        grid_marker.color.r = 0.5
        grid_marker.color.g = 0.5
        grid_marker.color.b = 0.5
        grid_marker.color.a = 0.3
        
        # Create grid lines
        grid_size = 20  # 20x20 meter grid
        grid_spacing = 1.0  # 1 meter spacing
        
        # Horizontal lines
        for i in range(int(grid_size / grid_spacing) + 1):
            y = -grid_size/2 + i * grid_spacing
            # Start point
            start_point = Point()
            start_point.x = -grid_size/2
            start_point.y = y
            start_point.z = 0.0
            # End point
            end_point = Point()
            end_point.x = grid_size/2
            end_point.y = y
            end_point.z = 0.0
            
            grid_marker.points.append(start_point)
            grid_marker.points.append(end_point)
        
        # Vertical lines
        for i in range(int(grid_size / grid_spacing) + 1):
            x = -grid_size/2 + i * grid_spacing
            # Start point
            start_point = Point()
            start_point.x = x
            start_point.y = -grid_size/2
            start_point.z = 0.0
            # End point
            end_point = Point()
            end_point.x = x
            end_point.y = grid_size/2
            end_point.z = 0.0
            
            grid_marker.points.append(start_point)
            grid_marker.points.append(end_point)
        
        marker_array.markers.append(grid_marker)
        
        # Create status text marker
        status_marker = Marker()
        status_marker.header = Header()
        status_marker.header.stamp = self.get_clock().now().to_msg()
        status_marker.header.frame_id = "map"
        status_marker.ns = "map_status"
        status_marker.id = 1
        status_marker.type = Marker.TEXT_VIEW_FACING
        status_marker.action = Marker.ADD
        
        # Position text above origin
        status_marker.pose.position.x = 0.0
        status_marker.pose.position.y = 0.0
        status_marker.pose.position.z = 2.0
        status_marker.pose.orientation.w = 1.0
        
        status_marker.scale.z = 0.5  # Text size
        
        # Status text color (red for error)
        status_marker.color = ColorRGBA()
        status_marker.color.r = 1.0
        status_marker.color.g = 0.0
        status_marker.color.b = 0.0
        status_marker.color.a = 1.0
        
        if not self.map_available:
            status_marker.text = "MAP NOT AVAILABLE\nCheck SLAM node status"
        else:
            status_marker.text = "MAP DATA STALE\nSLAM may have stopped"
        
        marker_array.markers.append(status_marker)
        
        # Publish fallback visualization
        self.fallback_marker_publisher.publish(marker_array)
        
        self.get_logger().warn('Publishing fallback visualization - map data unavailable')
    
    def update_robot_pose(self):
        """Update and publish robot pose for visualization."""
        try:
            # Get transform from map to base_link
            transform = self.tf_buffer.lookup_transform(
                'map',
                'base_link',
                rclpy.time.Time(),
                timeout=rclpy.duration.Duration(seconds=1.0)
            )
            
            # Create pose message
            pose_msg = PoseStamped()
            pose_msg.header = Header()
            pose_msg.header.stamp = self.get_clock().now().to_msg()
            pose_msg.header.frame_id = "map"
            
            pose_msg.pose.position.x = transform.transform.translation.x
            pose_msg.pose.position.y = transform.transform.translation.y
            pose_msg.pose.position.z = transform.transform.translation.z
            
            pose_msg.pose.orientation = transform.transform.rotation
            
            self.robot_pose_publisher.publish(pose_msg)
            self.robot_position = (
                transform.transform.translation.x,
                transform.transform.translation.y
            )
            
        except (LookupException, ConnectivityException, ExtrapolationException) as e:
            self.get_logger().debug(f'Could not get robot pose: {e}')
    
    def validate_coordinate_frames(self):
        """Validate that required coordinate frames are available."""
        required_frames = ['map', 'odom', 'base_link']
        
        for frame in required_frames:
            try:
                # Check if frame exists by looking up identity transform
                self.tf_buffer.lookup_transform(
                    frame,
                    frame,
                    rclpy.time.Time(),
                    timeout=rclpy.duration.Duration(seconds=0.1)
                )
            except (LookupException, ConnectivityException, ExtrapolationException):
                self.get_logger().warn(f'Required coordinate frame "{frame}" not available')
                return False
        
        # Check map -> odom -> base_link chain
        try:
            self.tf_buffer.lookup_transform(
                'map',
                'base_link',
                rclpy.time.Time(),
                timeout=rclpy.duration.Duration(seconds=0.1)
            )
            return True
        except (LookupException, ConnectivityException, ExtrapolationException) as e:
            self.get_logger().warn(f'Transform chain map->base_link broken: {e}')
            return False

def main(args=None):
    rclpy.init(args=args)
    node = MapStatusMonitor()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()