#!/usr/bin/env python3
"""
Resource Manager Module

Provides dynamic resource management for the robot vision detection pipeline,
including automatic frame rate throttling, memory cleanup, and graceful degradation.
"""

import time
import gc
import threading
from typing import Optional, Dict, Any
from dataclasses import dataclass
from collections import deque
import rclpy
from rclpy.node import Node


@dataclass
class ResourceLimits:
    """Container for resource limit configuration."""
    max_cpu_percent: float = 80.0
    max_memory_mb: float = 500.0
    min_fps: float = 5.0
    max_fps: float = 30.0
    memory_cleanup_threshold: float = 0.8  # Trigger cleanup at 80% of limit


class ResourceManager:
    """
    Dynamic resource management system for object detection pipeline.
    
    Implements automatic frame rate throttling based on system load,
    memory cleanup for image buffers to prevent leaks, and graceful
    degradation when resource limits are exceeded.
    """
    
    def __init__(self, node: Node, limits: Optional[ResourceLimits] = None):
        """
        Initialize resource manager.
        
        Args:
            node: ROS2 node for logging
            limits: Resource limits configuration
        """
        self.node = node
        self.limits = limits or ResourceLimits()
        
        # Current resource state
        self.current_fps_limit = self.limits.max_fps
        self.throttling_active = False
        self.degradation_level = 0  # 0=normal, 1=light, 2=moderate, 3=severe
        
        # Frame timing control
        self.last_frame_time = 0.0
        self.frame_interval = 1.0 / self.limits.max_fps
        
        # Memory management
        self.image_buffer_cache = deque(maxlen=10)  # Cache for reusable buffers
        self.last_gc_time = time.time()
        self.gc_interval = 30.0  # Run garbage collection every 30 seconds
        
        # Performance tracking for adaptive behavior
        self.performance_history = deque(maxlen=50)  # Last 50 performance samples
        self.adaptation_lock = threading.Lock()
        
        # Resource management timer
        self.management_timer = node.create_timer(
            2.0,  # Check every 2 seconds
            self._manage_resources
        )
        
        self.node.get_logger().info(
            f'Resource Manager initialized - Max CPU: {self.limits.max_cpu_percent}%, '
            f'Max Memory: {self.limits.max_memory_mb}MB, FPS range: {self.limits.min_fps}-{self.limits.max_fps}'
        )
    
    def should_process_frame(self) -> bool:
        """
        Determine if the current frame should be processed based on throttling.
        
        Returns:
            True if frame should be processed, False if it should be skipped
        """
        current_time = time.time()
        
        # Check if enough time has passed since last frame
        if current_time - self.last_frame_time < self.frame_interval:
            return False
        
        self.last_frame_time = current_time
        return True
    
    def get_current_fps_limit(self) -> float:
        """
        Get the current FPS limit based on resource management.
        
        Returns:
            Current FPS limit
        """
        return self.current_fps_limit
    
    def is_throttling_active(self) -> bool:
        """
        Check if frame rate throttling is currently active.
        
        Returns:
            True if throttling is active
        """
        return self.throttling_active
    
    def get_degradation_level(self) -> int:
        """
        Get the current system degradation level.
        
        Returns:
            Degradation level (0=normal, 1=light, 2=moderate, 3=severe)
        """
        return self.degradation_level
    
    def request_memory_cleanup(self) -> None:
        """Request immediate memory cleanup."""
        self._perform_memory_cleanup(force=True)
    
    def get_reusable_buffer(self, shape: tuple, dtype: Any) -> Optional[Any]:
        """
        Get a reusable buffer from cache to reduce memory allocations.
        
        Args:
            shape: Required buffer shape
            dtype: Required buffer data type
            
        Returns:
            Reusable buffer or None if not available
        """
        try:
            import numpy as np
            
            # Look for compatible buffer in cache
            for i, (cached_shape, cached_dtype, buffer) in enumerate(self.image_buffer_cache):
                if cached_shape == shape and cached_dtype == dtype:
                    # Remove from cache and return
                    del self.image_buffer_cache[i]
                    return buffer
            
            return None
            
        except Exception as e:
            self.node.get_logger().debug(f'Error getting reusable buffer: {e}')
            return None
    
    def return_buffer(self, buffer: Any, shape: tuple, dtype: Any) -> None:
        """
        Return a buffer to the cache for reuse.
        
        Args:
            buffer: Buffer to cache
            shape: Buffer shape
            dtype: Buffer data type
        """
        try:
            # Only cache if we have space and buffer is reasonable size
            if len(self.image_buffer_cache) < self.image_buffer_cache.maxlen:
                # Don't cache very large buffers to avoid memory issues
                buffer_size_mb = buffer.nbytes / 1024 / 1024 if hasattr(buffer, 'nbytes') else 0
                if buffer_size_mb < 50:  # Max 50MB per cached buffer
                    self.image_buffer_cache.append((shape, dtype, buffer))
        
        except Exception as e:
            self.node.get_logger().debug(f'Error caching buffer: {e}')
    
    def update_performance_metrics(self, cpu_usage: float, memory_usage_mb: float, 
                                 current_fps: float) -> None:
        """
        Update performance metrics for adaptive resource management.
        
        Args:
            cpu_usage: Current CPU usage percentage
            memory_usage_mb: Current memory usage in MB
            current_fps: Current measured frame rate
        """
        with self.adaptation_lock:
            # Store performance sample
            sample = {
                'timestamp': time.time(),
                'cpu_usage': cpu_usage,
                'memory_usage_mb': memory_usage_mb,
                'fps': current_fps,
                'fps_limit': self.current_fps_limit
            }
            self.performance_history.append(sample)
    
    def _manage_resources(self) -> None:
        """Main resource management loop."""
        try:
            # Get latest performance data
            if not self.performance_history:
                return
            
            with self.adaptation_lock:
                latest = self.performance_history[-1]
                cpu_usage = latest['cpu_usage']
                memory_usage_mb = latest['memory_usage_mb']
                current_fps = latest['fps']
            
            # Determine if we need to adjust resource usage
            self._adapt_frame_rate(cpu_usage, memory_usage_mb, current_fps)
            
            # Check if memory cleanup is needed
            self._check_memory_cleanup(memory_usage_mb)
            
            # Update degradation level
            self._update_degradation_level(cpu_usage, memory_usage_mb)
            
        except Exception as e:
            self.node.get_logger().error(f'Error in resource management: {e}')
    
    def _adapt_frame_rate(self, cpu_usage: float, memory_usage_mb: float, 
                         current_fps: float) -> None:
        """
        Adapt frame rate based on system resource usage.
        
        Args:
            cpu_usage: Current CPU usage percentage
            memory_usage_mb: Current memory usage in MB
            current_fps: Current measured frame rate
        """
        old_fps_limit = self.current_fps_limit
        
        # Determine target FPS based on resource usage
        if cpu_usage > self.limits.max_cpu_percent * 0.9 or memory_usage_mb > self.limits.max_memory_mb * 0.9:
            # High resource usage - reduce FPS aggressively
            target_fps = max(self.limits.min_fps, self.current_fps_limit * 0.7)
            self.throttling_active = True
            
        elif cpu_usage > self.limits.max_cpu_percent * 0.8 or memory_usage_mb > self.limits.max_memory_mb * 0.8:
            # Moderate resource usage - reduce FPS moderately
            target_fps = max(self.limits.min_fps, self.current_fps_limit * 0.85)
            self.throttling_active = True
            
        elif cpu_usage < self.limits.max_cpu_percent * 0.6 and memory_usage_mb < self.limits.max_memory_mb * 0.6:
            # Low resource usage - can increase FPS
            target_fps = min(self.limits.max_fps, self.current_fps_limit * 1.1)
            if target_fps >= self.limits.max_fps * 0.95:
                self.throttling_active = False
        else:
            # Stable resource usage - maintain current FPS
            target_fps = self.current_fps_limit
        
        # Apply gradual changes to avoid oscillation
        if target_fps != self.current_fps_limit:
            # Limit rate of change
            max_change = self.current_fps_limit * 0.2  # Max 20% change per adjustment
            if target_fps > self.current_fps_limit:
                self.current_fps_limit = min(target_fps, self.current_fps_limit + max_change)
            else:
                self.current_fps_limit = max(target_fps, self.current_fps_limit - max_change)
            
            # Update frame interval
            self.frame_interval = 1.0 / self.current_fps_limit
            
            # Log significant changes
            if abs(old_fps_limit - self.current_fps_limit) > 1.0:
                self.node.get_logger().info(
                    f'Adapted FPS limit: {old_fps_limit:.1f} -> {self.current_fps_limit:.1f} '
                    f'(CPU: {cpu_usage:.1f}%, Memory: {memory_usage_mb:.1f}MB)'
                )
    
    def _check_memory_cleanup(self, memory_usage_mb: float) -> None:
        """
        Check if memory cleanup is needed and perform it.
        
        Args:
            memory_usage_mb: Current memory usage in MB
        """
        current_time = time.time()
        
        # Force cleanup if memory usage is high
        if memory_usage_mb > self.limits.max_memory_mb * self.limits.memory_cleanup_threshold:
            self._perform_memory_cleanup(force=True)
            return
        
        # Regular cleanup based on time interval
        if current_time - self.last_gc_time > self.gc_interval:
            self._perform_memory_cleanup(force=False)
    
    def _perform_memory_cleanup(self, force: bool = False) -> None:
        """
        Perform memory cleanup operations.
        
        Args:
            force: Whether to force aggressive cleanup
        """
        try:
            # Clear image buffer cache if memory is tight
            if force and len(self.image_buffer_cache) > 0:
                self.image_buffer_cache.clear()
                self.node.get_logger().info('Cleared image buffer cache due to memory pressure')
            
            # Run garbage collection
            if force:
                # Aggressive cleanup
                collected = gc.collect()
                if collected > 0:
                    self.node.get_logger().info(f'Forced garbage collection freed {collected} objects')
            else:
                # Regular cleanup
                gc.collect()
            
            self.last_gc_time = time.time()
            
        except Exception as e:
            self.node.get_logger().error(f'Error during memory cleanup: {e}')
    
    def _update_degradation_level(self, cpu_usage: float, memory_usage_mb: float) -> None:
        """
        Update system degradation level based on resource usage.
        
        Args:
            cpu_usage: Current CPU usage percentage
            memory_usage_mb: Current memory usage in MB
        """
        old_level = self.degradation_level
        
        # Determine degradation level
        if (cpu_usage > self.limits.max_cpu_percent * 0.95 or 
            memory_usage_mb > self.limits.max_memory_mb * 0.95):
            self.degradation_level = 3  # Severe
        elif (cpu_usage > self.limits.max_cpu_percent * 0.85 or 
              memory_usage_mb > self.limits.max_memory_mb * 0.85):
            self.degradation_level = 2  # Moderate
        elif (cpu_usage > self.limits.max_cpu_percent * 0.7 or 
              memory_usage_mb > self.limits.max_memory_mb * 0.7):
            self.degradation_level = 1  # Light
        else:
            self.degradation_level = 0  # Normal
        
        # Log degradation level changes
        if old_level != self.degradation_level:
            level_names = ['Normal', 'Light', 'Moderate', 'Severe']
            self.node.get_logger().info(
                f'System degradation level changed: {level_names[old_level]} -> {level_names[self.degradation_level]}'
            )
    
    def get_resource_status(self) -> Dict[str, Any]:
        """
        Get current resource management status.
        
        Returns:
            Dictionary with resource status information
        """
        return {
            'fps_limit': self.current_fps_limit,
            'throttling_active': self.throttling_active,
            'degradation_level': self.degradation_level,
            'frame_interval': self.frame_interval,
            'cached_buffers': len(self.image_buffer_cache),
            'last_gc_time': self.last_gc_time
        }
    
    def shutdown(self) -> None:
        """Shutdown the resource manager."""
        # Clear all cached buffers
        self.image_buffer_cache.clear()
        
        # Final garbage collection
        gc.collect()
        
        self.node.get_logger().info('Resource Manager shutdown complete')

