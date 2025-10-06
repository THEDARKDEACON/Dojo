#!/usr/bin/env python3
"""
Map Display Diagnostic Node
Monitors map topic and provides diagnostic information for RViz display issues
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from nav_msgs.msg import OccupancyGrid
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from std_msgs.msg import Header
import time

class MapDiagnosticNode(Node):
    def __init__(self):
        super().__init__('map_diagnostic_node')
        
        # Parameters
        self.declare_parameter('map_topic', '/map')
        self.declare_parameter('diagnostic_period', 2.0)
        
        self.map_topic = self.get_parameter('map_topic').get_parameter_value().string_value
        self.diagnostic_period = self.get_parameter('diagnostic_period').get_parameter_value().double_value
        
        # QoS profile for map topic (should match SLAM toolbox)
        map_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )
        
        # Subscribers
        self.map_subscriber = self.create_subscription(
            OccupancyGrid,
            self.map_topic,
            self.map_callback,
            map_qos
        )
        
        # Publishers
        self.diagnostic_publisher = self.create_publisher(
            DiagnosticArray,
            '/diagnostics',
            10
        )
        
        # State tracking
        self.last_map_time = None
        self.map_received = False
        self.map_size = (0, 0)
        self.map_resolution = 0.0
        self.map_frame_id = ""
        self.occupied_cells = 0
        self.free_cells = 0
        
        # Timer for periodic diagnostics
        self.diagnostic_timer = self.create_timer(
            self.diagnostic_period,
            self.publish_diagnostics
        )
        
        self.get_logger().info(f'Map diagnostic node started, monitoring {self.map_topic}')
    
    def map_callback(self, msg):
        """Handle incoming map messages."""
        self.last_map_time = time.time()
        self.map_received = True
        self.map_size = (msg.info.width, msg.info.height)
        self.map_resolution = msg.info.resolution
        self.map_frame_id = msg.header.frame_id
        
        # Count occupied and free cells
        self.occupied_cells = sum(1 for cell in msg.data if cell > 50)
        self.free_cells = sum(1 for cell in msg.data if 0 <= cell <= 50)
        
        self.get_logger().debug(
            f'Map received: {self.map_size[0]}x{self.map_size[1]}, '
            f'resolution: {self.map_resolution:.3f}, '
            f'frame: {self.map_frame_id}'
        )
    
    def publish_diagnostics(self):
        """Publish diagnostic information about map status."""
        diagnostic_array = DiagnosticArray()
        diagnostic_array.header = Header()
        diagnostic_array.header.stamp = self.get_clock().now().to_msg()
        
        # Map availability diagnostic
        map_status = DiagnosticStatus()
        map_status.name = "Map Display Status"
        map_status.hardware_id = "map_visualization"
        
        current_time = time.time()
        
        if not self.map_received:
            map_status.level = DiagnosticStatus.ERROR
            map_status.message = f"No map data received on {self.map_topic}"
            map_status.values = [
                KeyValue(key="topic", value=self.map_topic),
                KeyValue(key="status", value="no_data"),
                KeyValue(key="suggestion", value="Check if SLAM is running and publishing to /map")
            ]
        elif self.last_map_time and (current_time - self.last_map_time) > 10.0:
            map_status.level = DiagnosticStatus.WARN
            map_status.message = f"Map data is stale (last update: {current_time - self.last_map_time:.1f}s ago)"
            map_status.values = [
                KeyValue(key="topic", value=self.map_topic),
                KeyValue(key="status", value="stale_data"),
                KeyValue(key="last_update", value=f"{current_time - self.last_map_time:.1f}s ago"),
                KeyValue(key="suggestion", value="Check SLAM node status")
            ]
        else:
            map_status.level = DiagnosticStatus.OK
            map_status.message = "Map data is being received and updated"
            map_status.values = [
                KeyValue(key="topic", value=self.map_topic),
                KeyValue(key="status", value="active"),
                KeyValue(key="map_size", value=f"{self.map_size[0]}x{self.map_size[1]}"),
                KeyValue(key="resolution", value=f"{self.map_resolution:.3f}m/cell"),
                KeyValue(key="frame_id", value=self.map_frame_id),
                KeyValue(key="occupied_cells", value=str(self.occupied_cells)),
                KeyValue(key="free_cells", value=str(self.free_cells))
            ]
        
        # RViz configuration diagnostic
        rviz_status = DiagnosticStatus()
        rviz_status.name = "RViz Map Configuration"
        rviz_status.hardware_id = "rviz_display"
        
        if self.map_received:
            if self.map_frame_id == "map":
                rviz_status.level = DiagnosticStatus.OK
                rviz_status.message = "Map frame configuration is correct"
                rviz_status.values = [
                    KeyValue(key="fixed_frame", value="map"),
                    KeyValue(key="map_frame", value=self.map_frame_id),
                    KeyValue(key="status", value="configured_correctly")
                ]
            else:
                rviz_status.level = DiagnosticStatus.WARN
                rviz_status.message = f"Map frame is '{self.map_frame_id}', RViz fixed frame should match"
                rviz_status.values = [
                    KeyValue(key="expected_fixed_frame", value=self.map_frame_id),
                    KeyValue(key="map_frame", value=self.map_frame_id),
                    KeyValue(key="status", value="frame_mismatch"),
                    KeyValue(key="suggestion", value="Set RViz Fixed Frame to match map frame")
                ]
        else:
            rviz_status.level = DiagnosticStatus.ERROR
            rviz_status.message = "Cannot validate RViz configuration without map data"
            rviz_status.values = [
                KeyValue(key="status", value="no_map_data"),
                KeyValue(key="suggestion", value="Start SLAM to generate map data")
            ]
        
        diagnostic_array.status = [map_status, rviz_status]
        self.diagnostic_publisher.publish(diagnostic_array)

def main(args=None):
    rclpy.init(args=args)
    node = MapDiagnosticNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()