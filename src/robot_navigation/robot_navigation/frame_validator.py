#!/usr/bin/env python3
"""
Coordinate Frame Validator Node
Validates coordinate frame setup and reports configuration issues for map visualization
"""

import rclpy
from rclpy.node import Node
from tf2_ros import TransformListener, Buffer, LookupException, ConnectivityException, ExtrapolationException
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from std_msgs.msg import Header
import time

class FrameValidator(Node):
    def __init__(self):
        super().__init__('frame_validator')
        
        # Parameters
        self.declare_parameter('diagnostic_period', 5.0)
        self.declare_parameter('frame_timeout', 1.0)
        
        self.diagnostic_period = self.get_parameter('diagnostic_period').get_parameter_value().double_value
        self.frame_timeout = self.get_parameter('frame_timeout').get_parameter_value().double_value
        
        # TF2 setup
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        # Publishers
        self.diagnostic_publisher = self.create_publisher(
            DiagnosticArray,
            '/diagnostics',
            10
        )
        
        # Required frames for proper map visualization
        self.required_frames = ['map', 'odom', 'base_link']
        self.required_transforms = [
            ('map', 'odom'),
            ('odom', 'base_link'),
            ('map', 'base_link')
        ]
        
        # Timer for periodic validation
        self.validation_timer = self.create_timer(
            self.diagnostic_period,
            self.validate_frames
        )
        
        self.get_logger().info('Frame validator started')
    
    def validate_frames(self):
        """Validate coordinate frames and publish diagnostic information."""
        diagnostic_array = DiagnosticArray()
        diagnostic_array.header = Header()
        diagnostic_array.header.stamp = self.get_clock().now().to_msg()
        
        # Frame existence validation
        frame_status = self.validate_frame_existence()
        diagnostic_array.status.append(frame_status)
        
        # Transform chain validation
        transform_status = self.validate_transform_chains()
        diagnostic_array.status.append(transform_status)
        
        # RViz configuration validation
        rviz_status = self.validate_rviz_configuration()
        diagnostic_array.status.append(rviz_status)
        
        self.diagnostic_publisher.publish(diagnostic_array)
    
    def validate_frame_existence(self):
        """Validate that all required frames exist."""
        status = DiagnosticStatus()
        status.name = "Coordinate Frame Existence"
        status.hardware_id = "tf2_frames"
        
        missing_frames = []
        existing_frames = []
        
        for frame in self.required_frames:
            try:
                # Check if frame exists by looking up identity transform
                self.tf_buffer.lookup_transform(
                    frame,
                    frame,
                    rclpy.time.Time(),
                    timeout=rclpy.duration.Duration(seconds=self.frame_timeout)
                )
                existing_frames.append(frame)
            except (LookupException, ConnectivityException, ExtrapolationException):
                missing_frames.append(frame)
        
        if not missing_frames:
            status.level = DiagnosticStatus.OK
            status.message = "All required coordinate frames are available"
            status.values = [
                KeyValue(key="status", value="all_frames_available"),
                KeyValue(key="existing_frames", value=", ".join(existing_frames))
            ]
        else:
            status.level = DiagnosticStatus.ERROR
            status.message = f"Missing required coordinate frames: {', '.join(missing_frames)}"
            status.values = [
                KeyValue(key="status", value="missing_frames"),
                KeyValue(key="missing_frames", value=", ".join(missing_frames)),
                KeyValue(key="existing_frames", value=", ".join(existing_frames)),
                KeyValue(key="suggestion", value="Check robot_state_publisher and SLAM node status")
            ]
        
        return status
    
    def validate_transform_chains(self):
        """Validate that required transform chains are working."""
        status = DiagnosticStatus()
        status.name = "Transform Chain Validation"
        status.hardware_id = "tf2_transforms"
        
        broken_transforms = []
        working_transforms = []
        
        for parent, child in self.required_transforms:
            try:
                transform = self.tf_buffer.lookup_transform(
                    parent,
                    child,
                    rclpy.time.Time(),
                    timeout=rclpy.duration.Duration(seconds=self.frame_timeout)
                )
                working_transforms.append(f"{parent}->{child}")
                
                # Log transform details for debugging
                self.get_logger().debug(
                    f"Transform {parent}->{child}: "
                    f"x={transform.transform.translation.x:.3f}, "
                    f"y={transform.transform.translation.y:.3f}, "
                    f"z={transform.transform.translation.z:.3f}"
                )
                
            except (LookupException, ConnectivityException, ExtrapolationException) as e:
                broken_transforms.append(f"{parent}->{child}")
                self.get_logger().debug(f"Transform {parent}->{child} failed: {e}")
        
        if not broken_transforms:
            status.level = DiagnosticStatus.OK
            status.message = "All required transform chains are working"
            status.values = [
                KeyValue(key="status", value="all_transforms_working"),
                KeyValue(key="working_transforms", value=", ".join(working_transforms))
            ]
        else:
            status.level = DiagnosticStatus.ERROR
            status.message = f"Broken transform chains: {', '.join(broken_transforms)}"
            status.values = [
                KeyValue(key="status", value="broken_transforms"),
                KeyValue(key="broken_transforms", value=", ".join(broken_transforms)),
                KeyValue(key="working_transforms", value=", ".join(working_transforms)),
                KeyValue(key="suggestion", value="Check SLAM node and robot_state_publisher configuration")
            ]
        
        return status
    
    def validate_rviz_configuration(self):
        """Validate RViz configuration for proper map display."""
        status = DiagnosticStatus()
        status.name = "RViz Configuration Validation"
        status.hardware_id = "rviz_config"
        
        # Check if map frame is available (required for RViz Fixed Frame)
        try:
            self.tf_buffer.lookup_transform(
                'map',
                'map',
                rclpy.time.Time(),
                timeout=rclpy.duration.Duration(seconds=self.frame_timeout)
            )
            
            status.level = DiagnosticStatus.OK
            status.message = "Map frame available for RViz Fixed Frame setting"
            status.values = [
                KeyValue(key="status", value="map_frame_available"),
                KeyValue(key="fixed_frame_recommendation", value="map"),
                KeyValue(key="configuration", value="Set RViz Fixed Frame to 'map'")
            ]
            
        except (LookupException, ConnectivityException, ExtrapolationException):
            # Check if odom frame is available as fallback
            try:
                self.tf_buffer.lookup_transform(
                    'odom',
                    'odom',
                    rclpy.time.Time(),
                    timeout=rclpy.duration.Duration(seconds=self.frame_timeout)
                )
                
                status.level = DiagnosticStatus.WARN
                status.message = "Map frame not available, use odom frame as fallback"
                status.values = [
                    KeyValue(key="status", value="map_frame_unavailable"),
                    KeyValue(key="fixed_frame_recommendation", value="odom"),
                    KeyValue(key="configuration", value="Set RViz Fixed Frame to 'odom' temporarily"),
                    KeyValue(key="suggestion", value="Start SLAM to make map frame available")
                ]
                
            except (LookupException, ConnectivityException, ExtrapolationException):
                status.level = DiagnosticStatus.ERROR
                status.message = "Neither map nor odom frames available for RViz"
                status.values = [
                    KeyValue(key="status", value="no_suitable_frame"),
                    KeyValue(key="suggestion", value="Check robot_state_publisher and odometry configuration")
                ]
        
        return status

def main(args=None):
    rclpy.init(args=args)
    node = FrameValidator()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()