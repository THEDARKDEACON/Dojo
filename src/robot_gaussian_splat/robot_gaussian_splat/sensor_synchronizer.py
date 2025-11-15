#!/usr/bin/env python3
"""
SensorSynchronizer Component for Gaussian Splatting Reconstruction

This module provides time synchronization between camera and LiDAR sensor data
using ROS2 message_filters for temporal alignment.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, PointCloud2, CameraInfo
import message_filters
from typing import Callable, Optional
import numpy as np


class SensorSynchronizer:
    """
    Synchronizes camera and LiDAR data streams with temporal alignment.
    
    Uses message_filters.ApproximateTimeSynchronizer to align sensor data
    within a configurable time tolerance.
    """
    
    def __init__(self, node: Node, sync_tolerance: float = 0.05):
        """
        Initialize the SensorSynchronizer.
        
        Args:
            node: ROS2 node instance for creating subscribers
            sync_tolerance: Maximum time difference (in seconds) for synchronization
        """
        self.node = node
        self.sync_tolerance = sync_tolerance
        self.synchronizer: Optional[message_filters.ApproximateTimeSynchronizer] = None
        self.callback_function: Optional[Callable] = None
        
        # Subscribers (will be created in setup_subscribers)
        self.image_sub: Optional[message_filters.Subscriber] = None
        self.pointcloud_sub: Optional[message_filters.Subscriber] = None
        self.camera_info_sub: Optional[message_filters.Subscriber] = None
        
        # Statistics tracking
        self.sync_success_count = 0
        self.sync_failure_count = 0
        
        self.node.get_logger().info(
            f"SensorSynchronizer initialized with tolerance: {sync_tolerance}s"
        )
    
    def setup_subscribers(
        self, 
        camera_topic: str, 
        camera_info_topic: str,
        pointcloud_topic: str,
        queue_size: int = 10
    ):
        """
        Create subscribers for camera and pointcloud topics with synchronization.
        
        Args:
            camera_topic: Topic name for camera images
            camera_info_topic: Topic name for camera calibration info
            pointcloud_topic: Topic name for LiDAR point clouds
            queue_size: Size of message queue for synchronization
        """
        try:
            # Create message_filters subscribers
            self.image_sub = message_filters.Subscriber(
                self.node,
                Image,
                camera_topic
            )
            
            self.camera_info_sub = message_filters.Subscriber(
                self.node,
                CameraInfo,
                camera_info_topic
            )
            
            self.pointcloud_sub = message_filters.Subscriber(
                self.node,
                PointCloud2,
                pointcloud_topic
            )
            
            # Create ApproximateTimeSynchronizer
            # Slop is the tolerance in seconds for message timestamps
            self.synchronizer = message_filters.ApproximateTimeSynchronizer(
                [self.image_sub, self.camera_info_sub, self.pointcloud_sub],
                queue_size=queue_size,
                slop=self.sync_tolerance
            )
            
            # Register the internal callback wrapper
            self.synchronizer.registerCallback(self._synchronized_callback_wrapper)
            
            self.node.get_logger().info(
                f"Subscribers set up for topics:\n"
                f"  Camera: {camera_topic}\n"
                f"  Camera Info: {camera_info_topic}\n"
                f"  PointCloud: {pointcloud_topic}\n"
                f"  Queue size: {queue_size}, Slop: {self.sync_tolerance}s"
            )
            
        except Exception as e:
            self.node.get_logger().error(
                f"Failed to set up subscribers: {str(e)}"
            )
            raise
    
    def register_callback(self, callback_function: Callable):
        """
        Register a callback function to be called with synchronized data.
        
        Args:
            callback_function: Function to call with (image_msg, camera_info_msg, pointcloud_msg)
        """
        self.callback_function = callback_function
        self.node.get_logger().info("Synchronized callback registered")
    
    def _synchronized_callback_wrapper(
        self, 
        image_msg: Image, 
        camera_info_msg: CameraInfo,
        pointcloud_msg: PointCloud2
    ):
        """
        Internal wrapper for synchronized callback with validation.
        
        Args:
            image_msg: Synchronized camera image message
            camera_info_msg: Synchronized camera info message
            pointcloud_msg: Synchronized point cloud message
        """
        # Validate data before passing to user callback
        if self.validate_data(image_msg, pointcloud_msg):
            self.sync_success_count += 1
            
            # Call the registered callback if it exists
            if self.callback_function is not None:
                try:
                    self.callback_function(image_msg, camera_info_msg, pointcloud_msg)
                except Exception as e:
                    self.node.get_logger().error(
                        f"Error in synchronized callback: {str(e)}"
                    )
        else:
            self.sync_failure_count += 1
            
            # Log statistics periodically
            if (self.sync_success_count + self.sync_failure_count) % 100 == 0:
                total = self.sync_success_count + self.sync_failure_count
                success_rate = (self.sync_success_count / total) * 100
                self.node.get_logger().info(
                    f"Sync statistics: {self.sync_success_count}/{total} "
                    f"({success_rate:.1f}% success rate)"
                )
    
    def validate_data(self, image_msg: Image, pointcloud_msg: PointCloud2) -> bool:
        """
        Validate image and pointcloud data quality.
        
        Checks:
        - Image encoding is valid (RGB8, BGR8)
        - Point cloud data doesn't contain NaN or Inf values
        - Messages are not empty
        
        Args:
            image_msg: Camera image message to validate
            pointcloud_msg: Point cloud message to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Validate image encoding
        valid_encodings = ['rgb8', 'bgr8', 'RGB8', 'BGR8']
        if image_msg.encoding not in valid_encodings:
            self.node.get_logger().warning(
                f"Invalid image encoding: {image_msg.encoding}. "
                f"Expected one of {valid_encodings}"
            )
            return False
        
        # Check if image data is not empty
        if len(image_msg.data) == 0:
            self.node.get_logger().warning("Received empty image data")
            return False
        
        # Check if image dimensions are valid
        if image_msg.height == 0 or image_msg.width == 0:
            self.node.get_logger().warning(
                f"Invalid image dimensions: {image_msg.width}x{image_msg.height}"
            )
            return False
        
        # Check if point cloud data is not empty
        if len(pointcloud_msg.data) == 0:
            self.node.get_logger().warning("Received empty point cloud data")
            return False
        
        # Validate point cloud for NaN/Inf values
        # We'll do a quick check by converting a sample of the data
        try:
            # Import here to avoid circular dependencies
            import struct
            
            # Check point cloud fields
            has_xyz = False
            x_offset = y_offset = z_offset = None
            
            for field in pointcloud_msg.fields:
                if field.name == 'x':
                    x_offset = field.offset
                elif field.name == 'y':
                    y_offset = field.offset
                elif field.name == 'z':
                    z_offset = field.offset
            
            has_xyz = (x_offset is not None and y_offset is not None and z_offset is not None)
            
            if not has_xyz:
                self.node.get_logger().warning(
                    "Point cloud missing x, y, or z fields"
                )
                return False
            
            # Sample check: validate first few points for NaN/Inf
            point_step = pointcloud_msg.point_step
            num_points_to_check = min(10, len(pointcloud_msg.data) // point_step)
            
            for i in range(num_points_to_check):
                offset = i * point_step
                
                # Extract x, y, z values
                x = struct.unpack_from('f', pointcloud_msg.data, offset + x_offset)[0]
                y = struct.unpack_from('f', pointcloud_msg.data, offset + y_offset)[0]
                z = struct.unpack_from('f', pointcloud_msg.data, offset + z_offset)[0]
                
                # Check for NaN or Inf
                if not (np.isfinite(x) and np.isfinite(y) and np.isfinite(z)):
                    self.node.get_logger().warning(
                        f"Point cloud contains NaN or Inf values at point {i}: "
                        f"({x}, {y}, {z})"
                    )
                    return False
            
        except Exception as e:
            self.node.get_logger().warning(
                f"Error validating point cloud data: {str(e)}"
            )
            return False
        
        # All validation checks passed
        return True
    
    def get_statistics(self) -> dict:
        """
        Get synchronization statistics.
        
        Returns:
            Dictionary with sync success/failure counts and rate
        """
        total = self.sync_success_count + self.sync_failure_count
        success_rate = (self.sync_success_count / total * 100) if total > 0 else 0.0
        
        return {
            'sync_success_count': self.sync_success_count,
            'sync_failure_count': self.sync_failure_count,
            'total_attempts': total,
            'success_rate_percent': success_rate
        }
