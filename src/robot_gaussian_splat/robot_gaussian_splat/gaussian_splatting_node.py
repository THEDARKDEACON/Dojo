#!/usr/bin/env python3
"""
GaussianSplattingNode - Main ROS2 node for Gaussian Splatting reconstruction.

This node coordinates all components of the Gaussian Splatting reconstruction
system, including sensor synchronization, splat generation, reconstruction
management, and visualization.
"""

import rclpy
from rclpy.node import Node
from rclpy.timer import Timer
from sensor_msgs.msg import Image, PointCloud2, CameraInfo
from std_msgs.msg import Float32
from std_srvs.srv import Trigger
import os
from typing import Optional

from .sensor_synchronizer import SensorSynchronizer
from .splat_generator import SplatGenerator
from .reconstruction_manager import ReconstructionManager
from .visualization_publisher import VisualizationPublisher


class GaussianSplattingNode(Node):
    """
    Main ROS2 node for Gaussian Splatting reconstruction.
    
    This node manages the complete reconstruction pipeline:
    - Synchronizes camera and LiDAR sensor data
    - Generates Gaussian primitives from sensor data
    - Accumulates primitives into a reconstruction model
    - Provides visualization and diagnostic output
    - Offers services for model export and management
    """
    
    def __init__(self):
        """Initialize the GaussianSplattingNode with all components and parameters."""
        super().__init__('gaussian_splatting_node')
        
        # Declare and get parameters
        self._declare_parameters()
        self._get_parameters()
        
        # Initialize components
        self._initialize_components()
        
        # Set up publishers
        self._setup_publishers()
        
        # Set up services
        self._setup_services()
        
        # Set up visualization timer
        self._setup_visualization_timer()
        
        # Frame counter
        self.frames_processed = 0
        
        # Camera info cache (will be populated from synchronized callback)
        self.camera_info: Optional[CameraInfo] = None
        
        self.get_logger().info("GaussianSplattingNode initialized successfully")
    
    def _declare_parameters(self):
        """Declare all configurable ROS2 parameters."""
        # Synchronization parameters
        self.declare_parameter('sync_tolerance', 0.05)
        
        # Visualization parameters
        self.declare_parameter('visualization_enabled', True)
        self.declare_parameter('visualization_rate', 1.0)
        self.declare_parameter('visualization_limit', 10000)
        
        # Reconstruction parameters
        self.declare_parameter('max_primitives', 1000000)
        
        # Topic names
        self.declare_parameter('camera_topic', '/camera/image_raw')
        self.declare_parameter('camera_info_topic', '/camera/camera_info')
        self.declare_parameter('pointcloud_topic', '/scan')
        
        # Output directory
        self.declare_parameter('output_directory', os.path.expanduser('~/gaussian_splats'))
        
        # Frame ID for visualization
        self.declare_parameter('frame_id', 'map')
    
    def _get_parameters(self):
        """Retrieve parameter values from the parameter server."""
        self.sync_tolerance = self.get_parameter('sync_tolerance').value
        self.visualization_enabled = self.get_parameter('visualization_enabled').value
        self.visualization_rate = self.get_parameter('visualization_rate').value
        self.visualization_limit = self.get_parameter('visualization_limit').value
        self.max_primitives = self.get_parameter('max_primitives').value
        self.camera_topic = self.get_parameter('camera_topic').value
        self.camera_info_topic = self.get_parameter('camera_info_topic').value
        self.pointcloud_topic = self.get_parameter('pointcloud_topic').value
        self.output_directory = self.get_parameter('output_directory').value
        self.frame_id = self.get_parameter('frame_id').value
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_directory, exist_ok=True)
        
        self.get_logger().info(
            f"Parameters loaded:\n"
            f"  sync_tolerance: {self.sync_tolerance}s\n"
            f"  visualization_enabled: {self.visualization_enabled}\n"
            f"  visualization_rate: {self.visualization_rate}Hz\n"
            f"  visualization_limit: {self.visualization_limit}\n"
            f"  max_primitives: {self.max_primitives}\n"
            f"  camera_topic: {self.camera_topic}\n"
            f"  camera_info_topic: {self.camera_info_topic}\n"
            f"  pointcloud_topic: {self.pointcloud_topic}\n"
            f"  output_directory: {self.output_directory}\n"
            f"  frame_id: {self.frame_id}"
        )
    
    def _initialize_components(self):
        """Initialize all subsystem components."""
        # Initialize SensorSynchronizer
        self.sensor_synchronizer = SensorSynchronizer(
            node=self,
            sync_tolerance=self.sync_tolerance
        )
        
        # Set up subscribers through SensorSynchronizer
        self.sensor_synchronizer.setup_subscribers(
            camera_topic=self.camera_topic,
            camera_info_topic=self.camera_info_topic,
            pointcloud_topic=self.pointcloud_topic
        )
        
        # Register synchronized callback
        self.sensor_synchronizer.register_callback(self.synchronized_callback)
        
        # Initialize ReconstructionManager
        self.reconstruction_manager = ReconstructionManager(
            max_primitives=self.max_primitives
        )
        
        # Initialize VisualizationPublisher
        self.visualization_publisher = VisualizationPublisher(
            node=self,
            rate=self.visualization_rate,
            limit=self.visualization_limit
        )
        
        # SplatGenerator will be initialized after we receive first camera_info
        self.splat_generator: Optional[SplatGenerator] = None
        
        self.get_logger().info("All components initialized")
    
    def _setup_publishers(self):
        """Set up ROS2 publishers for diagnostics and progress."""
        # Progress publisher (percentage of reconstruction progress)
        self.progress_publisher = self.create_publisher(
            Float32,
            'gaussian_splat/progress',
            10
        )
        
        self.get_logger().info("Publishers set up")
    
    def _setup_services(self):
        """Set up ROS2 services for model management."""
        # Import custom service types
        # Note: These will be available after building the package with service definitions
        try:
            from robot_gaussian_splat.srv import SaveSplatModel, GetSplatStats
            
            self.save_model_service = self.create_service(
                SaveSplatModel,
                'gaussian_splat/save_model',
                self.save_model_service_callback
            )
            
            self.get_stats_service = self.create_service(
                GetSplatStats,
                'gaussian_splat/get_stats',
                self.get_stats_service_callback
            )
        except ImportError:
            self.get_logger().warning(
                "Custom service types not available. "
                "Please build the package to generate service definitions."
            )
        
        self.clear_model_service = self.create_service(
            Trigger,
            'gaussian_splat/clear_model',
            self.clear_model_service_callback
        )
        
        self.get_logger().info("Services set up")
    
    def _setup_visualization_timer(self):
        """Set up timer for periodic visualization publishing."""
        if self.visualization_enabled and self.visualization_rate > 0:
            timer_period = 1.0 / self.visualization_rate
            self.visualization_timer: Timer = self.create_timer(
                timer_period,
                self.publish_visualization
            )
            self.get_logger().info(
                f"Visualization timer set up: {self.visualization_rate}Hz"
            )
        else:
            self.visualization_timer = None
            self.get_logger().info("Visualization disabled")
    
    def synchronized_callback(
        self, 
        image_msg: Image, 
        camera_info_msg: CameraInfo,
        pointcloud_msg: PointCloud2
    ):
        """
        Process synchronized camera and LiDAR data.
        
        This callback is triggered when camera and LiDAR data are temporally
        aligned by the SensorSynchronizer. It generates Gaussian primitives
        from the sensor data and adds them to the reconstruction model.
        
        Args:
            image_msg: Synchronized camera image message
            camera_info_msg: Synchronized camera info message
            pointcloud_msg: Synchronized point cloud message
        """
        try:
            # Initialize SplatGenerator on first camera_info if not already done
            if self.splat_generator is None:
                self.get_logger().info("Initializing SplatGenerator with camera info")
                self.splat_generator = SplatGenerator(camera_info=camera_info_msg)
                self.camera_info = camera_info_msg
            
            # Update camera info if it has changed
            if self.camera_info != camera_info_msg:
                self.camera_info = camera_info_msg
                # Reinitialize SplatGenerator with new camera info
                self.splat_generator = SplatGenerator(camera_info=camera_info_msg)
                self.get_logger().info("Updated SplatGenerator with new camera info")
            
            # Get timestamp from message header
            timestamp = image_msg.header.stamp.sec + image_msg.header.stamp.nanosec * 1e-9
            
            # Generate Gaussian primitives from synchronized data
            primitives = self.splat_generator.generate_splats(
                image_msg=image_msg,
                pointcloud_msg=pointcloud_msg,
                timestamp=timestamp
            )
            
            # Add primitives to reconstruction manager
            if len(primitives) > 0:
                self.reconstruction_manager.add_primitives(primitives)
                
                # Update frame counter
                self.frames_processed += 1
                self.reconstruction_manager.model.metadata['total_frames_processed'] = self.frames_processed
                
                # Log progress periodically
                if self.frames_processed % 10 == 0:
                    primitive_count = self.reconstruction_manager.get_primitive_count()
                    self.get_logger().info(
                        f"Processed {self.frames_processed} frames, "
                        f"total primitives: {primitive_count}"
                    )
                
                # Publish progress (as a simple frame count for now)
                # In a more sophisticated implementation, this could be based on
                # mapped area coverage or other metrics
                progress_msg = Float32()
                progress_msg.data = float(self.frames_processed)
                self.progress_publisher.publish(progress_msg)
            else:
                self.get_logger().debug(
                    f"No primitives generated from frame {self.frames_processed}"
                )
        
        except Exception as e:
            self.get_logger().error(
                f"Error in synchronized callback: {str(e)}",
                throttle_duration_sec=1.0  # Throttle error messages to avoid spam
            )
    
    def save_model_service_callback(self, request, response):
        """
        Service callback to save the reconstruction model to disk.
        
        Exports the model in either PLY or JSON format based on the request.
        Returns success status, message, and primitive count.
        
        Args:
            request: SaveSplatModel request with filepath and format
            response: SaveSplatModel response to populate
            
        Returns:
            Populated response object
        """
        try:
            # Validate format
            if request.format not in ['ply', 'json']:
                response.success = False
                response.message = f"Invalid format '{request.format}'. Must be 'ply' or 'json'"
                response.primitive_count = 0
                return response
            
            # Get filepath (expand user directory if needed)
            filepath = os.path.expanduser(request.filepath)
            
            # If no directory specified, use default output directory
            if not os.path.dirname(filepath):
                filepath = os.path.join(self.output_directory, filepath)
            
            # Ensure proper file extension
            if request.format == 'ply' and not filepath.endswith('.ply'):
                filepath += '.ply'
            elif request.format == 'json' and not filepath.endswith('.json'):
                filepath += '.json'
            
            # Export model
            if request.format == 'ply':
                success = self.reconstruction_manager.export_ply(filepath)
            else:  # json
                success = self.reconstruction_manager.export_json(filepath)
            
            # Populate response
            if success:
                primitive_count = self.reconstruction_manager.get_primitive_count()
                response.success = True
                response.message = f"Successfully exported {primitive_count} primitives to {filepath}"
                response.primitive_count = primitive_count
                
                self.get_logger().info(response.message)
            else:
                response.success = False
                response.message = f"Failed to export model to {filepath}"
                response.primitive_count = 0
                
                self.get_logger().error(response.message)
        
        except Exception as e:
            response.success = False
            response.message = f"Error saving model: {str(e)}"
            response.primitive_count = 0
            self.get_logger().error(response.message)
        
        return response
    
    def clear_model_service_callback(self, request, response):
        """
        Service callback to clear the reconstruction model.
        
        Resets the model to an empty state, ready for a new reconstruction.
        
        Args:
            request: Trigger request (empty)
            response: Trigger response to populate
            
        Returns:
            Populated response object
        """
        try:
            # Clear the reconstruction model
            self.reconstruction_manager.clear()
            
            # Reset frame counter
            self.frames_processed = 0
            
            response.success = True
            response.message = "Reconstruction model cleared successfully"
            
            self.get_logger().info(response.message)
        
        except Exception as e:
            response.success = False
            response.message = f"Error clearing model: {str(e)}"
            self.get_logger().error(response.message)
        
        return response
    
    def get_stats_service_callback(self, request, response):
        """
        Service callback to get reconstruction statistics.
        
        Returns current statistics including primitive count, memory usage,
        bounding box, and frames processed.
        
        Args:
            request: GetSplatStats request (empty)
            response: GetSplatStats response to populate
            
        Returns:
            Populated response object
        """
        try:
            # Get statistics from reconstruction manager
            stats = self.reconstruction_manager.get_statistics()
            
            # Populate response
            response.primitive_count = stats['primitive_count']
            response.memory_usage_mb = stats['memory_usage_mb']
            response.frames_processed = stats['frames_processed']
            
            # Handle bounds (may be None if model is empty)
            if stats['bounds_min'] is not None:
                response.bounds_min = stats['bounds_min']
            else:
                response.bounds_min = [0.0, 0.0, 0.0]
            
            if stats['bounds_max'] is not None:
                response.bounds_max = stats['bounds_max']
            else:
                response.bounds_max = [0.0, 0.0, 0.0]
            
            self.get_logger().debug(
                f"Statistics requested: {response.primitive_count} primitives, "
                f"{response.memory_usage_mb:.2f} MB"
            )
        
        except Exception as e:
            self.get_logger().error(f"Error getting statistics: {str(e)}")
            # Return empty/zero values on error
            response.primitive_count = 0
            response.memory_usage_mb = 0.0
            response.frames_processed = 0
            response.bounds_min = [0.0, 0.0, 0.0]
            response.bounds_max = [0.0, 0.0, 0.0]
        
        return response
    
    def publish_visualization(self):
        """
        Timer callback to publish visualization markers and diagnostics.
        
        This method is called periodically by the visualization timer. It queries
        primitives from the ReconstructionManager and publishes them as RViz markers.
        It also publishes diagnostic information about the system state.
        """
        try:
            # Check if visualization is enabled
            if not self.visualization_enabled:
                return
            
            # Get primitives for visualization (limited to visualization_limit)
            primitives = self.reconstruction_manager.get_primitives_for_visualization(
                limit=self.visualization_limit
            )
            
            # Publish markers
            self.visualization_publisher.publish_markers(
                primitives=primitives,
                frame_id=self.frame_id
            )
            
            # Get statistics for diagnostics
            stats = self.reconstruction_manager.get_statistics()
            
            # Calculate sync rate from sensor synchronizer
            sync_stats = self.sensor_synchronizer.get_statistics()
            # Estimate sync rate based on success count and elapsed time
            # This is a simple approximation
            sync_rate = 0.0
            if self.frames_processed > 0:
                # Rough estimate: assume we've been running for frames_processed seconds at 10Hz
                sync_rate = self.frames_processed / max(1, self.frames_processed / 10.0)
            
            # Publish diagnostics
            self.visualization_publisher.publish_diagnostics(
                stats=stats,
                sync_rate=sync_rate
            )
        
        except Exception as e:
            self.get_logger().error(
                f"Error in visualization callback: {str(e)}",
                throttle_duration_sec=5.0  # Throttle to avoid spam
            )


def main(args=None):
    """Main entry point for the GaussianSplattingNode."""
    rclpy.init(args=args)
    
    try:
        node = GaussianSplattingNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error in GaussianSplattingNode: {e}")
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