def main(args=None):
    """Main entry point for standalone resource manager node."""
    rclpy.init(args=args)
    
    # Create a simple node for standalone resource management
    node = Node('system_resource_manager')
    
    # Declare parameters
    node.declare_parameter('cpu_limit', 80.0)
    node.declare_parameter('memory_limit_mb', 500.0)
    node.declare_parameter('throttle_threshold', 85.0)
    node.declare_parameter('recovery_threshold', 70.0)
    node.declare_parameter('min_fps', 5.0)
    node.declare_parameter('max_fps', 30.0)
    
    # Get parameters
    cpu_limit = node.get_parameter('cpu_limit').get_parameter_value().double_value
    memory_limit_mb = node.get_parameter('memory_limit_mb').get_parameter_value().double_value
    throttle_threshold = node.get_parameter('throttle_threshold').get_parameter_value().double_value
    recovery_threshold = node.get_parameter('recovery_threshold').get_parameter_value().double_value
    min_fps = node.get_parameter('min_fps').get_parameter_value().double_value
    max_fps = node.get_parameter('max_fps').get_parameter_value().double_value
    
    # Create resource limits
    limits = ResourceLimits(
        max_cpu_percent=cpu_limit,
        max_memory_mb=memory_limit_mb,
        min_fps=min_fps,
        max_fps=max_fps
    )
    
    # Create resource manager
    resource_manager = ResourceManager(node=node, limits=limits)
    
    node.get_logger().info(
        f'System Resource Manager started - '
        f'CPU Limit: {cpu_limit}%, Memory Limit: {memory_limit_mb}MB, '
        f'FPS Range: {min_fps}-{max_fps}'
    )
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Resource manager interrupted by user')
    finally:
        resource_manager.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()