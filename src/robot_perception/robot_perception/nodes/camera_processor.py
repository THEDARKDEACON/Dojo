#!/usr/bin/env python3
"""
Camera Processor Node

This node processes camera images for computer vision tasks including:
- Image preprocessing (resize, undistort, color conversion)
- Color-based object detection
- Integration with object detection models
- Visualization of results
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy
from sensor_msgs.msg import Image, CameraInfo, CompressedImage, PointCloud2, PointField
from cv_bridge import CvBridge, CvBridgeError
import cv2
import numpy as np
from geometry_msgs.msg import Point, Pose, Quaternion, Vector3, TransformStamped, PoseStamped
from visualization_msgs.msg import Marker, MarkerArray
from std_msgs.msg import ColorRGBA, Header
import tf2_ros
from tf2_ros import TransformBroadcaster, Buffer, TransformListener
import tf2_geometry_msgs
import yaml
import os
from ament_index_python.packages import get_package_share_directory
import time
from typing import List, Dict, Tuple, Optional, Union

# Import common utilities
from robot_perception.utils.common import (
    create_marker,
    create_point_cloud,
    transform_pose
)

class CameraProcessor(Node):
    """
    Enhanced camera processor for advanced computer vision tasks.
    
    Features:
    - Supports both raw and compressed image topics
    - Camera calibration and image undistortion
    - Color-based object detection with configurable HSV ranges
    - Integration with deep learning models (YOLO, etc.)
    - Visualization of detections and processing results
    - TF frame publishing for detected objects
    
    Subscribers:
        /camera/image_raw - Raw or compressed camera image
        /camera/camera_info - Camera calibration info
        
    Publishers:
        /perception/processed_image - Processed image with visualizations
        /perception/detection_markers - Visualization markers for detections
        /perception/detections - Detection results as custom message
    """
    
    def __init__(self):
        super().__init__('camera_processor')
        
        # Load parameters from YAML file with defaults
        self.declare_parameters(
            namespace='',
            parameters=[
                ('enabled', True),
                ('camera_topic', '/camera/image_raw'),
                ('camera_info_topic', '/camera/camera_info'),
                ('compressed', True),
                ('queue_size', 10),
                ('resize_width', 640),
                ('resize_height', 480),
                ('publish_processed', True),
                ('processed_topic', '/perception/processed_image'),
                ('debug', False),
                ('debug_window_name', 'Camera Feed'),
                ('base_frame', 'base_footprint'),
                ('camera_frame', 'camera_link'),
                ('color_detection.enabled', True),
                ('color_detection.min_object_size', 100),
                ('color_detection.max_objects', 10),
                # Red color range 1 (HSV)
                ('color_detection.red_lower_1', [0, 100, 100]),
                ('color_detection.red_upper_1', [10, 255, 255]),
                # Red color range 2 (for wrapping around red)
                ('color_detection.red_lower_2', [160, 100, 100]),
                ('color_detection.red_upper_2', [180, 255, 255]),
                # Green color range
                ('color_detection.green_lower', [40, 40, 40]),
                ('color_detection.green_upper', [80, 255, 255]),
                # Blue color range
                ('color_detection.blue_lower', [90, 50, 50]),
                ('color_detection.blue_upper', [130, 255, 255])
            ]
        )
        
        # Get parameters
        self.enabled = self.get_parameter('enabled').value
        self.camera_topic = self.get_parameter('camera_topic').value
        self.camera_info_topic = self.get_parameter('camera_info_topic').value
        self.compressed = self.get_parameter('compressed').value
        self.queue_size = self.get_parameter('queue_size').value
        self.resize_width = self.get_parameter('resize_width').value
        self.resize_height = self.get_parameter('resize_height').value
        self.publish_processed = self.get_parameter('publish_processed').value
        self.processed_topic = self.get_parameter('processed_topic').value
        self.debug = self.get_parameter('debug').value
        self.debug_window_name = self.get_parameter('debug_window_name').value
        self.base_frame = self.get_parameter('base_frame').value
        self.camera_frame = self.get_parameter('camera_frame').value
        
        # Color detection parameters
        self.color_detection_enabled = self.get_parameter('color_detection.enabled').value
        self.min_object_size = self.get_parameter('color_detection.min_object_size').value
        self.max_objects = self.get_parameter('color_detection.max_objects').value
        
        # Color ranges
        self.red_lower_1 = np.array(self.get_parameter('color_detection.red_lower_1').value, dtype=np.uint8)
        self.red_upper_1 = np.array(self.get_parameter('color_detection.red_upper_1').value, dtype=np.uint8)
        self.red_lower_2 = np.array(self.get_parameter('color_detection.red_lower_2').value, dtype=np.uint8)
        self.red_upper_2 = np.array(self.get_parameter('color_detection.red_upper_2').value, dtype=np.uint8)
        self.green_lower = np.array(self.get_parameter('color_detection.green_lower').value, dtype=np.uint8)
        self.green_upper = np.array(self.get_parameter('color_detection.green_upper').value, dtype=np.uint8)
        self.blue_lower = np.array(self.get_parameter('color_detection.blue_lower').value, dtype=np.uint8)
        self.blue_upper = np.array(self.get_parameter('color_detection.blue_upper').value, dtype=np.uint8)
        
        # CV bridge for image conversion
        self.bridge = CvBridge()
        
        # Camera parameters (will be updated from camera_info)
        self.camera_matrix = None
        self.dist_coeffs = None
        self.camera_info_received = False
        
        # TF buffer and broadcaster
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # Set up QoS profile for image transport
        qos_profile = QoSProfile(
            depth=self.queue_size,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE
        )
        
        # Publishers
        self.processed_image_pub = self.create_publisher(
            Image if not self.compressed else CompressedImage,
            self.processed_topic,
            qos_profile=qos_profile
        )
        
        self.marker_pub = self.create_publisher(
            MarkerArray,
            '/perception/detection_markers',
            qos_profile=10
        )
        
        # Subscribers
        if self.compressed:
            self.image_sub = self.create_subscription(
                CompressedImage,
                f"{self.camera_topic}/compressed",
                self.image_callback,
                qos_profile=qos_profile
            )
        else:
            self.image_sub = self.create_subscription(
                Image,
                self.camera_topic,
                self.image_callback,
                qos_profile=qos_profile
            )
        
        self.camera_info_sub = self.create_subscription(
            CameraInfo,
            self.camera_info_topic,
            self.camera_info_callback,
            qos_profile=10
        )
        
        self.get_logger().info('Camera Processor initialized')
        
        # Image processing pipeline
        self.processing_pipeline = []
        
        # Detection results
        self.detections = []
        self.last_frame_time = self.get_clock().now()
        self.frame_count = 0
        self.fps = 0.0
    
    def camera_info_callback(self, msg):
        """Handle camera info messages to get calibration parameters."""
        if not self.camera_info_received:
            self.get_logger().info('Received camera info')
            
        # Extract camera matrix and distortion coefficients
        self.camera_matrix = np.array(msg.k).reshape(3, 3)
        self.dist_coeffs = np.array(msg.d)
        self.camera_info_received = True
    
    def image_callback(self, msg):
        """Process incoming image messages."""
        if not self.enabled or not self.camera_info_received:
            return
        
        try:
            # Convert ROS image to OpenCV format
            if isinstance(msg, CompressedImage):
                cv_image = self.bridge.compressed_imgmsg_to_cv2(msg, 'bgr8')
            else:
                cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            
            # Store original image for visualization
            original_image = cv_image.copy()
            
            # Resize image if needed
            if self.resize_width > 0 and self.resize_height > 0:
                cv_image = cv2.resize(cv_image, (self.resize_width, self.resize_height))
            
            # Undistort image using camera calibration
            if self.camera_matrix is not None and self.dist_coeffs is not None:
                h, w = cv_image.shape[:2]
                new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
                    self.camera_matrix, self.dist_coeffs, (w, h), 1, (w, h)
                )
                cv_image = cv2.undistort(cv_image, self.camera_matrix, self.dist_coeffs, None, new_camera_matrix)
                
                # Crop the image if needed
                x, y, w, h = roi
                if w > 0 and h > 0:
                    cv_image = cv_image[y:y+h, x:x+w]
            
            # Process the image
            processed_image = self.process_image(cv_image)
            
            # Publish processed image
            if self.publish_processed:
                self.publish_processed_image(processed_image, msg.header)
            
            # Calculate FPS
            self.frame_count += 1
            current_time = self.get_clock().now()
            time_diff = (current_time - self.last_frame_time).nanoseconds / 1e9
            
            if time_diff >= 1.0:  # Update FPS every second
                self.fps = self.frame_count / time_diff
                self.frame_count = 0
                self.last_frame_time = current_time
            
            # Debug visualization
            if self.debug:
                debug_image = self.create_debug_image(original_image, processed_image)
                cv2.imshow(self.debug_window_name, debug_image)
                cv2.waitKey(1)
                
        except Exception as e:
            self.get_logger().error(f'Error processing image: {str(e)}')
    
    def process_image(self, image):
        """Process the input image through the processing pipeline."""
        processed = image.copy()
        
        # Apply color detection if enabled
        if self.color_detection_enabled:
            processed, detections = self.detect_colors(processed)
            self.detections = detections
            
            # Publish detection markers
            self.publish_detection_markers(detections, image.shape)
        
        return processed
    
    def detect_colors(self, image):
        """Detect colored objects in the image."""
        # Convert to HSV color space
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Create masks for each color
        masks = {
            'red': self.create_color_mask(hsv, self.red_lower_1, self.red_upper_1, 
                                        self.red_lower_2, self.red_upper_2),
            'green': self.create_color_mask(hsv, self.green_lower, self.green_upper),
            'blue': self.create_color_mask(hsv, self.blue_lower, self.blue_upper)
        }
        
        detections = []
        
        # Process each color mask
        for color, mask in masks.items():
            # Find contours in the mask
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours by size
            filtered_contours = [
                c for c in contours 
                if cv2.contourArea(c) > self.min_object_size
            ]
            
            # Sort by area (largest first) and limit number of detections
            filtered_contours = sorted(
                filtered_contours, 
                key=cv2.contourArea, 
                reverse=True
            )[:self.max_objects]
            
            # Process each contour
            for i, contour in enumerate(filtered_contours):
                # Get bounding box
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate center and radius of the minimum enclosing circle
                ((x_center, y_center), radius) = cv2.minEnclosingCircle(contour)
                
                # Only proceed if the radius meets a minimum size
                if radius > 10:
                    # Draw the circle and rectangle around the object
                    cv2.circle(image, (int(x_center), int(y_center)), int(radius),
                              (0, 255, 255), 2)
                    cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    
                    # Add label
                    label = f"{color} {i+1}"
                    cv2.putText(image, label, (x, y - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    
                    # Add to detections
                    detections.append({
                        'color': color,
                        'position': (x_center, y_center, radius),
                        'bbox': (x, y, w, h),
                        'contour': contour
                    })
        
        return image, detections
    
    def create_color_mask(self, hsv, lower1, upper1, lower2=None, upper2=None):
        """Create a mask for a color range, optionally with two ranges (for red)."""
        # Threshold the HSV image to get only desired colors
        mask1 = cv2.inRange(hsv, lower1, upper1)
        
        # If a second range is provided, combine with the first range
        if lower2 is not None and upper2 is not None:
            mask2 = cv2.inRange(hsv, lower2, upper2)
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            mask = mask1
        
        # Apply morphological operations to remove noise
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        return mask
    
    def publish_processed_image(self, image, header):
        """Publish the processed image."""
        try:
            if self.compressed:
                msg = self.bridge.cv2_to_compressed_imgmsg(image)
            else:
                msg = self.bridge.cv2_to_imgmsg(image, 'bgr8')
            
            msg.header = header
            self.processed_image_pub.publish(msg)
            
        except CvBridgeError as e:
            self.get_logger().error(f'Error converting image: {str(e)}')
    
    def publish_detection_markers(self, detections, image_shape):
        """Publish visualization markers for detections."""
        marker_array = MarkerArray()
        
        for i, detection in enumerate(detections):
            # Create a marker for the detection
            marker = Marker()
            marker.header.frame_id = self.camera_frame
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = 'detections'
            marker.id = i
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            
            # Set marker position (in camera frame, place at fixed depth)
            depth = 1.0  # Fixed depth for visualization
            fx = self.camera_matrix[0, 0] if self.camera_matrix is not None else 500.0
            fy = self.camera_matrix[1, 1] if self.camera_matrix is not None else 500.0
            cx = self.camera_matrix[0, 2] if self.camera_matrix is not None else image_shape[1] / 2
            cy = self.camera_matrix[1, 2] if self.camera_matrix is not None else image_shape[0] / 2
            
            # Convert from image coordinates to 3D (assuming pinhole camera model)
            x_img, y_img, radius = detection['position']
            x = (x_img - cx) * depth / fx
            y = (y_img - cy) * depth / fy
            z = depth
            
            marker.pose.position.x = float(x)
            marker.pose.position.y = float(y)
            marker.pose.position.z = float(z)
            marker.pose.orientation.w = 1.0
            
            # Set marker size based on detection size
            marker.scale.x = marker.scale.y = marker.scale.z = float(radius) * 2 / fx * depth
            
            # Set marker color based on detection color
            if detection['color'] == 'red':
                marker.color.r = 1.0
                marker.color.g = 0.0
                marker.color.b = 0.0
            elif detection['color'] == 'green':
                marker.color.r = 0.0
                marker.color.g = 1.0
                marker.color.b = 0.0
            elif detection['color'] == 'blue':
                marker.color.r = 0.0
                marker.color.g = 0.0
                marker.color.b = 1.0
            else:
                marker.color.r = 1.0
                marker.color.g = 1.0
                marker.color.b = 0.0
            
            marker.color.a = 0.5  # Semi-transparent
            marker.lifetime = rclpy.duration.Duration(seconds=0.1).to_msg()
            
            marker_array.markers.append(marker)
        
        # Publish markers
        self.marker_pub.publish(marker_array)
    
    def create_debug_image(self, original, processed):
        """Create a debug image with original and processed views."""
        # Resize images to same height
        target_height = 480
        scale = target_height / original.shape[0]
        new_width = int(original.shape[1] * scale)
        
        resized_original = cv2.resize(original, (new_width, target_height))
        resized_processed = cv2.resize(processed, (new_width, target_height))
        
        # Add FPS counter
        fps_text = f'FPS: {self.fps:.1f}'
        cv2.putText(resized_processed, fps_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Combine images side by side
        debug_image = np.hstack((resized_original, resized_processed))
        
        return debug_image


def main(args=None):
    rclpy.init(args=args)
    node = CameraProcessor()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
