"""
VisualizationPublisher component for Gaussian Splatting reconstruction.

This module handles the conversion of Gaussian primitives to RViz markers
and publishes visualization and diagnostic data at configurable rates.
"""

import logging
from typing import List, Dict
import numpy as np
from rclpy.node import Node
from rclpy.timer import Timer
from visualization_msgs.msg import Marker, MarkerArray
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from std_msgs.msg import ColorRGBA

from .data_models import GaussianPrimitive


class VisualizationPublisher:
    """
    Manages visualization and diagnostics publishing for Gaussian Splat reconstruction.
    
    This class converts Gaussian primitives to RViz markers, manages visualization
    update rates, and publishes system diagnostics including primitive count,
    memory usage, and synchronization statistics.
    """
    
    def __init__(self, node: Node, rate: float = 1.0, limit: int = 10000):
        """
        Initialize the VisualizationPublisher.
        
        Args:
            node: ROS2 node instance for creating publishers and timers
            rate: Visualization publish rate in Hz
            limit: Maximum number of primitives to visualize
        """
        self.node = node
        self.rate = rate
        self.limit = limit
        
        # Set up logging
        self.logger = logging.getLogger('VisualizationPublisher')
        self.logger.setLevel(logging.INFO)
        
        # Create publishers
        self.marker_publisher = self.node.create_publisher(
            MarkerArray,
            'gaussian_splat/visualization',
            10
        )
        
        self.diagnostics_publisher = self.node.create_publisher(
            DiagnosticArray,
            'gaussian_splat/diagnostics',
            10
        )
        
        # Set up timer for periodic publishing
        timer_period = 1.0 / rate if rate > 0 else 1.0
        self.timer: Timer = self.node.create_timer(
            timer_period,
            self._timer_callback
        )
        
        # State for timer callback
        self.primitives_to_publish: List[GaussianPrimitive] = []
        self.stats_to_publish: Dict = {}
        
        self.logger.info(
            f"VisualizationPublisher initialized: rate={rate}Hz, limit={limit}"
        )
    
    def _timer_callback(self):
        """
        Timer callback for periodic publishing.
        
        This is called automatically by the ROS2 timer at the configured rate.
        It publishes both markers and diagnostics if data is available.
        """
        # This callback will be triggered by the timer
        # The actual publishing is done through explicit calls to publish_markers
        # and publish_diagnostics from the main node
        pass

    def create_marker(self, primitive: GaussianPrimitive, marker_id: int, 
                     frame_id: str = "map") -> Marker:
        """
        Convert a GaussianPrimitive to a RViz Marker.
        
        The marker is represented as a SPHERE with color and scale derived from
        the primitive's properties. The scale is computed from the covariance
        matrix eigenvalues to represent the Gaussian's extent.
        
        Args:
            primitive: GaussianPrimitive to convert
            marker_id: Unique ID for the marker
            frame_id: Reference frame for the marker (default: "map")
            
        Returns:
            Marker message for RViz visualization
        """
        marker = Marker()
        
        # Header
        marker.header.frame_id = frame_id
        marker.header.stamp = self.node.get_clock().now().to_msg()
        
        # Marker properties
        marker.ns = "gaussian_splats"
        marker.id = marker_id
        marker.type = Marker.SPHERE
        marker.action = Marker.ADD
        
        # Position from primitive
        marker.pose.position.x = float(primitive.position[0])
        marker.pose.position.y = float(primitive.position[1])
        marker.pose.position.z = float(primitive.position[2])
        
        # Orientation (identity quaternion)
        marker.pose.orientation.x = 0.0
        marker.pose.orientation.y = 0.0
        marker.pose.orientation.z = 0.0
        marker.pose.orientation.w = 1.0
        
        # Scale from covariance eigenvalues
        # Compute eigenvalues to determine the extent of the Gaussian
        try:
            eigenvalues = np.linalg.eigvalsh(primitive.covariance)
            # Use 2 standard deviations (95% confidence) for visualization
            scale_factor = 2.0
            marker.scale.x = float(scale_factor * np.sqrt(abs(eigenvalues[0])))
            marker.scale.y = float(scale_factor * np.sqrt(abs(eigenvalues[1])))
            marker.scale.z = float(scale_factor * np.sqrt(abs(eigenvalues[2])))
            
            # Ensure minimum scale for visibility
            min_scale = 0.01
            marker.scale.x = max(marker.scale.x, min_scale)
            marker.scale.y = max(marker.scale.y, min_scale)
            marker.scale.z = max(marker.scale.z, min_scale)
        except Exception as e:
            # Fallback to default scale if eigenvalue computation fails
            self.logger.warning(f"Failed to compute scale from covariance: {e}")
            marker.scale.x = 0.05
            marker.scale.y = 0.05
            marker.scale.z = 0.05
        
        # Color from primitive (normalize to [0, 1])
        marker.color = ColorRGBA()
        marker.color.r = float(primitive.color[0]) / 255.0
        marker.color.g = float(primitive.color[1]) / 255.0
        marker.color.b = float(primitive.color[2]) / 255.0
        marker.color.a = float(primitive.opacity)
        
        # Marker lifetime (0 means forever, but we'll set a reasonable value)
        marker.lifetime.sec = 2  # 2 seconds (refresh at 1Hz means this is safe)
        marker.lifetime.nanosec = 0
        
        return marker

    def publish_markers(self, primitives: List[GaussianPrimitive], frame_id: str = "map"):
        """
        Publish a MarkerArray of Gaussian primitives for RViz visualization.
        
        If the number of primitives exceeds the visualization limit, uniformly
        samples primitives to stay within the limit. This prevents overwhelming
        RViz with too many markers.
        
        Args:
            primitives: List of GaussianPrimitive objects to visualize
            frame_id: Reference frame for the markers (default: "map")
        """
        if len(primitives) == 0:
            # Publish empty marker array to clear previous markers
            marker_array = MarkerArray()
            delete_marker = Marker()
            delete_marker.action = Marker.DELETEALL
            marker_array.markers.append(delete_marker)
            self.marker_publisher.publish(marker_array)
            return
        
        # Limit primitives if necessary
        primitives_to_viz = primitives
        if len(primitives) > self.limit:
            # Uniformly sample primitives
            indices = np.linspace(0, len(primitives) - 1, self.limit, dtype=int)
            primitives_to_viz = [primitives[i] for i in indices]
            self.logger.debug(
                f"Sampling {self.limit} of {len(primitives)} primitives for visualization"
            )
        
        # Create marker array
        marker_array = MarkerArray()
        
        for idx, primitive in enumerate(primitives_to_viz):
            marker = self.create_marker(primitive, idx, frame_id)
            marker_array.markers.append(marker)
        
        # Publish markers
        self.marker_publisher.publish(marker_array)
        
        self.logger.debug(
            f"Published {len(marker_array.markers)} markers to RViz"
        )

    def publish_diagnostics(self, stats: Dict, sync_rate: float = 0.0):
        """
        Publish system diagnostics including primitive count, memory usage, and sync rate.
        
        Publishes diagnostic warnings when appropriate (e.g., high memory usage,
        low sync rate, or other system issues).
        
        Args:
            stats: Dictionary containing reconstruction statistics from ReconstructionManager
            sync_rate: Current sensor synchronization rate in Hz
        """
        diagnostic_array = DiagnosticArray()
        diagnostic_array.header.stamp = self.node.get_clock().now().to_msg()
        
        # Create main status message
        status = DiagnosticStatus()
        status.name = "Gaussian Splatting Reconstruction"
        status.hardware_id = "gaussian_splat_node"
        
        # Determine overall status level
        primitive_count = stats.get('primitive_count', 0)
        memory_usage_mb = stats.get('memory_usage_mb', 0.0)
        downsample_count = stats.get('downsample_count', 0)
        
        # Status logic
        warnings = []
        errors = []
        
        # Check memory usage
        if memory_usage_mb > 1000:  # > 1GB
            warnings.append(f"High memory usage: {memory_usage_mb:.1f} MB")
        
        # Check sync rate
        if sync_rate < 1.0 and sync_rate > 0:
            warnings.append(f"Low sync rate: {sync_rate:.2f} Hz")
        
        # Check if downsampling occurred
        if downsample_count > 0:
            warnings.append(f"Downsampling applied {downsample_count} times")
        
        # Set status level
        if len(errors) > 0:
            status.level = DiagnosticStatus.ERROR
            status.message = "; ".join(errors)
        elif len(warnings) > 0:
            status.level = DiagnosticStatus.WARN
            status.message = "; ".join(warnings)
        else:
            status.level = DiagnosticStatus.OK
            status.message = "System operating normally"
        
        # Add key-value pairs for detailed information
        status.values.append(KeyValue(
            key="Primitive Count",
            value=str(primitive_count)
        ))
        
        status.values.append(KeyValue(
            key="Memory Usage (MB)",
            value=f"{memory_usage_mb:.2f}"
        ))
        
        status.values.append(KeyValue(
            key="Sync Rate (Hz)",
            value=f"{sync_rate:.2f}"
        ))
        
        status.values.append(KeyValue(
            key="Frames Processed",
            value=str(stats.get('frames_processed', 0))
        ))
        
        status.values.append(KeyValue(
            key="Total Primitives Added",
            value=str(stats.get('total_primitives_added', 0))
        ))
        
        status.values.append(KeyValue(
            key="Downsample Count",
            value=str(downsample_count)
        ))
        
        # Add bounds information if available
        bounds_min = stats.get('bounds_min')
        bounds_max = stats.get('bounds_max')
        if bounds_min is not None and bounds_max is not None:
            status.values.append(KeyValue(
                key="Bounds Min",
                value=f"[{bounds_min[0]:.2f}, {bounds_min[1]:.2f}, {bounds_min[2]:.2f}]"
            ))
            status.values.append(KeyValue(
                key="Bounds Max",
                value=f"[{bounds_max[0]:.2f}, {bounds_max[1]:.2f}, {bounds_max[2]:.2f}]"
            ))
        
        # Add status to array and publish
        diagnostic_array.status.append(status)
        self.diagnostics_publisher.publish(diagnostic_array)
        
        self.logger.debug(
            f"Published diagnostics: {primitive_count} primitives, "
            f"{memory_usage_mb:.1f} MB, {sync_rate:.2f} Hz"
        )
    
    def shutdown(self):
        """
        Clean up resources when shutting down.
        
        Cancels the timer and clears any pending data.
        """
        if self.timer is not None:
            self.timer.cancel()
        self.logger.info("VisualizationPublisher shutdown complete")
