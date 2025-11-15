"""
SplatGenerator component for creating Gaussian primitives from sensor data.

This module processes synchronized camera and LiDAR data to generate
GaussianPrimitive objects with position, color, covariance, and opacity.
"""

from typing import List, Tuple, Optional
import numpy as np
from scipy.spatial import KDTree
from sensor_msgs.msg import Image, PointCloud2, CameraInfo
import sensor_msgs_py.point_cloud2 as pc2
from cv_bridge import CvBridge
import cv2

from .data_models import GaussianPrimitive


class SplatGenerator:
    """
    Generates Gaussian Splat primitives from synchronized camera and LiDAR data.
    
    This class processes 3D point clouds and camera images to create GaussianPrimitive
    objects. It computes covariance from local geometry, projects colors from camera
    images, and calculates opacity based on point density.
    """
    
    def __init__(self, camera_info: CameraInfo, neighbor_count: int = 10, 
                 neighbor_radius: float = 0.5):
        """
        Initialize the SplatGenerator.
        
        Args:
            camera_info: ROS CameraInfo message containing camera intrinsics
            neighbor_count: Number of neighbors to use for covariance computation
            neighbor_radius: Maximum radius for neighbor search in meters
        """
        # Store camera intrinsics
        self.camera_matrix = np.array(camera_info.k).reshape(3, 3)
        self.distortion_coeffs = np.array(camera_info.d) if camera_info.d else None
        self.image_width = camera_info.width
        self.image_height = camera_info.height
        
        # Configuration parameters
        self.neighbor_count = neighbor_count
        self.neighbor_radius = neighbor_radius
        
        # Default covariance for cases with insufficient neighbors
        self.default_covariance = np.eye(3) * 0.01  # 1cm standard deviation
        
        # CV Bridge for image conversion
        self.bridge = CvBridge()
        
        # KDTree will be built per point cloud
        self.kdtree: Optional[KDTree] = None
        self.points_array: Optional[np.ndarray] = None
    
    def generate_splats(self, image_msg: Image, pointcloud_msg: PointCloud2, 
                       timestamp: float) -> List[GaussianPrimitive]:
        """
        Generate Gaussian Splat primitives from synchronized sensor data.
        
        This is the main pipeline that coordinates all processing steps:
        1. Convert and validate input data
        2. Filter invalid points (NaN, Inf)
        3. Build spatial index for neighbor searches
        4. Process each valid point into a GaussianPrimitive
        
        Args:
            image_msg: ROS Image message containing camera data
            pointcloud_msg: ROS PointCloud2 message containing LiDAR data
            timestamp: ROS timestamp for the primitives
            
        Returns:
            List of generated GaussianPrimitive objects
        """
        # Convert image to OpenCV format
        try:
            cv_image = self.bridge.imgmsg_to_cv2(image_msg, desired_encoding='rgb8')
        except Exception as e:
            print(f"Error converting image: {e}")
            return []
        
        # Extract points from point cloud
        points_list = []
        for point in pc2.read_points(pointcloud_msg, field_names=("x", "y", "z"), 
                                     skip_nans=True):
            points_list.append([point[0], point[1], point[2]])
        
        if len(points_list) == 0:
            return []
        
        # Convert to numpy array
        self.points_array = np.array(points_list, dtype=np.float64)
        
        # Filter invalid points (NaN, Inf)
        valid_mask = np.all(np.isfinite(self.points_array), axis=1)
        self.points_array = self.points_array[valid_mask]
        
        if len(self.points_array) == 0:
            return []
        
        # Build KDTree for neighbor searches
        self.kdtree = KDTree(self.points_array)
        
        # Generate primitives for each valid point
        primitives = []
        for i, point_3d in enumerate(self.points_array):
            # Project color from camera
            color = self.project_color(point_3d, cv_image)
            if color is None:
                continue  # Point outside camera FOV
            
            # Find neighbors for this point
            neighbors = self.find_neighbors(point_3d, i)
            
            # Compute covariance from local geometry
            covariance = self.compute_covariance(point_3d, neighbors)
            
            # Compute opacity based on local density
            opacity = self.compute_opacity(point_3d, neighbors)
            
            # Create GaussianPrimitive
            primitive = GaussianPrimitive(
                position=point_3d.copy(),
                covariance=covariance,
                color=color,
                opacity=opacity,
                timestamp=timestamp
            )
            primitives.append(primitive)
        
        return primitives
    
    def project_color(self, point_3d: np.ndarray, image: np.ndarray) -> Optional[Tuple[int, int, int]]:
        """
        Project a 3D point to the camera image and extract its color.
        
        Uses camera intrinsics to project the 3D point to 2D image coordinates,
        then samples the color from the image. Handles points outside the camera
        field of view and validates image bounds.
        
        Args:
            point_3d: 3D point in camera frame [x, y, z]
            image: OpenCV image in RGB format
            
        Returns:
            RGB color tuple (r, g, b) or None if point is outside FOV
        """
        # Check if point is in front of camera
        if point_3d[2] <= 0:
            return None
        
        # Project 3D point to 2D using camera matrix
        # P = K * [X, Y, Z]^T where K is camera matrix
        point_homogeneous = point_3d.reshape(3, 1)
        pixel_homogeneous = self.camera_matrix @ point_homogeneous
        
        # Convert from homogeneous coordinates
        u = int(pixel_homogeneous[0, 0] / pixel_homogeneous[2, 0])
        v = int(pixel_homogeneous[1, 0] / pixel_homogeneous[2, 0])
        
        # Validate image bounds
        if u < 0 or u >= self.image_width or v < 0 or v >= self.image_height:
            return None
        
        # Extract color from image
        color = image[v, u]  # Note: image indexing is [row, col] = [y, x]
        return (int(color[0]), int(color[1]), int(color[2]))
    
    def find_neighbors(self, point: np.ndarray, point_index: int) -> np.ndarray:
        """
        Find neighboring points using KDTree spatial search.
        
        Searches for k-nearest neighbors within a specified radius. Excludes
        the query point itself from the results.
        
        Args:
            point: Query point [x, y, z]
            point_index: Index of the query point in the points array
            
        Returns:
            Array of neighbor points with shape (n, 3) where n <= neighbor_count
        """
        if self.kdtree is None or self.points_array is None:
            return np.array([])
        
        # Query k+1 neighbors (including the point itself)
        distances, indices = self.kdtree.query(
            point, 
            k=min(self.neighbor_count + 1, len(self.points_array)),
            distance_upper_bound=self.neighbor_radius
        )
        
        # Handle single neighbor case
        if not isinstance(indices, np.ndarray):
            indices = np.array([indices])
            distances = np.array([distances])
        
        # Filter out the point itself and invalid results
        valid_mask = (indices != point_index) & (indices < len(self.points_array)) & np.isfinite(distances)
        valid_indices = indices[valid_mask]
        
        if len(valid_indices) == 0:
            return np.array([])
        
        # Return neighbor points
        return self.points_array[valid_indices]
    
    def compute_covariance(self, point: np.ndarray, neighbors: np.ndarray) -> np.ndarray:
        """
        Compute covariance matrix from local point cloud geometry using PCA.
        
        The covariance matrix describes the shape and orientation of the Gaussian.
        It is computed from the distribution of neighboring points. If insufficient
        neighbors are available, returns a default isotropic covariance.
        
        Args:
            point: Center point [x, y, z]
            neighbors: Array of neighbor points with shape (n, 3)
            
        Returns:
            3x3 covariance matrix
        """
        # Need at least 3 neighbors for meaningful covariance
        if len(neighbors) < 3:
            return self.default_covariance.copy()
        
        # Center the neighbors around the query point
        centered = neighbors - point
        
        # Compute covariance matrix
        # Cov = (1/n) * X^T * X where X is the centered data matrix
        covariance = np.cov(centered.T)
        
        # Ensure covariance is positive definite by adding small regularization
        # This prevents numerical issues with degenerate configurations
        regularization = 1e-6
        covariance += np.eye(3) * regularization
        
        # Validate that covariance is symmetric and positive definite
        if not np.allclose(covariance, covariance.T):
            covariance = (covariance + covariance.T) / 2
        
        # Check for valid covariance (all eigenvalues positive)
        eigenvalues = np.linalg.eigvalsh(covariance)
        if np.any(eigenvalues <= 0):
            return self.default_covariance.copy()
        
        return covariance
    
    def compute_opacity(self, point: np.ndarray, neighbors: np.ndarray) -> float:
        """
        Calculate opacity based on local point density.
        
        Higher point density indicates more confident measurements and results
        in higher opacity. Opacity is normalized to the range [0.0, 1.0].
        
        Args:
            point: Center point [x, y, z]
            neighbors: Array of neighbor points with shape (n, 3)
            
        Returns:
            Opacity value in range [0.0, 1.0]
        """
        # Base opacity on number of neighbors found
        neighbor_count = len(neighbors)
        
        # Normalize based on expected neighbor count
        # More neighbors = higher confidence = higher opacity
        opacity = min(1.0, neighbor_count / self.neighbor_count)
        
        # Apply minimum opacity threshold to ensure visibility
        min_opacity = 0.3
        opacity = max(min_opacity, opacity)
        
        return opacity
