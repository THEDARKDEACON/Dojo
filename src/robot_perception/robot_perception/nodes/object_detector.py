#!/usr/bin/env python3
"""
Object Detector Node

Performs real-time object detection using YOLO and OpenCV.
Publishes detections, markers, and detection info.
"""

import os
import cv2
import numpy as np
import json
from typing import List, Dict, Any

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy
from sensor_msgs.msg import Image, CameraInfo
from std_msgs.msg import String
from geometry_msgs.msg import Point
from visualization_msgs.msg import Marker, MarkerArray
from cv_bridge import CvBridge, CvBridgeError
from ament_index_python.packages import get_package_share_directory

class ObjectDetector(Node):
    """Real-time object detection using YOLO and OpenCV."""
    
    def __init__(self):
        super().__init__('object_detector')
        self.bridge = CvBridge()
        
        # Parameters
        self.declare_parameters(namespace='', parameters=[
            ('detection_method', 'yolo'),
            ('yolo.model_path', 'yolov8n.pt'),
            ('yolo.confidence_threshold', 0.5),
            ('debug', False),
            ('publish_images', True),
            ('visualize_in_rviz', True),
            ('camera_frame', 'camera_link')
        ])
        
        # Get parameters
        params = self.get_parameters([
            'detection_method', 'yolo.model_path', 'yolo.confidence_threshold',
            'debug', 'publish_images', 'visualize_in_rviz', 'camera_frame'
        ])
        
        self.detection_method = params[0].value
        self.yolo_model_path = params[1].value
        self.confidence_threshold = params[2].value
        self.debug = params[3].value
        self.publish_images = params[4].value
        self.visualize_in_rviz = params[5].value
        self.camera_frame = params[6].value
        
        # Initialize YOLO model
        self.yolo_model = None
        self._init_yolo()
        
        # Setup QoS profile
        qos = QoSProfile(
            depth=10,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE
        )
        
        # Subscribers
        self.image_sub = self.create_subscription(
            Image, '/camera/image_raw', self.image_callback, qos)
            
        self.camera_info_sub = self.create_subscription(
            CameraInfo, '/camera/camera_info', self.camera_info_callback, 10)
        
        # Publishers
        self.detection_pub = self.create_publisher(
            Image, '/perception/detections', 10)
            
        self.detection_info_pub = self.create_publisher(
            String, '/perception/detection_info', 10)
            
        self.object_count_pub = self.create_publisher(
            Point, '/perception/object_count', 10)
            
        if self.visualize_in_rviz:
            self.marker_pub = self.create_publisher(
                MarkerArray, '/perception/detection_markers', 10)
        
        # Camera parameters
        self.camera_matrix = None
        self.camera_info_received = False
    
    def _init_yolo(self):
        """Initialize YOLO model for object detection."""
        try:
            from ultralytics import YOLO
            
            # Resolve model path
            if not os.path.isabs(self.yolo_model_path):
                pkg_share = get_package_share_directory('robot_perception')
                model_path = os.path.join(pkg_share, 'models', self.yolo_model_path)
            else:
                model_path = self.yolo_model_path
            
            # Load YOLO model
            self.yolo_model = YOLO(model_path)
            self.get_logger().info(f'YOLO model loaded from {model_path}')
            
        except ImportError:
            self.get_logger().error('ultralytics package not found. Install with: pip install ultralytics')
            raise
        except Exception as e:
            self.get_logger().error(f'Failed to load YOLO model: {str(e)}')
            raise
    
    
    
    def camera_info_callback(self, msg):
        """Store camera calibration parameters."""
        if not self.camera_info_received:
            self.get_logger().info('Received camera info')
            self.camera_matrix = np.array(msg.k).reshape(3, 3)
            self.camera_info_received = True
    
    def detect_objects(self, cv_image):
        """Detect objects in the image using YOLO."""
        if self.yolo_model is None:
            return cv_image, []
            
        # Run YOLO inference
        results = self.yolo_model(cv_image, verbose=False)
        
        detections = []
        annotated_image = cv_image.copy()
        
        for result in results:
            boxes = result.boxes.xyxy.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            class_ids = result.boxes.cls.cpu().numpy().astype(int)
            
            for box, conf, class_id in zip(boxes, confs, class_ids):
                if conf < self.confidence_threshold:
                    continue
                    
                # Get box coordinates
                x1, y1, x2, y2 = map(int, box)
                width = x2 - x1
                height = y2 - y1
                
                # Create detection
                detection = {
                    'class_id': int(class_id),
                    'class_name': self.yolo_model.names.get(class_id, f'class_{class_id}'),
                    'confidence': float(conf),
                    'bbox': [x1, y1, width, height],
                    'center': (x1 + width//2, y1 + height//2),
                    'area': width * height
                }
                
                # Estimate 3D position if camera info is available
                if self.camera_info_received and self.camera_matrix is not None:
                    self._estimate_3d_position(detection)
                
                detections.append(detection)
                
                # Draw detection
                if self.publish_images:
                    color = (0, 255, 0)  # Green
                    cv2.rectangle(annotated_image, (x1, y1), (x2, y2), color, 2)
                    label = f"{detection['class_name']} {conf:.2f}"
                    cv2.putText(annotated_image, label, (x1, y1-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return annotated_image, detections
    
    
    
    def _estimate_3d_position(self, detection):
        """Estimate 3D position using camera parameters and bbox size."""
        if not hasattr(self, 'camera_matrix') or 'center' not in detection:
            return
            
        try:
            cx, cy = detection['center']
            fx = self.camera_matrix[0, 0]
            cx_img = self.camera_matrix[0, 2]
            
            # Simple depth estimation based on bbox width
            if detection['bbox'][2] > 0:
                # Object width in meters (approximate for common objects)
                obj_width = 0.2  # Default 20cm
                
                # Calculate distance using pinhole camera model
                distance = (fx * obj_width) / detection['bbox'][2]
                
                # Calculate 3D position
                x = (cx - cx_img) * distance / fx
                y = 0  # Assuming objects are on ground plane
                z = distance
                
                detection['position_3d'] = (float(x), float(y), float(z))
                
        except Exception as e:
            self.get_logger().warn(f'3D estimation failed: {str(e)}', throttle_duration_sec=5.0)
    
    def image_callback(self, msg):
        """Process incoming image messages."""
        try:
            # Convert image to OpenCV format
            cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            
            # Run object detection
            detected_image, detections = self.detect_objects(cv_image)
            
            # Publish results
            if self.publish_images:
                try:
                    img_msg = self.bridge.cv2_to_imgmsg(detected_image, 'bgr8')
                    img_msg.header = msg.header
                    self.detection_pub.publish(img_msg)
                except CvBridgeError as e:
                    self.get_logger().error(f'Image conversion error: {e}')
            
            # Publish detection info
            self.publish_detection_info(detections)
            
        except Exception as e:
            self.get_logger().error(f'Image processing error: {str(e)}')
            
    def _publish_markers(self, detections):
        """Publish detection markers for RViz visualization."""
        if not hasattr(self, 'marker_pub') or not detections:
            return
            
        marker_array = MarkerArray()
        now = self.get_clock().now()
        
        for i, det in enumerate(detections):
            if 'position_3d' not in det:
                continue
                
            # Create sphere marker
            marker = Marker()
            marker.header.frame_id = self.camera_frame
            marker.header.stamp = now.to_msg()
            marker.ns = 'detections'
            marker.id = i
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            
            # Position and appearance
            x, y, z = det['position_3d']
            marker.pose.position.x = x
            marker.pose.position.y = y
            marker.pose.position.z = z
            marker.pose.orientation.w = 1.0
            
            marker.scale.x = marker.scale.y = marker.scale.z = 0.1  # 10cm sphere
            
            # Color based on class
            class_name = det.get('class_name', '').lower()
            if 'person' in class_name:
                marker.color.r, marker.color.g, marker.color.b = 1.0, 0.0, 0.0  # Red
            elif 'car' in class_name:
                marker.color.r, marker.color.g, marker.color.b = 0.0, 0.0, 1.0  # Blue
            else:
                marker.color.r, marker.color.g, marker.color.b = 0.0, 1.0, 0.0  # Green
                
            marker.color.a = 0.7  # Slightly transparent
            marker.lifetime = Duration(seconds=1.0).to_msg()
            
            # Add text label
            text_marker = Marker()
            text_marker.header = marker.header
            text_marker.ns = 'labels'
            text_marker.id = i
            text_marker.type = Marker.TEXT_VIEW_FACING
            text_marker.action = Marker.ADD
            text_marker.pose.position.x = x
            text_marker.pose.position.y = y
            text_marker.pose.position.z = z + 0.15
            text_marker.pose.orientation.w = 1.0
            text_marker.scale.z = 0.1
            text_marker.color.r = text_marker.color.g = text_marker.color.b = 1.0
            text_marker.color.a = 1.0
            text_marker.text = f"{det.get('class_name', 'object')} {det.get('confidence', 0):.1f}"
            text_marker.lifetime = Duration(seconds=1.0).to_msg()
            
            marker_array.markers.extend([marker, text_marker])
        
        self.marker_pub.publish(marker_array)
    
    def publish_detection_info(self, detections):
        """Publish detection information and markers."""
        if not isinstance(detections, list):
            return
            
        try:
            # Publish detection info as JSON
            info = {
                'header': {
                    'stamp': self.get_clock().now().to_msg(),
                    'frame_id': self.camera_frame
                },
                'detections': [{
                    'class_id': int(d.get('class_id', -1)),
                    'class_name': str(d.get('class_name', 'unknown')),
                    'confidence': float(d.get('confidence', 0.0)),
                    'bbox': [float(x) for x in d.get('bbox', [0, 0, 0, 0])],
                    'position_3d': [float(x) for x in d.get('position_3d', [0, 0, 0])]
                } for d in detections if isinstance(d, dict)],
                'num_detections': len(detections)
            }
            
            json_str = String()
            json_str.data = json.dumps(info, default=str)
            self.detection_info_pub.publish(json_str)
            
            # Publish object count
            count_msg = Point()
            count_msg.x = float(len(detections))
            self.object_count_pub.publish(count_msg)
            
            # Publish markers if enabled
            if self.visualize_in_rviz:
                self._publish_markers(detections)
                
        except Exception as e:
            self.get_logger().error(f'Publish error: {str(e)}', throttle_duration_sec=5.0)

def main(args=None):
    rclpy.init(args=args)
    node = ObjectDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down object detector')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
