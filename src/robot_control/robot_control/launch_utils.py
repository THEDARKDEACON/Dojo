#!/usr/bin/env python3
"""
Launch utilities for mode-aware robot launching.

Provides utilities for detecting available packages and configuring
launch parameters based on the current operation mode.
"""

import os
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from ament_index_python.packages import get_package_share_directory, PackageNotFoundError


class LaunchModeManager:
    """
    Manages launch configuration based on operation mode and available packages.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.available_packages = self._detect_available_packages()
        
    def _detect_available_packages(self) -> List[str]:
        """Detect available ROS2 packages."""
        available_packages = []
        
        # Common packages to check
        packages_to_check = [
            'robot_gazebo',
            'robot_hardware', 
            'robot_control',
            'robot_perception',
            'robot_navigation',
            'robot_description',
            'gazebo_ros',
            'controller_manager',
            'diff_drive_controller',
            'joint_state_broadcaster'
        ]
        
        for package in packages_to_check:
            try:
                get_package_share_directory(package)
                available_packages.append(package)
            except PackageNotFoundError:
                pass
        
        return available_packages
    
    def is_package_available(self, package_name: str) -> bool:
        """Check if a package is available."""
        return package_name in self.available_packages
    
    def is_gazebo_available(self) -> bool:
        """Check if Gazebo simulation is available."""
        return (self.is_package_available('robot_gazebo') and 
                self.is_package_available('gazebo_ros') and
                self._is_gazebo_installed())
    
    def _is_gazebo_installed(self) -> bool:
        """Check if Gazebo is installed on the system."""
        try:
            import subprocess
            result = subprocess.run(['which', 'gazebo'], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False
    
    def detect_operation_mode(self) -> str:
        """
        Detect the operation mode based on environment and available packages.
        
        Returns:
            'simulation' if Gazebo is available and requested, 'hardware' otherwise.
        """
        # Check environment variables
        use_simulation = os.getenv('USE_SIMULATION', 'false').lower() == 'true'
        use_gazebo = os.getenv('USE_GAZEBO', 'false').lower() == 'true'
        
        if use_simulation or use_gazebo:
            if self.is_gazebo_available():
                return 'simulation'
            else:
                self.logger.warning("Simulation requested but Gazebo not available, using hardware mode")
        
        return 'hardware'
    
    def get_launch_arguments(self, mode: Optional[str] = None) -> Dict[str, str]:
        """
        Get launch arguments for the specified mode.
        
        Args:
            mode: Operation mode ('simulation' or 'hardware'). If None, auto-detects.
            
        Returns:
            Dictionary of launch arguments.
        """
        if mode is None:
            mode = self.detect_operation_mode()
        
        base_args = {
            'operation_mode': mode,
        }
        
        if mode == 'simulation':
            base_args.update({
                'use_sim_time': 'true',
                'use_gazebo': 'true',
                'use_hardware': 'false',
                'use_arduino': 'false',
                'use_camera': 'false',
                'use_lidar': 'false',
                'world': os.getenv('GAZEBO_WORLD', 'empty.world'),
            })
        else:  # hardware mode
            base_args.update({
                'use_sim_time': 'false',
                'use_gazebo': 'false',
                'use_hardware': 'true',
                'use_arduino': str(self.is_package_available('robot_hardware')).lower(),
                'use_camera': str(self.is_package_available('robot_sensors')).lower(),
                'use_lidar': str(self.is_package_available('robot_sensors')).lower(),
            })
        
        return base_args
    
    def validate_mode_requirements(self, mode: str) -> Tuple[bool, List[str]]:
        """
        Validate that requirements for the specified mode are met.
        
        Args:
            mode: Operation mode to validate.
            
        Returns:
            Tuple of (is_valid, list_of_missing_requirements).
        """
        missing_requirements = []
        
        if mode == 'simulation':
            if not self.is_package_available('robot_gazebo'):
                missing_requirements.append('robot_gazebo package')
            
            if not self.is_package_available('gazebo_ros'):
                missing_requirements.append('gazebo_ros package')
            
            if not self._is_gazebo_installed():
                missing_requirements.append('Gazebo installation')
            
            if not self.is_package_available('controller_manager'):
                missing_requirements.append('controller_manager package')
                
        elif mode == 'hardware':
            if not self.is_package_available('robot_hardware'):
                missing_requirements.append('robot_hardware package')
            
            if not self.is_package_available('robot_control'):
                missing_requirements.append('robot_control package')
        
        # Common requirements
        if not self.is_package_available('robot_description'):
            missing_requirements.append('robot_description package')
        
        return len(missing_requirements) == 0, missing_requirements
    
    def get_conditional_launch_includes(self, mode: str) -> Dict[str, bool]:
        """
        Get conditional launch includes based on mode and available packages.
        
        Args:
            mode: Operation mode.
            
        Returns:
            Dictionary mapping launch file types to whether they should be included.
        """
        includes = {
            'gazebo': False,
            'hardware': False,
            'control': False,
            'perception': False,
            'navigation': False,
        }
        
        if mode == 'simulation':
            includes['gazebo'] = self.is_gazebo_available()
        else:  # hardware mode
            includes['hardware'] = self.is_package_available('robot_hardware')
            includes['control'] = self.is_package_available('robot_control')
        
        # Optional components (available in both modes)
        includes['perception'] = self.is_package_available('robot_perception')
        includes['navigation'] = self.is_package_available('robot_navigation')
        
        return includes
    
    def log_mode_status(self, mode: str) -> None:
        """Log the current mode status and available packages."""
        self.logger.info(f"Operation mode: {mode}")
        self.logger.info(f"Available packages: {self.available_packages}")
        
        is_valid, missing = self.validate_mode_requirements(mode)
        if not is_valid:
            self.logger.warning(f"Mode requirements not fully met: {missing}")
        else:
            self.logger.info("All mode requirements satisfied")
        
        includes = self.get_conditional_launch_includes(mode)
        self.logger.info(f"Launch includes: {includes}")


def get_mode_manager() -> LaunchModeManager:
    """Get a singleton instance of the LaunchModeManager."""
    if not hasattr(get_mode_manager, '_instance'):
        get_mode_manager._instance = LaunchModeManager()
    return get_mode_manager._instance