"""
Data models for Gaussian Splatting reconstruction.

This module defines the core data structures used in the Gaussian Splatting
reconstruction system, including GaussianPrimitive and SplatModel.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import numpy as np
import struct
import time


@dataclass
class GaussianPrimitive:
    """
    Represents a single 3D Gaussian primitive.
    
    A Gaussian primitive is defined by its position in 3D space, a covariance
    matrix describing its shape, RGB color, opacity, and creation timestamp.
    
    Attributes:
        position: 3D position [x, y, z] in meters
        covariance: 3x3 covariance matrix describing the Gaussian shape
        color: RGB color values in range [0-255]
        opacity: Opacity value in range [0.0-1.0]
        timestamp: ROS time when the primitive was created
    """
    position: np.ndarray  # Shape: (3,)
    covariance: np.ndarray  # Shape: (3, 3)
    color: Tuple[int, int, int]  # RGB [0-255]
    opacity: float  # [0.0-1.0]
    timestamp: float  # ROS time
    
    def __post_init__(self):
        """Validate data types and shapes after initialization."""
        # Ensure position is a numpy array with shape (3,)
        if not isinstance(self.position, np.ndarray):
            self.position = np.array(self.position, dtype=np.float64)
        assert self.position.shape == (3,), f"Position must have shape (3,), got {self.position.shape}"
        
        # Ensure covariance is a numpy array with shape (3, 3)
        if not isinstance(self.covariance, np.ndarray):
            self.covariance = np.array(self.covariance, dtype=np.float64)
        assert self.covariance.shape == (3, 3), f"Covariance must have shape (3, 3), got {self.covariance.shape}"
        
        # Validate color tuple
        assert len(self.color) == 3, "Color must be a tuple of 3 values"
        assert all(0 <= c <= 255 for c in self.color), "Color values must be in range [0-255]"
        
        # Validate opacity
        assert 0.0 <= self.opacity <= 1.0, f"Opacity must be in range [0.0-1.0], got {self.opacity}"
    
    def to_dict(self) -> Dict:
        """
        Serialize the GaussianPrimitive to a dictionary.
        
        Returns:
            Dictionary containing all primitive attributes with numpy arrays
            converted to lists for JSON serialization.
        """
        return {
            'position': self.position.tolist(),
            'covariance': self.covariance.tolist(),
            'color': list(self.color),
            'opacity': float(self.opacity),
            'timestamp': float(self.timestamp)
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GaussianPrimitive':
        """
        Deserialize a GaussianPrimitive from a dictionary.
        
        Args:
            data: Dictionary containing primitive attributes
            
        Returns:
            GaussianPrimitive instance
        """
        return cls(
            position=np.array(data['position'], dtype=np.float64),
            covariance=np.array(data['covariance'], dtype=np.float64),
            color=tuple(data['color']),
            opacity=float(data['opacity']),
            timestamp=float(data['timestamp'])
        )
    
    def to_ply_vertex(self) -> bytes:
        """
        Convert the GaussianPrimitive to PLY vertex format.
        
        The PLY format stores position (x, y, z), color (r, g, b), opacity,
        and the 6 unique elements of the symmetric covariance matrix
        (cov_xx, cov_yy, cov_zz, cov_xy, cov_xz, cov_yz).
        
        Returns:
            Binary data representing the vertex in PLY format
        """
        # Extract position
        x, y, z = self.position
        
        # Extract color
        r, g, b = self.color
        
        # Extract unique covariance elements (symmetric matrix)
        cov_xx = self.covariance[0, 0]
        cov_yy = self.covariance[1, 1]
        cov_zz = self.covariance[2, 2]
        cov_xy = self.covariance[0, 1]
        cov_xz = self.covariance[0, 2]
        cov_yz = self.covariance[1, 2]
        
        # Pack as binary: 3 floats (position) + 3 bytes (color) + 1 float (opacity) + 6 floats (covariance)
        # Format: fff BBB f ffffff
        vertex_data = struct.pack(
            'fffBBBfffffff',
            x, y, z,  # position
            r, g, b,  # color
            self.opacity,  # opacity
            cov_xx, cov_yy, cov_zz, cov_xy, cov_xz, cov_yz  # covariance
        )
        
        return vertex_data



class OctreeNode:
    """
    A node in the octree spatial index.
    
    Each node represents a cubic region of space and can contain primitives
    or subdivide into 8 child nodes for finer spatial resolution.
    """
    def __init__(self, center: np.ndarray, size: float, max_depth: int, current_depth: int = 0):
        """
        Initialize an octree node.
        
        Args:
            center: Center point of the node's bounding box
            size: Size of the node's bounding box (edge length)
            max_depth: Maximum depth of the octree
            current_depth: Current depth of this node
        """
        self.center = center
        self.size = size
        self.max_depth = max_depth
        self.current_depth = current_depth
        self.primitives: List[GaussianPrimitive] = []
        self.children: Optional[List['OctreeNode']] = None
        self.max_primitives_per_node = 100  # Threshold for subdivision
    
    def insert(self, primitive: GaussianPrimitive):
        """
        Insert a primitive into the octree.
        
        Args:
            primitive: GaussianPrimitive to insert
        """
        # If we have children, insert into appropriate child
        if self.children is not None:
            child_idx = self._get_child_index(primitive.position)
            self.children[child_idx].insert(primitive)
            return
        
        # Add to this node
        self.primitives.append(primitive)
        
        # Subdivide if we exceed capacity and haven't reached max depth
        if len(self.primitives) > self.max_primitives_per_node and self.current_depth < self.max_depth:
            self._subdivide()
    
    def _get_child_index(self, position: np.ndarray) -> int:
        """
        Determine which child octant a position belongs to.
        
        Args:
            position: 3D position
            
        Returns:
            Child index (0-7)
        """
        idx = 0
        if position[0] > self.center[0]:
            idx |= 1
        if position[1] > self.center[1]:
            idx |= 2
        if position[2] > self.center[2]:
            idx |= 4
        return idx
    
    def _subdivide(self):
        """Subdivide this node into 8 children and redistribute primitives."""
        self.children = []
        half_size = self.size / 2
        quarter_size = self.size / 4
        
        # Create 8 child nodes
        for i in range(8):
            offset = np.array([
                quarter_size if i & 1 else -quarter_size,
                quarter_size if i & 2 else -quarter_size,
                quarter_size if i & 4 else -quarter_size
            ])
            child_center = self.center + offset
            child = OctreeNode(
                child_center,
                half_size,
                self.max_depth,
                self.current_depth + 1
            )
            self.children.append(child)
        
        # Redistribute primitives to children
        for primitive in self.primitives:
            child_idx = self._get_child_index(primitive.position)
            self.children[child_idx].primitives.append(primitive)
        
        # Clear primitives from this node
        self.primitives = []
    
    def query_region(self, min_point: np.ndarray, max_point: np.ndarray) -> List[GaussianPrimitive]:
        """
        Query all primitives within a bounding box region.
        
        Args:
            min_point: Minimum corner of the query region
            max_point: Maximum corner of the query region
            
        Returns:
            List of primitives within the region
        """
        # Check if this node intersects the query region
        node_min = self.center - self.size / 2
        node_max = self.center + self.size / 2
        
        if not self._boxes_intersect(node_min, node_max, min_point, max_point):
            return []
        
        results = []
        
        # If we have children, query them
        if self.children is not None:
            for child in self.children:
                results.extend(child.query_region(min_point, max_point))
        else:
            # Check primitives in this node
            for primitive in self.primitives:
                if self._point_in_box(primitive.position, min_point, max_point):
                    results.append(primitive)
        
        return results
    
    @staticmethod
    def _boxes_intersect(min1: np.ndarray, max1: np.ndarray, 
                         min2: np.ndarray, max2: np.ndarray) -> bool:
        """Check if two axis-aligned bounding boxes intersect."""
        return (min1[0] <= max2[0] and max1[0] >= min2[0] and
                min1[1] <= max2[1] and max1[1] >= min2[1] and
                min1[2] <= max2[2] and max1[2] >= min2[2])
    
    @staticmethod
    def _point_in_box(point: np.ndarray, min_point: np.ndarray, max_point: np.ndarray) -> bool:
        """Check if a point is inside an axis-aligned bounding box."""
        return (min_point[0] <= point[0] <= max_point[0] and
                min_point[1] <= point[1] <= max_point[1] and
                min_point[2] <= point[2] <= max_point[2])
    
    def get_all_primitives(self) -> List[GaussianPrimitive]:
        """
        Get all primitives in this node and its children.
        
        Returns:
            List of all primitives
        """
        if self.children is not None:
            results = []
            for child in self.children:
                results.extend(child.get_all_primitives())
            return results
        else:
            return self.primitives.copy()


class SplatModel:
    """
    Container for the complete Gaussian Splat reconstruction.
    
    Manages a collection of GaussianPrimitives with spatial indexing via octree
    for efficient queries and metadata tracking.
    """
    
    def __init__(self, max_depth: int = 10):
        """
        Initialize an empty SplatModel.
        
        Args:
            max_depth: Maximum depth of the octree spatial index
        """
        self.primitives: List[GaussianPrimitive] = []
        self.octree: Optional[OctreeNode] = None
        self.max_depth = max_depth
        self.metadata: Dict = {
            'creation_time': time.time(),
            'total_frames_processed': 0,
            'bounds_min': None,
            'bounds_max': None
        }
    
    def add_primitive(self, primitive: GaussianPrimitive):
        """
        Add a single primitive to the model.
        
        Args:
            primitive: GaussianPrimitive to add
        """
        self.primitives.append(primitive)
        
        # Initialize or update octree
        if self.octree is None:
            # Initialize octree with first primitive
            self._initialize_octree(primitive.position)
        
        # Insert into octree
        self.octree.insert(primitive)
        
        # Update bounds
        self._update_bounds(primitive.position)
    
    def _initialize_octree(self, first_position: np.ndarray):
        """
        Initialize the octree with appropriate bounds.
        
        Args:
            first_position: Position of the first primitive
        """
        # Start with a reasonable size centered at the first point
        initial_size = 100.0  # 100 meters
        self.octree = OctreeNode(
            center=first_position.copy(),
            size=initial_size,
            max_depth=self.max_depth
        )
    
    def _update_bounds(self, position: np.ndarray):
        """
        Update the model's bounding box.
        
        Args:
            position: Position to include in bounds
        """
        if self.metadata['bounds_min'] is None:
            self.metadata['bounds_min'] = position.copy()
            self.metadata['bounds_max'] = position.copy()
        else:
            self.metadata['bounds_min'] = np.minimum(self.metadata['bounds_min'], position)
            self.metadata['bounds_max'] = np.maximum(self.metadata['bounds_max'], position)
    
    def get_bounds(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Get the bounding box of all primitives in the model.
        
        Returns:
            Tuple of (min_point, max_point) or (None, None) if model is empty
        """
        return (self.metadata['bounds_min'], self.metadata['bounds_max'])
    
    def query_region(self, min_point: np.ndarray, max_point: np.ndarray) -> List[GaussianPrimitive]:
        """
        Query all primitives within a bounding box region.
        
        Args:
            min_point: Minimum corner of the query region [x, y, z]
            max_point: Maximum corner of the query region [x, y, z]
            
        Returns:
            List of primitives within the specified region
        """
        if self.octree is None:
            return []
        
        return self.octree.query_region(min_point, max_point)
    
    def get_primitive_count(self) -> int:
        """
        Get the total number of primitives in the model.
        
        Returns:
            Number of primitives
        """
        return len(self.primitives)
    
    def clear(self):
        """Clear all primitives and reset the model."""
        self.primitives = []
        self.octree = None
        self.metadata = {
            'creation_time': time.time(),
            'total_frames_processed': 0,
            'bounds_min': None,
            'bounds_max': None
        }
    
    def get_all_primitives(self) -> List[GaussianPrimitive]:
        """
        Get all primitives in the model.
        
        Returns:
            List of all GaussianPrimitives
        """
        return self.primitives.copy()
