#!/usr/bin/env python3
"""
Vision Detection Node

ROS2 node for real-time object detection that publishes detection results
and annotated images according to the robot vision enhancement specification.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose
from geometry_msgs.msg import Pose2D
from cv_bridge import CvBridge, CvBridgeError
import cv2
import numpy as np
from typing import List, Tuple, Optional
import os
from ament_index_python.packages import get_package_share_directory
from ..performance_monitor import PerformanceMonitor
from ..resource_manager import ResourceManager, ResourceLimits


class VisionDetectionNode(Node):
    """
    ROS2 node for object detection with proper initialization and cleanup.
    
    Subscribes to camera images and publishes detection results and annotated images
    with synchronized timestamps according to the vision enhancement requirements.
    """
    
    def __init__(self):
        super().__init__('vision_detection_node')
        
        # Initialize CV bridge for image conversion
        self.bridge = CvBridge()
        
        # Declare parameters
        self.declare_parameters(
            namespace='',
            parameters=[
                ('confidence_threshold', 0.5),
                ('input_topic', '/camera/image_raw'),
                ('detection_image_topic', '/camera/detection_image'),
                ('detections_topic', '/detections'),
                ('camera_frame', 'camera_optical_frame'),
                ('debug_mode', False),
                ('target_fps', 10.0),
                ('cpu_threshold', 80.0),
                ('memory_threshold_mb', 500.0),
                ('enable_performance_monitoring', True),
                ('enable_resource_management', True),
                ('max_fps', 30.0),
                ('min_fps', 5.0),
            ]
        )
        
        # Get parameters
        self.confidence_threshold = self.get_parameter('confidence_threshold').value
        self.input_topic = self.get_parameter('input_topic').value
        self.detection_image_topic = self.get_parameter('detection_image_topic').value
        self.detections_topic = self.get_parameter('detections_topic').value
        self.camera_frame = self.get_parameter('camera_frame').value
        self.debug_mode = self.get_parameter('debug_mode').value
        self.target_fps = self.get_parameter('target_fps').value
        self.cpu_threshold = self.get_parameter('cpu_threshold').value
        self.memory_threshold_mb = self.get_parameter('memory_threshold_mb').value
        self.enable_performance_monitoring = self.get_parameter('enable_performance_monitoring').value
        self.enable_resource_management = self.get_parameter('enable_resource_management').value
        self.max_fps = self.get_parameter('max_fps').value
        self.min_fps = self.get_parameter('min_fps').value
        
        # Setup QoS profile for image topics
        image_qos = QoSProfile(
            depth=10,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE
        )
        
        # Setup QoS profile for detection topics
        detection_qos = QoSProfile(
            depth=10,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE
        )
        
        # Initialize subscribers
        self.image_subscriber = self.create_subscription(
            Image,
            self.input_topic,
            self.image_callback,
            image_qos
        )
        
        # Initialize publishers
        self.detection_image_publisher = self.create_publisher(
            Image,
            self.detection_image_topic,
            image_qos
        )
        
        self.detections_publisher = self.create_publisher(
            Detection2DArray,
            self.detections_topic,
            detection_qos
        )
        
        # Initialize object detection model
        self.detection_model = None
        self.model_initialized = False
        self.class_names = {}
        self._initialize_detection_model()
        
        # Statistics
        self.frame_count = 0
        self.detection_count = 0
        
        # Initialize performance monitor
        self.performance_monitor = None
        if self.enable_performance_monitoring:
            self.performance_monitor = PerformanceMonitor(
                node=self,
                target_fps=self.target_fps,
                cpu_threshold=self.cpu_threshold,
                memory_threshold_mb=self.memory_threshold_mb
            )
            
            # Register alert callbacks
            self.performance_monitor.register_alert_callback('fps', self._handle_fps_alert)
            self.performance_monitor.register_alert_callback('cpu', self._handle_cpu_alert)
            self.performance_monitor.register_alert_callback('memory', self._handle_memory_alert)
        
        # Initialize resource manager
        self.resource_manager = None
        if self.enable_resource_management:
            limits = ResourceLimits(
                max_cpu_percent=self.cpu_threshold,
                max_memory_mb=self.memory_threshold_mb,
                min_fps=self.min_fps,
                max_fps=self.max_fps
            )
            self.resource_manager = ResourceManager(node=self, limits=limits)
        
        self.get_logger().info(f'Vision Detection Node initialized')
        self.get_logger().info(f'Subscribing to: {self.input_topic}')
        self.get_logger().info(f'Publishing detections to: {self.detections_topic}')
        self.get_logger().info(f'Publishing annotated images to: {self.detection_image_topic}')
        if self.enable_performance_monitoring:
            self.get_logger().info(f'Performance monitoring enabled - Target FPS: {self.target_fps}')
        if self.enable_resource_management:
            self.get_logger().info(f'Resource management enabled - FPS range: {self.min_fps}-{self.max_fps}')
    
    def _initialize_detection_model(self) -> None:
        """
        Initialize the object detection model using OpenCV DNN or YOLO.
        
        Implements lightweight object detection with bounding box detection
        and confidence scoring functionality.
        """
        try:
            # Try to use ultralytics YOLO first (lightweight and efficient)
            try:
                from ultralytics import YOLO
                
                # Get model path - check package directory first
                model_filename = 'yolov8n.pt'  # Lightweight nano model
                
                # Try to find model in package
                try:
                    pkg_share = get_package_share_directory('robot_perception')
                    model_path = os.path.join(pkg_share, 'models', model_filename)
                except:
                    # Fallback to package source directory
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    model_path = os.path.join(current_dir, '..', model_filename)
                
                if not os.path.exists(model_path):
                    # If model doesn't exist, YOLO will download it automatically
                    model_path = model_filename
                
                # Load YOLO model
                self.detection_model = YOLO(model_path)
                self.class_names = self.detection_model.names
                self.model_initialized = True
                
                self.get_logger().info(f'YOLO model loaded successfully from {model_path}')
                self.get_logger().info(f'Model supports {len(self.class_names)} classes')
                
            except ImportError:
                self.get_logger().warn('ultralytics not available, falling back to OpenCV DNN')
                self._initialize_opencv_dnn()
                
        except Exception as e:
            self.get_logger().error(f'Failed to initialize detection model: {e}')
            self.get_logger().warn('Running without object detection')
    
    def _initialize_opencv_dnn(self) -> None:
        """
        Fallback initialization using OpenCV DNN for object detection.
        
        This provides a lightweight alternative when YOLO is not available.
        """
        try:
            # For now, create a simple placeholder that can detect basic shapes
            # In a real implementation, this would load a pre-trained DNN model
            self.detection_model = "opencv_dnn_placeholder"
            self.class_names = {
                0: 'object',
                1: 'person',
                2: 'vehicle'
            }
            self.model_initialized = True
            self.get_logger().info('OpenCV DNN placeholder initialized')
            
        except Exception as e:
            self.get_logger().error(f'Failed to initialize OpenCV DNN: {e}')
    
    def _detect_objects_yolo(self, cv_image: np.ndarray) -> List[dict]:
        """
        Perform object detection using YOLO model.
        
        Args:
            cv_image: Input image as numpy array
            
        Returns:
            List of detection dictionaries with bounding boxes and confidence scores
        """
        detections = []
        
        try:
            # Run YOLO inference
            results = self.detection_model(cv_image, verbose=False)
            
            for result in results:
                if result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()  # x1, y1, x2, y2
                    confidences = result.boxes.conf.cpu().numpy()
                    class_ids = result.boxes.cls.cpu().numpy().astype(int)
                    
                    for box, confidence, class_id in zip(boxes, confidences, class_ids):
                        if confidence >= self.confidence_threshold:
                            x1, y1, x2, y2 = box
                            width = x2 - x1
                            height = y2 - y1
                            center_x = x1 + width / 2
                            center_y = y1 + height / 2
                            
                            detection = {
                                'class_id': int(class_id),
                                'class_name': self.class_names.get(class_id, f'class_{class_id}'),
                                'confidence': float(confidence),
                                'x1': float(x1),
                                'y1': float(y1),
                                'x2': float(x2),
                                'y2': float(y2),
                                'width': float(width),
                                'height': float(height),
                                'center_x': float(center_x),
                                'center_y': float(center_y)
                            }
                            detections.append(detection)
                            
        except Exception as e:
            self.get_logger().error(f'YOLO detection error: {e}')
            
        return detections
    
    def _detect_objects_opencv(self, cv_image: np.ndarray) -> List[dict]:
        """
        Placeholder object detection using OpenCV (for demonstration).
        
        In a real implementation, this would use OpenCV DNN with a pre-trained model.
        
        Args:
            cv_image: Input image as numpy array
            
        Returns:
            List of detection dictionaries
        """
        detections = []
        
        try:
            # Simple placeholder detection based on image properties
            # This is just for demonstration - real implementation would use DNN
            height, width = cv_image.shape[:2]
            
            # Create a fake detection in the center of the image
            if self.frame_count % 60 == 0:  # Every 2 seconds at 30fps
                detection = {
                    'class_id': 0,
                    'class_name': 'object',
                    'confidence': 0.8,
                    'x1': float(width * 0.3),
                    'y1': float(height * 0.3),
                    'x2': float(width * 0.7),
                    'y2': float(height * 0.7),
                    'width': float(width * 0.4),
                    'height': float(height * 0.4),
                    'center_x': float(width * 0.5),
                    'center_y': float(height * 0.5)
                }
                detections.append(detection)
                
        except Exception as e:
            self.get_logger().error(f'OpenCV detection error: {e}')
            
        return detections
    
    def _render_detections(self, cv_image: np.ndarray, detections: List[dict]) -> np.ndarray:
        """
        Render bounding boxes and labels on the image.
        
        Args:
            cv_image: Input image
            detections: List of detection dictionaries
            
        Returns:
            Annotated image with bounding boxes and labels
        """
        annotated_image = cv_image.copy()
        
        try:
            for detection in detections:
                # Extract coordinates
                x1 = int(detection['x1'])
                y1 = int(detection['y1'])
                x2 = int(detection['x2'])
                y2 = int(detection['y2'])
                
                # Choose color based on class
                class_name = detection.get('class_name', 'unknown')
                if 'person' in class_name.lower():
                    color = (0, 0, 255)  # Red for persons
                elif 'car' in class_name.lower() or 'vehicle' in class_name.lower():
                    color = (255, 0, 0)  # Blue for vehicles
                else:
                    color = (0, 255, 0)  # Green for other objects
                
                # Draw bounding box
                cv2.rectangle(annotated_image, (x1, y1), (x2, y2), color, 2)
                
                # Create label with class name and confidence
                confidence = detection.get('confidence', 0.0)
                label = f"{class_name} {confidence:.2f}"
                
                # Calculate label size and position
                (label_width, label_height), baseline = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                )
                
                # Draw label background
                cv2.rectangle(
                    annotated_image,
                    (x1, y1 - label_height - baseline - 5),
                    (x1 + label_width, y1),
                    color,
                    -1
                )
                
                # Draw label text
                cv2.putText(
                    annotated_image,
                    label,
                    (x1, y1 - baseline - 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )
                
        except Exception as e:
            self.get_logger().error(f'Error rendering detections: {e}')
            
        return annotated_image
    
    def image_callback(self, msg: Image) -> None:
        """
        Process incoming camera images and publish detection results.
        
        Args:
            msg: Input image message from camera
        """
        # Check if we should process this frame (resource management throttling)
        if self.resource_manager and not self.resource_manager.should_process_frame():
            # Skip this frame due to throttling
            if self.performance_monitor:
                self.performance_monitor.report_dropped_frame()
            return
        
        # Start performance monitoring for this frame
        processing_start = None
        if self.performance_monitor:
            processing_start = self.performance_monitor.start_frame_processing()
        
        try:
            # Convert ROS image to OpenCV format
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            
            # Increment frame counter
            self.frame_count += 1
            
            # Process image for object detection with resource management
            detections, annotated_image = self._process_image_with_resource_management(cv_image, msg.header)
            
            # Publish detection results with synchronized timestamps
            self._publish_detections(detections, msg.header)
            
            # Publish annotated image with synchronized timestamps
            self._publish_annotated_image(annotated_image, msg.header)
            
            # End performance monitoring and update resource manager
            if self.performance_monitor and processing_start:
                self.performance_monitor.end_frame_processing(processing_start, len(detections))
                
                # Update resource manager with current performance metrics
                if self.resource_manager:
                    metrics = self.performance_monitor.get_current_metrics()
                    self.resource_manager.update_performance_metrics(
                        metrics.cpu_usage,
                        metrics.memory_usage_mb,
                        metrics.frame_rate
                    )
            
            if self.debug_mode and self.frame_count % 30 == 0:  # Log every 30 frames
                if self.performance_monitor:
                    metrics = self.performance_monitor.get_current_metrics()
                    resource_status = self.resource_manager.get_resource_status() if self.resource_manager else {}
                    self.get_logger().info(
                        f'Processed {self.frame_count} frames, '
                        f'detected {len(detections)} objects in current frame, '
                        f'FPS: {metrics.frame_rate:.1f}, CPU: {metrics.cpu_usage:.1f}%, '
                        f'FPS Limit: {resource_status.get("fps_limit", "N/A")}'
                    )
                else:
                    self.get_logger().info(
                        f'Processed {self.frame_count} frames, '
                        f'detected {len(detections)} objects in current frame'
                    )
                
        except CvBridgeError as e:
            self.get_logger().error(f'CV Bridge error: {e}')
            if self.performance_monitor:
                self.performance_monitor.report_dropped_frame()
        except Exception as e:
            self.get_logger().error(f'Error in image callback: {e}')
            if self.performance_monitor:
                self.performance_monitor.report_dropped_frame()
    
    def _process_image(self, cv_image: np.ndarray, header) -> Tuple[List[dict], np.ndarray]:
        """
        Process image for object detection using the initialized model.
        
        Implements bounding box detection and confidence scoring functionality
        with class label mapping and annotation rendering.
        
        Args:
            cv_image: OpenCV image array
            header: ROS message header for timestamp synchronization
            
        Returns:
            Tuple of (detections_list, annotated_image)
        """
        detections = []
        
        if not self.model_initialized:
            # If no model is available, return empty detections
            annotated_image = cv_image.copy()
            cv2.putText(
                annotated_image,
                'No detection model available',
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )
            return detections, annotated_image
        
        try:
            # Perform object detection based on available model
            if hasattr(self.detection_model, 'predict') or hasattr(self.detection_model, '__call__'):
                # YOLO model
                detections = self._detect_objects_yolo(cv_image)
            else:
                # OpenCV DNN fallback
                detections = self._detect_objects_opencv(cv_image)
            
            # Render detections on image
            annotated_image = self._render_detections(cv_image, detections)
            
            # Add frame info
            cv2.putText(
                annotated_image,
                f'Frame {self.frame_count} | Detections: {len(detections)}',
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
            
        except Exception as e:
            self.get_logger().error(f'Error processing image: {e}')
            annotated_image = cv_image.copy()
            cv2.putText(
                annotated_image,
                f'Detection error: {str(e)[:50]}',
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                2
            )
        
        return detections, annotated_image
    
    def _process_image_with_resource_management(self, cv_image: np.ndarray, header) -> Tuple[List[dict], np.ndarray]:
        """
        Process image with resource management optimizations.
        
        Implements memory cleanup for image buffers and graceful degradation
        when resource limits are exceeded.
        
        Args:
            cv_image: OpenCV image array
            header: ROS message header for timestamp synchronization
            
        Returns:
            Tuple of (detections_list, annotated_image)
        """
        detections = []
        
        if not self.model_initialized:
            # If no model is available, return empty detections
            annotated_image = cv_image.copy()
            cv2.putText(
                annotated_image,
                'No detection model available',
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )
            return detections, annotated_image
        
        try:
            # Check degradation level and adjust processing accordingly
            degradation_level = 0
            if self.resource_manager:
                degradation_level = self.resource_manager.get_degradation_level()
            
            # Apply degradation strategies
            processed_image = cv_image
            if degradation_level >= 2:  # Moderate or severe degradation
                # Reduce image resolution to save processing time
                height, width = cv_image.shape[:2]
                new_height, new_width = height // 2, width // 2
                processed_image = cv2.resize(cv_image, (new_width, new_height))
                
            elif degradation_level >= 1:  # Light degradation
                # Reduce image quality slightly
                processed_image = cv2.resize(cv_image, None, fx=0.8, fy=0.8)
            
            # Perform object detection based on available model
            if hasattr(self.detection_model, 'predict') or hasattr(self.detection_model, '__call__'):
                # YOLO model
                detections = self._detect_objects_yolo(processed_image)
            else:
                # OpenCV DNN fallback
                detections = self._detect_objects_opencv(processed_image)
            
            # Scale detection coordinates back if image was resized
            if degradation_level >= 1 and detections:
                scale_x = cv_image.shape[1] / processed_image.shape[1]
                scale_y = cv_image.shape[0] / processed_image.shape[0]
                
                for detection in detections:
                    detection['x1'] *= scale_x
                    detection['x2'] *= scale_x
                    detection['y1'] *= scale_y
                    detection['y2'] *= scale_y
                    detection['center_x'] *= scale_x
                    detection['center_y'] *= scale_y
                    detection['width'] *= scale_x
                    detection['height'] *= scale_y
            
            # Render detections on original image
            annotated_image = self._render_detections(cv_image, detections)
            
            # Add system status info
            status_text = f'Frame {self.frame_count} | Detections: {len(detections)}'
            if self.resource_manager:
                if self.resource_manager.is_throttling_active():
                    status_text += f' | Throttling: ON'
                if degradation_level > 0:
                    level_names = ['Normal', 'Light', 'Moderate', 'Severe']
                    status_text += f' | Degradation: {level_names[degradation_level]}'
            
            cv2.putText(
                annotated_image,
                status_text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
            
            # Request memory cleanup if needed
            if self.resource_manager and degradation_level >= 2:
                self.resource_manager.request_memory_cleanup()
            
        except Exception as e:
            self.get_logger().error(f'Error processing image with resource management: {e}')
            annotated_image = cv_image.copy()
            cv2.putText(
                annotated_image,
                f'Detection error: {str(e)[:50]}',
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                2
            )
        
        return detections, annotated_image
    
    def _publish_detections(self, detections: List[dict], header) -> None:
        """
        Publish detection results as vision_msgs/Detection2DArray with proper structure.
        
        Creates vision_msgs/Detection2DArray message publishing with proper structure,
        ensuring timestamp synchronization between raw and detection topics.
        
        Args:
            detections: List of detection dictionaries
            header: Original image header for timestamp synchronization
        """
        try:
            # Create Detection2DArray message with synchronized timestamp
            detection_array = Detection2DArray()
            
            # Ensure timestamp synchronization with original image
            detection_array.header.stamp = header.stamp
            detection_array.header.frame_id = self.camera_frame
            
            # Convert each detection to Detection2D message format
            for detection in detections:
                detection_2d = Detection2D()
                
                # Set bounding box with proper coordinate system
                # vision_msgs uses center point + size representation
                detection_2d.bbox.center.x = detection.get('center_x', 0.0)
                detection_2d.bbox.center.y = detection.get('center_y', 0.0)
                detection_2d.bbox.size_x = detection.get('width', 0.0)
                detection_2d.bbox.size_y = detection.get('height', 0.0)
                
                # Create object hypothesis with class ID and confidence
                hypothesis = ObjectHypothesisWithPose()
                hypothesis.id = str(detection.get('class_id', 0))
                hypothesis.score = detection.get('confidence', 0.0)
                
                # Set pose (currently not used for 2D detection, but required by message)
                hypothesis.pose.pose.position.x = 0.0
                hypothesis.pose.pose.position.y = 0.0
                hypothesis.pose.pose.position.z = 0.0
                hypothesis.pose.pose.orientation.w = 1.0
                
                # Add hypothesis to detection
                detection_2d.results.append(hypothesis)
                
                # Add detection to array
                detection_array.detections.append(detection_2d)
            
            # Validate message structure before publishing
            if self._validate_detection_message(detection_array):
                # Publish detection array with synchronized timestamp
                self.detections_publisher.publish(detection_array)
            else:
                self.get_logger().error('Invalid detection message structure, skipping publish')
            
            # Update statistics
            self.detection_count += len(detections)
            
            if self.debug_mode and len(detections) > 0:
                self.get_logger().debug(
                    f'Published {len(detections)} detections at timestamp '
                    f'{header.stamp.sec}.{header.stamp.nanosec}'
                )
            
        except Exception as e:
            self.get_logger().error(f'Error publishing detections: {e}')
    
    def _publish_annotated_image(self, annotated_image: np.ndarray, header) -> None:
        """
        Publish annotated image with bounding box overlays.
        
        Implements annotated image publishing with bounding box overlays,
        ensuring timestamp synchronization between raw and detection topics.
        
        Args:
            annotated_image: OpenCV image with annotations and bounding boxes
            header: Original image header for timestamp synchronization
        """
        try:
            # Convert OpenCV image back to ROS message format
            annotated_msg = self.bridge.cv2_to_imgmsg(annotated_image, encoding='bgr8')
            
            # Ensure timestamp synchronization with original image
            annotated_msg.header.stamp = header.stamp
            annotated_msg.header.frame_id = self.camera_frame
            
            # Verify timestamp synchronization (within tolerance)
            original_time = header.stamp.sec + header.stamp.nanosec * 1e-9
            annotated_time = annotated_msg.header.stamp.sec + annotated_msg.header.stamp.nanosec * 1e-9
            time_diff = abs(annotated_time - original_time)
            
            if time_diff > 0.01:  # 10ms tolerance
                self.get_logger().warn(
                    f'Timestamp synchronization issue: {time_diff:.3f}s difference',
                    throttle_duration_sec=5.0
                )
            
            # Publish annotated image with synchronized timestamp
            self.detection_image_publisher.publish(annotated_msg)
            
            if self.debug_mode and self.frame_count % 30 == 0:
                self.get_logger().debug(
                    f'Published annotated image at timestamp '
                    f'{annotated_msg.header.stamp.sec}.{annotated_msg.header.stamp.nanosec}'
                )
            
        except CvBridgeError as e:
            self.get_logger().error(f'CV Bridge error in annotated image: {e}')
        except Exception as e:
            self.get_logger().error(f'Error publishing annotated image: {e}')
    
    def _validate_detection_message(self, detection_array: Detection2DArray) -> bool:
        """
        Validate the structure of the Detection2DArray message.
        
        Ensures the detection message follows the proper vision_msgs format
        and contains all required fields.
        
        Args:
            detection_array: The detection message to validate
            
        Returns:
            True if message is valid, False otherwise
        """
        try:
            # Check header
            if not hasattr(detection_array, 'header'):
                self.get_logger().error('Detection message missing header')
                return False
            
            if not detection_array.header.frame_id:
                self.get_logger().error('Detection message missing frame_id')
                return False
            
            # Check detections array
            if not hasattr(detection_array, 'detections'):
                self.get_logger().error('Detection message missing detections array')
                return False
            
            # Validate each detection
            for i, detection in enumerate(detection_array.detections):
                # Check bounding box
                if not hasattr(detection, 'bbox'):
                    self.get_logger().error(f'Detection {i} missing bbox')
                    return False
                
                # Check results
                if not hasattr(detection, 'results') or len(detection.results) == 0:
                    self.get_logger().error(f'Detection {i} missing results')
                    return False
                
                # Check hypothesis
                for j, hypothesis in enumerate(detection.results):
                    if not hasattr(hypothesis, 'id') or not hasattr(hypothesis, 'score'):
                        self.get_logger().error(f'Detection {i}, hypothesis {j} missing id or score')
                        return False
            
            return True
            
        except Exception as e:
            self.get_logger().error(f'Error validating detection message: {e}')
            return False
    
    def _handle_fps_alert(self, current_fps: float, target_fps: float) -> None:
        """
        Handle frame rate performance alert.
        
        Args:
            current_fps: Current measured frame rate
            target_fps: Target frame rate
        """
        self.get_logger().warn(
            f'FPS Alert: Current {current_fps:.1f} FPS below target {target_fps:.1f} FPS'
        )
    
    def _handle_cpu_alert(self, current_cpu: float, threshold: float) -> None:
        """
        Handle CPU usage performance alert.
        
        Args:
            current_cpu: Current CPU usage percentage
            threshold: CPU usage threshold
        """
        self.get_logger().warn(
            f'CPU Alert: Current {current_cpu:.1f}% exceeds threshold {threshold:.1f}%'
        )
    
    def _handle_memory_alert(self, current_memory: float, threshold: float) -> None:
        """
        Handle memory usage performance alert.
        
        Args:
            current_memory: Current memory usage in MB
            threshold: Memory usage threshold in MB
        """
        self.get_logger().warn(
            f'Memory Alert: Current {current_memory:.1f}MB exceeds threshold {threshold:.1f}MB'
        )
    
    def destroy_node(self) -> None:
        """Clean up resources when node is destroyed."""
        self.get_logger().info('Vision Detection Node shutting down...')
        self.get_logger().info(f'Processed {self.frame_count} total frames')
        self.get_logger().info(f'Total detections published: {self.detection_count}')
        
        # Shutdown performance monitor
        if self.performance_monitor:
            self.performance_monitor.shutdown()
        
        # Shutdown resource manager
        if self.resource_manager:
            self.resource_manager.shutdown()
        
        # Clean up detection model if needed
        if self.detection_model is not None:
            try:
                del self.detection_model
            except:
                pass
        
        super().destroy_node()


def main(args=None):
    """Main entry point for the vision detection node."""
    rclpy.init(args=args)
    
    try:
        node = VisionDetectionNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'Error in vision detection node: {e}')
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()