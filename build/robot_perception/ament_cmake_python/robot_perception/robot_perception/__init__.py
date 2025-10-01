"""
Robot Perception Package

This package provides computer vision and object detection capabilities
for the Dojo Robot platform.

Modules:
    camera_processor: Basic image processing and object detection
    object_detector: Advanced object detection using ML models
"""

__version__ = "0.1.0"
__author__ = "Dojo Robot Team"

# Import main classes for easier access
from .nodes.camera_processor import CameraProcessor
from .nodes.object_detector import ObjectDetector

__all__ = ['CameraProcessor', 'ObjectDetector']