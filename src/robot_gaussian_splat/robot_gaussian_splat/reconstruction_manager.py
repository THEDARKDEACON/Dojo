"""
ReconstructionManager component for managing Gaussian Splat reconstruction.

This module manages the accumulation of Gaussian primitives, spatial indexing,
downsampling, and export functionality for the reconstruction model.
"""

import threading
import json
import logging
from typing import List, Dict, Optional
import numpy as np
try:
    from plyfile import PlyData, PlyElement
    PLYFILE_AVAILABLE = True
except ImportError:
    PLYFILE_AVAILABLE = False
    PlyData = None
    PlyElement = None

from .data_models import GaussianPrimitive, SplatModel


class ReconstructionManager:
    """
    Manages the Gaussian Splat reconstruction pipeline and output storage.
    
    This class maintains a persistent collection of Gaussian primitives throughout
    the mapping session, provides spatial indexing for efficient queries, applies
    downsampling when memory limits are reached, and handles model export operations.
    """
    
    def __init__(self, max_primitives: int = 1000000):
        """
        Initialize the ReconstructionManager.
        
        Args:
            max_primitives: Maximum number of primitives before triggering downsampling
        """
        self.max_primitives = max_primitives
        self.model = SplatModel()
        self.lock = threading.Lock()
        
        # Set up logging
        self.logger = logging.getLogger('ReconstructionManager')
        self.logger.setLevel(logging.INFO)
        
        # Statistics tracking
        self.total_primitives_added = 0
        self.downsample_count = 0

    def add_primitives(self, primitives: List[GaussianPrimitive]):
        """
        Add new Gaussian primitives to the reconstruction model.
        
        This method is thread-safe and updates the octree spatial index when
        adding primitives. If the primitive count exceeds max_primitives,
        automatic downsampling is triggered.
        
        Args:
            primitives: List of GaussianPrimitive objects to add
        """
        with self.lock:
            # Add each primitive to the model
            for primitive in primitives:
                self.model.add_primitive(primitive)
                self.total_primitives_added += 1
            
            # Check if downsampling is needed
            if self.model.get_primitive_count() > self.max_primitives:
                self.logger.warning(
                    f"Primitive count ({self.model.get_primitive_count()}) "
                    f"exceeds maximum ({self.max_primitives}). Triggering downsampling."
                )
                self.downsample()

    def downsample(self):
        """
        Apply voxel grid filtering to reduce the number of primitives.
        
        This method uses adaptive voxel size based on scene bounds to downsample
        the reconstruction when the primitive count exceeds the maximum limit.
        Primitives within the same voxel are merged by averaging their properties.
        
        Note: This method assumes the lock is already held by the caller.
        """
        current_count = self.model.get_primitive_count()
        if current_count == 0:
            return
        
        self.logger.info(f"Starting downsampling with {current_count} primitives")
        
        # Get scene bounds
        bounds_min, bounds_max = self.model.get_bounds()
        if bounds_min is None or bounds_max is None:
            self.logger.warning("Cannot downsample: no bounds available")
            return
        
        # Calculate adaptive voxel size
        # Target: reduce to approximately 80% of max_primitives
        target_count = int(self.max_primitives * 0.8)
        scene_volume = np.prod(bounds_max - bounds_min)
        voxel_volume = scene_volume / target_count
        voxel_size = np.cbrt(voxel_volume)
        
        # Ensure minimum voxel size
        voxel_size = max(voxel_size, 0.01)  # At least 1cm
        
        self.logger.info(f"Using voxel size: {voxel_size:.4f} meters")
        
        # Create voxel grid
        voxel_grid: Dict[tuple, List[GaussianPrimitive]] = {}
        
        # Assign primitives to voxels
        for primitive in self.model.primitives:
            # Compute voxel index
            voxel_idx = tuple(
                int(np.floor((primitive.position[i] - bounds_min[i]) / voxel_size))
                for i in range(3)
            )
            
            if voxel_idx not in voxel_grid:
                voxel_grid[voxel_idx] = []
            voxel_grid[voxel_idx].append(primitive)
        
        # Merge primitives within each voxel
        downsampled_primitives = []
        for voxel_primitives in voxel_grid.values():
            if len(voxel_primitives) == 1:
                # Keep single primitive as-is
                downsampled_primitives.append(voxel_primitives[0])
            else:
                # Merge multiple primitives by averaging
                merged = self._merge_primitives(voxel_primitives)
                downsampled_primitives.append(merged)
        
        # Replace model with downsampled version
        self.model.clear()
        for primitive in downsampled_primitives:
            self.model.add_primitive(primitive)
        
        self.downsample_count += 1
        new_count = self.model.get_primitive_count()
        reduction_percent = (1 - new_count / current_count) * 100
        
        self.logger.info(
            f"Downsampling complete: {current_count} -> {new_count} primitives "
            f"({reduction_percent:.1f}% reduction)"
        )
    
    def _merge_primitives(self, primitives: List[GaussianPrimitive]) -> GaussianPrimitive:
        """
        Merge multiple primitives by averaging their properties.
        
        Args:
            primitives: List of primitives to merge
            
        Returns:
            Merged GaussianPrimitive
        """
        n = len(primitives)
        
        # Average position
        avg_position = np.mean([p.position for p in primitives], axis=0)
        
        # Average covariance
        avg_covariance = np.mean([p.covariance for p in primitives], axis=0)
        
        # Average color (convert to float, average, convert back to int)
        avg_color_float = np.mean([np.array(p.color) for p in primitives], axis=0)
        avg_color = tuple(int(c) for c in avg_color_float)
        
        # Average opacity
        avg_opacity = np.mean([p.opacity for p in primitives])
        
        # Use most recent timestamp
        latest_timestamp = max(p.timestamp for p in primitives)
        
        return GaussianPrimitive(
            position=avg_position,
            covariance=avg_covariance,
            color=avg_color,
            opacity=float(avg_opacity),
            timestamp=latest_timestamp
        )

    def export_ply(self, filepath: str) -> bool:
        """
        Export the reconstruction model to PLY format.
        
        The PLY file includes position, color, covariance, and opacity for each
        Gaussian primitive. This format is compatible with standard 3D visualization
        tools and Gaussian Splatting viewers.
        
        Args:
            filepath: Output file path (should end with .ply)
            
        Returns:
            True if export succeeded, False otherwise
        """
        with self.lock:
            try:
                primitives = self.model.get_all_primitives()
                
                if len(primitives) == 0:
                    self.logger.warning("Cannot export empty model")
                    return False
                
                self.logger.info(f"Exporting {len(primitives)} primitives to PLY: {filepath}")
                
                # Prepare vertex data
                vertex_data = []
                for primitive in primitives:
                    # Extract data
                    x, y, z = primitive.position
                    r, g, b = primitive.color
                    opacity = primitive.opacity
                    
                    # Extract covariance elements (symmetric matrix)
                    cov_xx = primitive.covariance[0, 0]
                    cov_yy = primitive.covariance[1, 1]
                    cov_zz = primitive.covariance[2, 2]
                    cov_xy = primitive.covariance[0, 1]
                    cov_xz = primitive.covariance[0, 2]
                    cov_yz = primitive.covariance[1, 2]
                    
                    vertex_data.append((
                        x, y, z,
                        r, g, b,
                        opacity,
                        cov_xx, cov_yy, cov_zz, cov_xy, cov_xz, cov_yz
                    ))
                
                # Define PLY vertex structure
                vertex_dtype = [
                    ('x', 'f4'), ('y', 'f4'), ('z', 'f4'),
                    ('red', 'u1'), ('green', 'u1'), ('blue', 'u1'),
                    ('opacity', 'f4'),
                    ('cov_xx', 'f4'), ('cov_yy', 'f4'), ('cov_zz', 'f4'),
                    ('cov_xy', 'f4'), ('cov_xz', 'f4'), ('cov_yz', 'f4')
                ]
                
                # Create structured array
                vertex_array = np.array(vertex_data, dtype=vertex_dtype)
                
                # Create PLY element
                if not PLYFILE_AVAILABLE:
                    raise ImportError("plyfile module not available. Install with: pip install plyfile")
                vertex_element = PlyElement.describe(vertex_array, 'vertex')
                
                # Write PLY file
                PlyData([vertex_element], text=False).write(filepath)
                
                self.logger.info(f"Successfully exported to {filepath}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error exporting PLY: {e}")
                return False

    def export_json(self, filepath: str) -> bool:
        """
        Export the reconstruction model to JSON format.
        
        The JSON file includes complete primitive parameters with numpy arrays
        serialized to lists. This format preserves all data and metadata for
        later reconstruction or analysis.
        
        Args:
            filepath: Output file path (should end with .json)
            
        Returns:
            True if export succeeded, False otherwise
        """
        with self.lock:
            try:
                primitives = self.model.get_all_primitives()
                
                if len(primitives) == 0:
                    self.logger.warning("Cannot export empty model")
                    return False
                
                self.logger.info(f"Exporting {len(primitives)} primitives to JSON: {filepath}")
                
                # Prepare export data
                export_data = {
                    'metadata': {
                        'creation_time': self.model.metadata['creation_time'],
                        'total_frames_processed': self.model.metadata['total_frames_processed'],
                        'primitive_count': len(primitives),
                        'total_primitives_added': self.total_primitives_added,
                        'downsample_count': self.downsample_count,
                        'bounds_min': (self.model.metadata['bounds_min'].tolist() 
                                      if self.model.metadata['bounds_min'] is not None else None),
                        'bounds_max': (self.model.metadata['bounds_max'].tolist() 
                                      if self.model.metadata['bounds_max'] is not None else None)
                    },
                    'primitives': [primitive.to_dict() for primitive in primitives]
                }
                
                # Write JSON file
                with open(filepath, 'w') as f:
                    json.dump(export_data, f, indent=2)
                
                self.logger.info(f"Successfully exported to {filepath}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error exporting JSON: {e}")
                return False

    def get_primitive_count(self) -> int:
        """
        Get the current number of primitives in the model.
        
        Returns:
            Number of primitives
        """
        with self.lock:
            return self.model.get_primitive_count()
    
    def get_primitives_for_visualization(self, limit: int) -> List[GaussianPrimitive]:
        """
        Get a limited subset of primitives for visualization.
        
        If the model contains more primitives than the limit, uniformly samples
        primitives to stay within the limit. This prevents overwhelming the
        visualization system with too many markers.
        
        Args:
            limit: Maximum number of primitives to return
            
        Returns:
            List of GaussianPrimitive objects (up to limit)
        """
        with self.lock:
            primitives = self.model.get_all_primitives()
            
            if len(primitives) <= limit:
                return primitives
            
            # Uniformly sample primitives
            indices = np.linspace(0, len(primitives) - 1, limit, dtype=int)
            return [primitives[i] for i in indices]
    
    def clear(self):
        """
        Clear all primitives and reset the reconstruction model.
        
        This resets the model to an empty state, ready for a new reconstruction.
        Statistics counters are also reset.
        """
        with self.lock:
            self.model.clear()
            self.total_primitives_added = 0
            self.downsample_count = 0
            self.logger.info("Reconstruction model cleared")
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about the current reconstruction model.
        
        Returns:
            Dictionary containing model statistics including:
            - primitive_count: Current number of primitives
            - total_primitives_added: Total primitives added (before downsampling)
            - downsample_count: Number of times downsampling was applied
            - memory_usage_mb: Estimated memory usage in megabytes
            - bounds_min: Minimum corner of bounding box
            - bounds_max: Maximum corner of bounding box
            - frames_processed: Number of frames processed
        """
        with self.lock:
            primitive_count = self.model.get_primitive_count()
            bounds_min, bounds_max = self.model.get_bounds()
            
            # Estimate memory usage
            # Each primitive: 3 floats (position) + 9 floats (covariance) + 
            #                 3 ints (color) + 1 float (opacity) + 1 float (timestamp)
            # Approximate: 17 * 4 bytes = 68 bytes per primitive
            bytes_per_primitive = 68
            memory_usage_bytes = primitive_count * bytes_per_primitive
            memory_usage_mb = memory_usage_bytes / (1024 * 1024)
            
            return {
                'primitive_count': primitive_count,
                'total_primitives_added': self.total_primitives_added,
                'downsample_count': self.downsample_count,
                'memory_usage_mb': memory_usage_mb,
                'bounds_min': bounds_min.tolist() if bounds_min is not None else None,
                'bounds_max': bounds_max.tolist() if bounds_max is not None else None,
                'frames_processed': self.model.metadata['total_frames_processed']
            }
