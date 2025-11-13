#!/usr/bin/env python3
"""
Event-Based Vision Processing.

Converts traditional camera frames to event-based representation
for neuromorphic processing.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
import numpy as np


class EventVisionProcessor(Node):
    """
    Convert camera frames to event-based representation.
    
    Events are generated when pixel intensity changes exceed a threshold.
    This mimics biological vision systems and enables ultra-low latency processing.
    """
    
    def __init__(self):
        super().__init__('event_vision')
        
        # Declare parameters
        self.declare_parameters(
            namespace='',
            parameters=[
                ('event_threshold', 15),
                ('temporal_resolution', 0.001),  # 1ms
            ]
        )
        
        # Get parameters
        self.event_threshold = self.get_parameter('event_threshold').value
        self.temporal_resolution = self.get_parameter('temporal_resolution').value
        
        # Previous frame for change detection
        self.prev_frame = None
        
        # Publishers
        self.events_pub = self.create_publisher(String, '/events/output', 10)
        
        # Subscribers
        self.image_sub = self.create_subscription(
            Image, '/camera/image_raw', self.image_callback, 10
        )
        
        self.get_logger().info('Event Vision Processor initialized')
    
    def image_callback(self, msg: Image):
        """Convert image to events"""
        try:
            # Convert ROS Image to numpy array
            frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(
                msg.height, msg.width, -1
            )
            
            # Convert to grayscale if needed
            if frame.shape[2] > 1:
                frame = np.mean(frame, axis=2).astype(np.uint8)
            else:
                frame = frame[:, :, 0]
            
            # Generate events
            if self.prev_frame is not None:
                events = self.generate_events(self.prev_frame, frame)
                self.publish_events(events)
            
            self.prev_frame = frame.copy()
            
        except Exception as e:
            self.get_logger().error(f'Error processing image: {e}')
    
    def generate_events(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> list:
        """
        Generate events from frame difference.
        
        Args:
            prev_frame: Previous frame
            curr_frame: Current frame
            
        Returns:
            List of events (x, y, polarity, timestamp)
        """
        # Compute intensity change
        diff = curr_frame.astype(int) - prev_frame.astype(int)
        
        # Find pixels with significant change
        pos_events = np.where(diff > self.event_threshold)
        neg_events = np.where(diff < -self.event_threshold)
        
        events = []
        timestamp = self.get_clock().now().nanoseconds / 1e9
        
        # Positive events (brightness increase)
        for y, x in zip(pos_events[0], pos_events[1]):
            events.append({
                'x': int(x),
                'y': int(y),
                'polarity': 1,
                'timestamp': timestamp
            })
        
        # Negative events (brightness decrease)
        for y, x in zip(neg_events[0], neg_events[1]):
            events.append({
                'x': int(x),
                'y': int(y),
                'polarity': -1,
                'timestamp': timestamp
            })
        
        return events
    
    def publish_events(self, events: list):
        """Publish events"""
        if not events:
            return
        
        msg = String()
        msg.data = str(events)
        self.events_pub.publish(msg)
        
        self.get_logger().debug(f'Published {len(events)} events')


def main(args=None):
    rclpy.init(args=args)
    node = EventVisionProcessor()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
