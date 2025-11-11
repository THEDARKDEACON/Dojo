#!/usr/bin/env python3
"""
CollaborativeMapper: Shared semantic mapping for multi-robot systems

This node manages:
- Sharing semantic map updates between robots
- Merging maps from multiple robots
- Handling map conflicts and inconsistencies
- Maintaining synchronized semantic database
"""

import time
import json
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy

from std_msgs.msg import String
from geometry_msgs.msg import Point
from nav_msgs.msg import OccupancyGrid


@dataclass
class SemanticObject:
    """Semantic object in the shared map."""
    object_id: str
    class_name: str
    position: Tuple[float, float, float]  # (x, y, z)
    confidence: float
    last_seen: float
    detection_count: int
    source_robot: str
    merged_from: List[str] = None  # List of object IDs that were merged


class CollaborativeMapper(Node):
    """
    Collaborative semantic mapping for multi-robot systems.
    
    Features:
    - Share semantic map updates via DDS
    - Merge maps from multiple robots
    - Resolve conflicts using confidence scores
    - Maintain synchronized semantic database
    """
    
    def __init__(self):
        super().__init__('collaborative_mapper')
        
        # Declare parameters
        self.declare_parameter('robot_id', '')
        self.declare_parameter('update_rate', 1.0)  # Hz
        self.declare_parameter('merge_distance_threshold', 1.0)  # meters
        self.declare_parameter('confidence_threshold', 0.5)
        self.declare_parameter('sync_timeout', 0.5)  # seconds
        
        # Get parameters
        self.robot_id = self.get_parameter('robot_id').value
        self.update_rate = self.get_parameter('update_rate').value
        self.merge_distance_threshold = self.get_parameter('merge_distance_threshold').value
        self.confidence_threshold = self.get_parameter('confidence_threshold').value
        self.sync_timeout = self.get_parameter('sync_timeout').value
        
        # Semantic map database
        self.semantic_objects: Dict[str, SemanticObject] = {}
        self.local_objects: Dict[str, SemanticObject] = {}  # Objects detected by this robot
        
        # Synchronization tracking
        self.last_sync_time = time.time()
        self.pending_updates: List[dict] = []
        
        # QoS profile for map sharing (reliable, transient local)
        map_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=100,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )
        
        # Publishers
        self.map_update_pub = self.create_publisher(
            String,
            '/swarm/map_updates',
            map_qos
        )
        
        self.merged_map_pub = self.create_publisher(
            String,
            f'/{self.robot_id}/merged_semantic_map',
            10
        )
        
        # Subscribers
        self.map_update_sub = self.create_subscription(
            String,
            '/swarm/map_updates',
            self.map_update_callback,
            map_qos
        )
        
        self.local_map_sub = self.create_subscription(
            String,
            f'/{self.robot_id}/semantic_map',
            self.local_map_callback,
            10
        )
        
        # Timers
        self.update_timer = self.create_timer(
            1.0 / self.update_rate,
            self.publish_map_updates
        )
        
        self.merge_timer = self.create_timer(
            0.5,
            self.merge_maps
        )
        
        self.get_logger().info(f'CollaborativeMapper initialized for {self.robot_id}')
    
    def local_map_callback(self, msg: String):
        """Process local semantic map updates."""
        try:
            data = json.loads(msg.data)
            
            # Update local objects
            for obj_data in data.get('objects', []):
                obj_id = obj_data['object_id']
                
                # Create or update semantic object
                if obj_id not in self.local_objects:
                    self.local_objects[obj_id] = SemanticObject(
                        object_id=obj_id,
                        class_name=obj_data['class_name'],
                        position=tuple(obj_data['position']),
                        confidence=obj_data['confidence'],
                        last_seen=time.time(),
                        detection_count=1,
                        source_robot=self.robot_id
                    )
                else:
                    # Update existing object
                    obj = self.local_objects[obj_id]
                    obj.position = tuple(obj_data['position'])
                    obj.confidence = obj_data['confidence']
                    obj.last_seen = time.time()
                    obj.detection_count += 1
                
                # Add to pending updates for sharing
                self.pending_updates.append({
                    'robot_id': self.robot_id,
                    'object': asdict(self.local_objects[obj_id]),
                    'timestamp': time.time()
                })
                
        except Exception as e:
            self.get_logger().error(f'Error processing local map: {e}')
    
    def map_update_callback(self, msg: String):
        """Process map updates from other robots."""
        try:
            data = json.loads(msg.data)
            
            # Ignore own updates
            if data.get('robot_id') == self.robot_id:
                return
            
            # Process object update
            obj_data = data.get('object')
            if obj_data:
                self.integrate_remote_object(obj_data)
            
            # Track sync latency
            update_time = data.get('timestamp', 0)
            latency = time.time() - update_time
            
            if latency > self.sync_timeout:
                self.get_logger().warn(
                    f'High map sync latency: {latency*1000:.0f}ms from {data.get("robot_id")}'
                )
                
        except Exception as e:
            self.get_logger().error(f'Error processing map update: {e}')
    
    def integrate_remote_object(self, obj_data: dict):
        """
        Integrate an object from another robot's map.
        
        Handles:
        - New objects
        - Updates to existing objects
        - Merging nearby objects
        - Conflict resolution
        """
        remote_obj = SemanticObject(**obj_data)
        obj_id = remote_obj.object_id
        
        # Check if this is a new object or update
        if obj_id in self.semantic_objects:
            # Update existing object
            existing_obj = self.semantic_objects[obj_id]
            
            # Use higher confidence version
            if remote_obj.confidence > existing_obj.confidence:
                existing_obj.position = remote_obj.position
                existing_obj.confidence = remote_obj.confidence
                existing_obj.last_seen = remote_obj.last_seen
                existing_obj.detection_count = max(
                    existing_obj.detection_count,
                    remote_obj.detection_count
                )
        else:
            # Check if this object should be merged with nearby objects
            merged = False
            for existing_id, existing_obj in self.semantic_objects.items():
                if existing_obj.class_name == remote_obj.class_name:
                    distance = self.calculate_distance(
                        existing_obj.position,
                        remote_obj.position
                    )
                    
                    if distance < self.merge_distance_threshold:
                        # Merge objects
                        self.merge_objects(existing_obj, remote_obj)
                        merged = True
                        break
            
            if not merged:
                # Add as new object
                self.semantic_objects[obj_id] = remote_obj
                self.get_logger().info(
                    f'Added new object from {remote_obj.source_robot}: '
                    f'{remote_obj.class_name} at {remote_obj.position}'
                )
    
    def merge_objects(self, obj1: SemanticObject, obj2: SemanticObject):
        """
        Merge two nearby objects of the same class.
        
        Uses weighted average based on confidence scores.
        """
        # Calculate weighted position
        total_confidence = obj1.confidence + obj2.confidence
        weight1 = obj1.confidence / total_confidence
        weight2 = obj2.confidence / total_confidence
        
        merged_position = (
            obj1.position[0] * weight1 + obj2.position[0] * weight2,
            obj1.position[1] * weight1 + obj2.position[1] * weight2,
            obj1.position[2] * weight1 + obj2.position[2] * weight2
        )
        
        # Update object 1 with merged data
        obj1.position = merged_position
        obj1.confidence = max(obj1.confidence, obj2.confidence)
        obj1.detection_count += obj2.detection_count
        obj1.last_seen = max(obj1.last_seen, obj2.last_seen)
        
        # Track merge history
        if obj1.merged_from is None:
            obj1.merged_from = []
        obj1.merged_from.append(obj2.object_id)
        
        self.get_logger().info(
            f'Merged objects: {obj1.object_id} and {obj2.object_id} '
            f'({obj1.class_name})'
        )
    
    def publish_map_updates(self):
        """Publish pending map updates to swarm."""
        if not self.pending_updates:
            return
        
        # Publish each pending update
        for update in self.pending_updates:
            msg = String()
            msg.data = json.dumps(update)
            self.map_update_pub.publish(msg)
        
        # Clear pending updates
        self.pending_updates.clear()
        self.last_sync_time = time.time()
    
    def merge_maps(self):
        """Merge local and remote objects into unified map."""
        # Combine local and semantic objects
        merged_map = {}
        
        # Add all semantic objects (from all robots)
        for obj_id, obj in self.semantic_objects.items():
            if obj.confidence >= self.confidence_threshold:
                merged_map[obj_id] = obj
        
        # Add local objects (may override if higher confidence)
        for obj_id, obj in self.local_objects.items():
            if obj.confidence >= self.confidence_threshold:
                if obj_id not in merged_map or obj.confidence > merged_map[obj_id].confidence:
                    merged_map[obj_id] = obj
        
        # Publish merged map
        self.publish_merged_map(merged_map)
    
    def publish_merged_map(self, merged_map: Dict[str, SemanticObject]):
        """Publish the merged semantic map."""
        map_data = {
            'robot_id': self.robot_id,
            'timestamp': time.time(),
            'num_objects': len(merged_map),
            'objects': [
                {
                    'object_id': obj.object_id,
                    'class_name': obj.class_name,
                    'position': obj.position,
                    'confidence': obj.confidence,
                    'last_seen': obj.last_seen,
                    'detection_count': obj.detection_count,
                    'source_robot': obj.source_robot
                }
                for obj in merged_map.values()
            ]
        }
        
        msg = String()
        msg.data = json.dumps(map_data)
        self.merged_map_pub.publish(msg)
    
    def calculate_distance(self, pos1: Tuple[float, float, float], 
                          pos2: Tuple[float, float, float]) -> float:
        """Calculate 3D Euclidean distance between two positions."""
        return np.sqrt(
            (pos1[0] - pos2[0])**2 +
            (pos1[1] - pos2[1])**2 +
            (pos1[2] - pos2[2])**2
        )
    
    def get_map_statistics(self) -> dict:
        """Get statistics about the collaborative map."""
        return {
            'robot_id': self.robot_id,
            'total_objects': len(self.semantic_objects),
            'local_objects': len(self.local_objects),
            'last_sync_time': self.last_sync_time,
            'sync_latency': time.time() - self.last_sync_time,
            'objects_by_class': self.count_objects_by_class()
        }
    
    def count_objects_by_class(self) -> Dict[str, int]:
        """Count objects by class name."""
        counts = {}
        for obj in self.semantic_objects.values():
            counts[obj.class_name] = counts.get(obj.class_name, 0) + 1
        return counts


def main(args=None):
    """Main function."""
    rclpy.init(args=args)
    
    try:
        node = CollaborativeMapper()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
