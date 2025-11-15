"""
Gaussian Splatting 3D Reconstruction Package

This package provides ROS2 nodes and utilities for generating 3D Gaussian Splat
reconstructions from synchronized camera and LiDAR sensor data.

Components:
- GaussianSplattingNode: Main ROS2 node for reconstruction
- SplatGenerator: Generates Gaussian primitives from sensor data
- ReconstructionManager: Manages reconstruction model and exports
- SensorSynchronizer: Synchronizes camera and LiDAR data streams
- VisualizationPublisher: Publishes RViz visualization markers
"""

__version__ = '1.0.0'
__author__ = 'Robot Team'
__license__ = 'MIT'

# Package-level imports
from .data_models import GaussianPrimitive, SplatModel, OctreeNode
from .splat_generator import SplatGenerator
from .reconstruction_manager import ReconstructionManager
from .sensor_synchronizer import SensorSynchronizer
from .visualization_publisher import VisualizationPublisher
from .gaussian_splatting_node import GaussianSplattingNode

__all__ = [
    'GaussianPrimitive', 
    'SplatModel', 
    'OctreeNode', 
    'SplatGenerator', 
    'ReconstructionManager',
    'SensorSynchronizer',
    'VisualizationPublisher',
    'GaussianSplattingNode'
]
