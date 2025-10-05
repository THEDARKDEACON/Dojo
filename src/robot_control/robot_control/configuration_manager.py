#!/usr/bin/env python3
"""
Configuration Manager for Dojo Robot

Provides centralized configuration management with validation, conflict detection,
and parameter propagation to all subsystems.
"""

import os
import yaml
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter


@dataclass
class ConfigConflict:
    """Represents a configuration conflict between parameters."""
    parameter_name: str
    expected_value: Any
    actual_value: Any
    source_file: str
    description: str


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    conflicts: List[ConfigConflict]


class ConfigurationManager:
    """
    Centralized configuration manager for the robot system.
    
    Handles loading, validation, and propagation of configuration parameters
    from the master robot_config.yaml file to all subsystems. Supports automatic
    mode switching between simulation and hardware modes.
    """
    
    def __init__(self, config_path: Optional[str] = None, mode: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the master configuration file. If None, uses default.
            mode: Operation mode ('simulation' or 'hardware'). If None, auto-detects.
        """
        self.logger = logging.getLogger(__name__)
        
        # Set default config path if not provided
        if config_path is None:
            # Look for config in workspace root
            workspace_root = self._find_workspace_root()
            config_path = os.path.join(workspace_root, "config", "robot_config.yaml")
        
        self.config_path = config_path
        self.master_config: Dict[str, Any] = {}
        self.validation_schema: Dict[str, Any] = {}
        self.environment = os.getenv('ROBOT_ENVIRONMENT', 'development')
        
        # Mode detection and configuration
        self.operation_mode = mode or self._detect_operation_mode()
        self.available_packages = self._detect_available_packages()
        
        # Load configuration on initialization
        self.load_master_config()
    
    def _find_workspace_root(self) -> str:
        """Find the ROS2 workspace root directory."""
        current_dir = Path(__file__).resolve()
        
        # Look for workspace indicators (src, install, build directories)
        for parent in current_dir.parents:
            if (parent / 'src').exists() and (parent / 'install').exists():
                return str(parent)
        
        # Fallback to current directory's parent structure
        return str(current_dir.parents[3])  # Assuming we're in src/package/package/
    
    def _detect_operation_mode(self) -> str:
        """
        Automatically detect the operation mode based on environment and available packages.
        
        Returns:
            'simulation' if Gazebo packages are available and USE_SIMULATION is set,
            'hardware' otherwise.
        """
        # Check environment variable first
        use_simulation = os.getenv('USE_SIMULATION', 'false').lower() == 'true'
        
        if use_simulation:
            # Check if Gazebo packages are available
            if self._is_package_available('robot_gazebo') and self._is_gazebo_available():
                self.logger.info("Detected simulation mode (Gazebo available)")
                return 'simulation'
            else:
                self.logger.warning("Simulation requested but Gazebo not available, falling back to hardware mode")
        
        self.logger.info("Detected hardware mode")
        return 'hardware'
    
    def _detect_available_packages(self) -> List[str]:
        """
        Detect which ROS2 packages are available in the workspace.
        
        Returns:
            List of available package names.
        """
        available_packages = []
        workspace_root = self._find_workspace_root()
        src_dir = os.path.join(workspace_root, 'src')
        
        if os.path.exists(src_dir):
            for item in os.listdir(src_dir):
                package_path = os.path.join(src_dir, item)
                if os.path.isdir(package_path):
                    # Check if it's a ROS2 package (has package.xml)
                    if os.path.exists(os.path.join(package_path, 'package.xml')):
                        available_packages.append(item)
        
        self.logger.debug(f"Available packages: {available_packages}")
        return available_packages
    
    def _is_package_available(self, package_name: str) -> bool:
        """Check if a specific package is available."""
        return package_name in self.available_packages
    
    def _is_gazebo_available(self) -> bool:
        """Check if Gazebo is installed and available."""
        try:
            import subprocess
            result = subprocess.run(['which', 'gazebo'], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False
    
    def load_master_config(self) -> Dict[str, Any]:
        """
        Load the master configuration file.
        
        Returns:
            The loaded configuration dictionary.
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
            yaml.YAMLError: If the YAML file is malformed.
        """
        try:
            with open(self.config_path, 'r') as file:
                config_data = yaml.safe_load(file)
            
            if not config_data:
                raise ValueError("Configuration file is empty")
            
            self.master_config = config_data
            self.validation_schema = config_data.get('validation', {})
            
            # Apply environment-specific overrides
            self._apply_environment_overrides()
            
            self.logger.info(f"Loaded master configuration from {self.config_path}")
            self.logger.info(f"Using environment: {self.environment}")
            
            return self.master_config
            
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML configuration: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error loading configuration: {e}")
            raise
    
    def _apply_environment_overrides(self) -> None:
        """Apply environment-specific and mode-specific configuration overrides."""
        environments = self.master_config.get('environments', {})
        
        # Apply environment overrides first
        env_config = environments.get(self.environment, {})
        if env_config:
            self.logger.info(f"Applying {self.environment} environment overrides")
            self._deep_merge(self.master_config['robot'], env_config)
        
        # Apply mode-specific overrides
        mode_config = environments.get(self.operation_mode, {})
        if mode_config:
            self.logger.info(f"Applying {self.operation_mode} mode overrides")
            self._deep_merge(self.master_config['robot'], mode_config)
        
        # Apply mode-specific system settings
        self._apply_mode_specific_settings()
    
    def _deep_merge(self, base_dict: Dict, override_dict: Dict) -> None:
        """Recursively merge override dictionary into base dictionary."""
        for key, value in override_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_merge(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _apply_mode_specific_settings(self) -> None:
        """Apply mode-specific system settings based on operation mode."""
        robot_config = self.master_config.get('robot', {})
        system_config = robot_config.get('system', {})
        
        if self.operation_mode == 'simulation':
            # Simulation mode settings
            system_config['use_simulation'] = True
            system_config['use_sim_time'] = True
            
            # Disable hardware auto-discovery in simulation
            hardware_config = robot_config.get('hardware', {})
            for device_type in ['arduino', 'camera', 'lidar']:
                if device_type in hardware_config:
                    hardware_config[device_type]['auto_discover'] = False
            
            self.logger.info("Applied simulation mode settings")
            
        elif self.operation_mode == 'hardware':
            # Hardware mode settings
            system_config['use_simulation'] = False
            system_config['use_sim_time'] = False
            
            # Enable hardware auto-discovery in hardware mode
            hardware_config = robot_config.get('hardware', {})
            for device_type in ['arduino', 'camera', 'lidar']:
                if device_type in hardware_config:
                    hardware_config[device_type]['auto_discover'] = True
            
            self.logger.info("Applied hardware mode settings")
    
    def validate_configuration(self) -> ValidationResult:
        """
        Validate the loaded configuration against the schema.
        
        Returns:
            ValidationResult containing validation status and any issues found.
        """
        errors = []
        warnings = []
        conflicts = []
        
        try:
            robot_config = self.master_config.get('robot', {})
            
            # Validate physical parameters
            physical_errors = self._validate_physical_parameters(robot_config)
            errors.extend(physical_errors)
            
            # Validate hardware configuration
            hardware_errors = self._validate_hardware_config(robot_config)
            errors.extend(hardware_errors)
            
            # Validate safety parameters
            safety_errors = self._validate_safety_config(robot_config)
            errors.extend(safety_errors)
            
            # Check for internal consistency
            consistency_conflicts = self._check_internal_consistency(robot_config)
            conflicts.extend(consistency_conflicts)
            
            # Validate required packages
            package_warnings = self._validate_packages(robot_config)
            warnings.extend(package_warnings)
            
            # Validate mode compatibility
            mode_warnings = self._validate_mode_compatibility(robot_config)
            warnings.extend(mode_warnings)
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            self.logger.info("Configuration validation passed")
        else:
            self.logger.error(f"Configuration validation failed with {len(errors)} errors")
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            conflicts=conflicts
        )
    
    def _validate_physical_parameters(self, config: Dict) -> List[str]:
        """Validate physical robot parameters against limits."""
        errors = []
        physical_params = config.get('physical_parameters', {})
        limits = self.validation_schema.get('physical_limits', {})
        
        for param, limit_range in limits.items():
            if param in physical_params:
                value = physical_params[param]
                min_val, max_val = limit_range
                
                if not (min_val <= value <= max_val):
                    errors.append(
                        f"Physical parameter '{param}' value {value} is outside "
                        f"valid range [{min_val}, {max_val}]"
                    )
        
        # Check for required physical parameters
        required_params = ['wheel_base', 'wheel_radius', 'max_linear_velocity', 'max_angular_velocity']
        for param in required_params:
            if param not in physical_params:
                errors.append(f"Required physical parameter '{param}' is missing")
        
        return errors
    
    def _validate_hardware_config(self, config: Dict) -> List[str]:
        """Validate hardware configuration parameters."""
        errors = []
        hardware_config = config.get('hardware', {})
        hardware_checks = self.validation_schema.get('hardware_checks', {})
        
        # Validate Arduino configuration
        arduino_config = hardware_config.get('arduino', {})
        if 'baud_rate' in arduino_config:
            baud_rate = arduino_config['baud_rate']
            valid_rates = hardware_checks.get('arduino_baud_rates', [])
            if valid_rates and baud_rate not in valid_rates:
                errors.append(f"Invalid Arduino baud rate: {baud_rate}")
        
        # Validate camera configuration
        camera_config = hardware_config.get('camera', {})
        if 'preferred_resolution' in camera_config:
            resolution = camera_config['preferred_resolution']
            valid_resolutions = hardware_checks.get('camera_resolutions', [])
            if valid_resolutions and resolution not in valid_resolutions:
                errors.append(f"Invalid camera resolution: {resolution}")
        
        # Validate LiDAR configuration
        lidar_config = hardware_config.get('lidar', {})
        if 'scan_frequency' in lidar_config:
            frequency = lidar_config['scan_frequency']
            valid_frequencies = hardware_checks.get('lidar_frequencies', [])
            if valid_frequencies and frequency not in valid_frequencies:
                errors.append(f"Invalid LiDAR frequency: {frequency}")
        
        return errors
    
    def _validate_safety_config(self, config: Dict) -> List[str]:
        """Validate safety system configuration."""
        errors = []
        safety_config = config.get('safety', {})
        safety_checks = self.validation_schema.get('safety_checks', {})
        
        # Check minimum obstacle distance
        if 'obstacle_stop_distance' in safety_config:
            distance = safety_config['obstacle_stop_distance']
            min_distance = safety_checks.get('min_obstacle_distance', 0.1)
            if distance < min_distance:
                errors.append(
                    f"Obstacle stop distance {distance}m is below minimum safe distance {min_distance}m"
                )
        
        # Check command timeout
        if 'command_timeout' in safety_config:
            timeout = safety_config['command_timeout']
            max_timeout = safety_checks.get('max_command_timeout', 5.0)
            if timeout > max_timeout:
                errors.append(f"Command timeout {timeout}s exceeds maximum {max_timeout}s")
        
        # Check emergency stop response time
        if 'emergency_stop_timeout' in safety_config:
            stop_time = safety_config['emergency_stop_timeout']
            min_stop_time = safety_checks.get('min_emergency_stop_time', 0.1)
            if stop_time < min_stop_time:
                errors.append(
                    f"Emergency stop timeout {stop_time}s is below minimum {min_stop_time}s"
                )
        
        return errors
    
    def _check_internal_consistency(self, config: Dict) -> List[ConfigConflict]:
        """Check for internal configuration consistency."""
        conflicts = []
        
        # Check wheel parameters consistency
        physical_params = config.get('physical_parameters', {})
        wheel_radius = physical_params.get('wheel_radius')
        wheel_circumference = physical_params.get('wheel_circumference')
        
        if wheel_radius and wheel_circumference:
            expected_circumference = 2 * 3.14159 * wheel_radius
            if abs(wheel_circumference - expected_circumference) > 0.01:
                conflicts.append(ConfigConflict(
                    parameter_name='wheel_circumference',
                    expected_value=expected_circumference,
                    actual_value=wheel_circumference,
                    source_file='robot_config.yaml',
                    description='Wheel circumference does not match wheel radius'
                ))
        
        # Check velocity limits consistency
        max_linear = physical_params.get('max_linear_velocity')
        safe_linear = config.get('safety', {}).get('safe_linear_velocity')
        
        if max_linear and safe_linear and safe_linear > max_linear:
            conflicts.append(ConfigConflict(
                parameter_name='safe_linear_velocity',
                expected_value=f'<= {max_linear}',
                actual_value=safe_linear,
                source_file='robot_config.yaml',
                description='Safe linear velocity exceeds maximum linear velocity'
            ))
        
        return conflicts
    
    def _validate_packages(self, config: Dict) -> List[str]:
        """Validate package dependencies."""
        warnings = []
        system_config = config.get('system', {})
        
        required_packages = system_config.get('required_packages', [])
        optional_packages = system_config.get('optional_packages', [])
        
        # Check if packages exist (simplified check)
        workspace_root = self._find_workspace_root()
        src_dir = os.path.join(workspace_root, 'src')
        
        for package in required_packages:
            package_path = os.path.join(src_dir, package)
            if not os.path.exists(package_path):
                warnings.append(f"Required package '{package}' not found in workspace")
        
        for package in optional_packages:
            package_path = os.path.join(src_dir, package)
            if not os.path.exists(package_path):
                warnings.append(f"Optional package '{package}' not found in workspace")
        
        return warnings
    
    def _validate_mode_compatibility(self, config: Dict) -> List[str]:
        """Validate that the current mode is compatible with available packages."""
        warnings = []
        
        if self.operation_mode == 'simulation':
            # Check if simulation packages are available
            if not self._is_package_available('robot_gazebo'):
                warnings.append("Simulation mode requested but robot_gazebo package not found")
            
            if not self._is_gazebo_available():
                warnings.append("Simulation mode requested but Gazebo not installed")
            
            # Check for simulation-specific configuration
            system_config = config.get('system', {})
            if not system_config.get('use_simulation', False):
                warnings.append("Simulation mode detected but use_simulation is false in config")
        
        elif self.operation_mode == 'hardware':
            # Check if hardware packages are available
            required_hardware_packages = ['robot_hardware', 'robot_control']
            for package in required_hardware_packages:
                if not self._is_package_available(package):
                    warnings.append(f"Hardware mode requires {package} package but it's not found")
        
        return warnings
    
    def detect_conflicts(self) -> List[ConfigConflict]:
        """
        Detect conflicts between master config and existing configuration files.
        
        Returns:
            List of detected configuration conflicts.
        """
        conflicts = []
        
        try:
            # Check conflicts with existing config files
            workspace_root = self._find_workspace_root()
            
            # Check Arduino config conflicts
            arduino_conflicts = self._check_arduino_config_conflicts(workspace_root)
            conflicts.extend(arduino_conflicts)
            
            # Check controller config conflicts
            controller_conflicts = self._check_controller_config_conflicts(workspace_root)
            conflicts.extend(controller_conflicts)
            
        except Exception as e:
            self.logger.error(f"Error detecting conflicts: {e}")
        
        return conflicts
    
    def _check_arduino_config_conflicts(self, workspace_root: str) -> List[ConfigConflict]:
        """Check for conflicts with Arduino configuration files."""
        conflicts = []
        
        arduino_config_paths = [
            "src/robot_control/config/arduino.yaml",
            "src/robot_hardware/config/rosarduino_bridge.yaml"
        ]
        
        master_arduino = self.master_config['robot']['hardware']['arduino']
        master_physical = self.master_config['robot']['physical_parameters']
        
        for config_path in arduino_config_paths:
            full_path = os.path.join(workspace_root, config_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r') as file:
                        existing_config = yaml.safe_load(file)
                    
                    # Check for parameter conflicts
                    conflicts.extend(self._compare_arduino_params(
                        master_arduino, master_physical, existing_config, config_path
                    ))
                    
                except Exception as e:
                    self.logger.warning(f"Could not check conflicts in {config_path}: {e}")
        
        return conflicts
    
    def _compare_arduino_params(self, master_arduino: Dict, master_physical: Dict, 
                               existing_config: Dict, source_file: str) -> List[ConfigConflict]:
        """Compare Arduino parameters between master and existing config."""
        conflicts = []
        
        # Extract existing parameters (handle different config structures)
        existing_params = {}
        if 'arduino_bridge' in existing_config:
            existing_params = existing_config['arduino_bridge'].get('ros__parameters', {})
        elif 'arduino_driver' in existing_config:
            existing_params = existing_config['arduino_driver'].get('ros__parameters', {})
        
        # Check key parameters for conflicts
        param_mappings = {
            'baud_rate': master_arduino.get('baud_rate'),
            'wheel_base': master_physical.get('wheel_base'),
            'wheel_radius': master_physical.get('wheel_radius'),
            'timeout': master_arduino.get('timeout'),
        }
        
        for param_name, master_value in param_mappings.items():
            if param_name in existing_params and master_value is not None:
                existing_value = existing_params[param_name]
                if abs(existing_value - master_value) > 0.001:  # Allow small floating point differences
                    conflicts.append(ConfigConflict(
                        parameter_name=param_name,
                        expected_value=master_value,
                        actual_value=existing_value,
                        source_file=source_file,
                        description=f"Parameter mismatch in {source_file}"
                    ))
        
        return conflicts
    
    def _check_controller_config_conflicts(self, workspace_root: str) -> List[ConfigConflict]:
        """Check for conflicts with controller configuration files."""
        conflicts = []
        
        controller_config_path = "src/robot_control/config/controllers.yaml"
        full_path = os.path.join(workspace_root, controller_config_path)
        
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r') as file:
                    existing_config = yaml.safe_load(file)
                
                master_physical = self.master_config['robot']['physical_parameters']
                
                # Check diff drive controller parameters
                controller_manager = existing_config.get('controller_manager', {}).get('ros__parameters', {})
                diff_drive = controller_manager.get('diff_drive_controller', {})
                
                if 'wheel_separation' in diff_drive:
                    master_wheel_base = master_physical.get('wheel_base')
                    existing_separation = diff_drive['wheel_separation']
                    
                    if master_wheel_base and abs(existing_separation - master_wheel_base) > 0.001:
                        conflicts.append(ConfigConflict(
                            parameter_name='wheel_separation',
                            expected_value=master_wheel_base,
                            actual_value=existing_separation,
                            source_file=controller_config_path,
                            description="Wheel separation mismatch with master wheel_base"
                        ))
                
                if 'wheel_radius' in diff_drive:
                    master_wheel_radius = master_physical.get('wheel_radius')
                    existing_radius = diff_drive['wheel_radius']
                    
                    if master_wheel_radius and abs(existing_radius - master_wheel_radius) > 0.001:
                        conflicts.append(ConfigConflict(
                            parameter_name='wheel_radius',
                            expected_value=master_wheel_radius,
                            actual_value=existing_radius,
                            source_file=controller_config_path,
                            description="Wheel radius mismatch with master configuration"
                        ))
                        
            except Exception as e:
                self.logger.warning(f"Could not check conflicts in {controller_config_path}: {e}")
        
        return conflicts
    
    def propagate_parameters(self) -> None:
        """
        Propagate parameters from master config to all subsystem configuration files.
        
        This method updates existing configuration files to use values from the master config,
        ensuring consistency across the entire system.
        """
        try:
            workspace_root = self._find_workspace_root()
            
            # Update Arduino configuration files
            self._update_arduino_configs(workspace_root)
            
            # Update controller configuration files
            self._update_controller_configs(workspace_root)
            
            self.logger.info("Successfully propagated parameters to all subsystems")
            
        except Exception as e:
            self.logger.error(f"Error propagating parameters: {e}")
            raise
    
    def _update_arduino_configs(self, workspace_root: str) -> None:
        """Update Arduino configuration files with master parameters."""
        arduino_config_paths = [
            "src/robot_control/config/arduino.yaml",
            "src/robot_hardware/config/rosarduino_bridge.yaml"
        ]
        
        master_arduino = self.master_config['robot']['hardware']['arduino']
        master_physical = self.master_config['robot']['physical_parameters']
        
        for config_path in arduino_config_paths:
            full_path = os.path.join(workspace_root, config_path)
            if os.path.exists(full_path):
                self._update_single_arduino_config(full_path, master_arduino, master_physical)
    
    def _update_single_arduino_config(self, config_path: str, master_arduino: Dict, 
                                    master_physical: Dict) -> None:
        """Update a single Arduino configuration file."""
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
            
            # Determine the config structure and update accordingly
            if 'arduino_bridge' in config:
                params = config['arduino_bridge']['ros__parameters']
            elif 'arduino_driver' in config:
                params = config['arduino_driver']['ros__parameters']
            else:
                self.logger.warning(f"Unknown config structure in {config_path}")
                return
            
            # Update parameters from master config
            params['baud_rate'] = master_arduino['baud_rate']
            params['timeout'] = master_arduino['timeout']
            params['wheel_base'] = master_physical['wheel_base']
            params['wheel_radius'] = master_physical['wheel_radius']
            params['wheel_circumference'] = master_physical['wheel_circumference']
            params['encoder_ticks_per_rev'] = master_physical['encoder_ticks_per_rev']
            params['max_speed'] = master_physical['max_linear_velocity']
            params['max_angular_speed'] = master_physical['max_angular_velocity']
            
            # Update PID parameters if they exist in master config
            if 'pid' in master_arduino:
                if 'pid' not in params:
                    params['pid'] = {}
                params['pid'].update(master_arduino['pid'])
            
            # Write updated config back to file
            with open(config_path, 'w') as file:
                yaml.dump(config, file, default_flow_style=False, indent=2)
            
            self.logger.info(f"Updated Arduino config: {config_path}")
            
        except Exception as e:
            self.logger.error(f"Error updating Arduino config {config_path}: {e}")
    
    def _update_controller_configs(self, workspace_root: str) -> None:
        """Update controller configuration files with master parameters."""
        # Update hardware controller config
        controller_config_path = os.path.join(workspace_root, "src/robot_control/config/controllers.yaml")
        if os.path.exists(controller_config_path):
            self._update_hardware_controller_config(controller_config_path)
        
        # Update Gazebo controller config if in simulation mode or package exists
        gazebo_config_path = os.path.join(workspace_root, "src/robot_gazebo/config/ros2_control.yaml")
        if os.path.exists(gazebo_config_path):
            self._update_gazebo_controller_config(gazebo_config_path)
    
    def _update_hardware_controller_config(self, config_path: str) -> None:
        """Update hardware controller configuration."""
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
            
            master_physical = self.master_config['robot']['physical_parameters']
            master_control = self.master_config['robot']['control']
            
            # Update controller manager parameters
            controller_manager = config['controller_manager']['ros__parameters']
            controller_manager['update_rate'] = master_control['controller_update_rate']
            
            # Update diff drive controller parameters
            diff_drive = controller_manager['diff_drive_controller']
            diff_drive['wheel_separation'] = master_physical['wheel_base']
            diff_drive['wheel_radius'] = master_physical['wheel_radius']
            diff_drive['publish_rate'] = master_control['joint_state_rate']
            
            # Update velocity limits
            diff_drive['linear.x.max_velocity'] = master_physical['max_linear_velocity']
            diff_drive['linear.x.min_velocity'] = -master_physical['max_linear_velocity']
            diff_drive['linear.x.max_acceleration'] = master_physical['max_linear_acceleration']
            diff_drive['linear.x.min_acceleration'] = -master_physical['max_linear_acceleration']
            
            # Update other diff drive parameters from master config
            if 'diff_drive' in master_control:
                diff_drive_master = master_control['diff_drive']
                for key, value in diff_drive_master.items():
                    if key not in ['wheel_separation', 'wheel_radius']:  # Don't override physical params
                        diff_drive[key] = value
            
            # Write updated config back to file
            with open(config_path, 'w') as file:
                yaml.dump(config, file, default_flow_style=False, indent=2)
            
            self.logger.info(f"Updated hardware controller config: {config_path}")
            
        except Exception as e:
            self.logger.error(f"Error updating hardware controller config: {e}")
    
    def _update_gazebo_controller_config(self, config_path: str) -> None:
        """Update Gazebo controller configuration."""
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
            
            master_physical = self.master_config['robot']['physical_parameters']
            master_control = self.master_config['robot']['control']
            master_safety = self.master_config['robot']['safety']
            
            # Update controller manager parameters
            controller_manager = config['controller_manager']['ros__parameters']
            controller_manager['update_rate'] = master_control['controller_update_rate']
            controller_manager['use_sim_time'] = True  # Always true for Gazebo
            
            # Update diff drive controller parameters
            diff_drive = config['diff_drive_controller']['ros__parameters']
            diff_drive['wheel_separation'] = master_physical['wheel_base']
            diff_drive['wheel_radius'] = master_physical['wheel_radius']
            diff_drive['publish_rate'] = master_control['joint_state_rate']
            diff_drive['cmd_vel_timeout'] = master_safety['command_timeout']
            
            # Update velocity limits
            diff_drive['linear']['x']['max_velocity'] = master_physical['max_linear_velocity']
            diff_drive['linear']['x']['min_velocity'] = -master_physical['max_linear_velocity']
            diff_drive['linear']['x']['max_acceleration'] = master_physical['max_linear_acceleration']
            diff_drive['linear']['x']['min_acceleration'] = -master_physical['max_linear_acceleration']
            
            diff_drive['angular']['z']['max_velocity'] = master_physical['max_angular_velocity']
            diff_drive['angular']['z']['min_velocity'] = -master_physical['max_angular_velocity']
            diff_drive['angular']['z']['max_acceleration'] = master_physical['max_angular_acceleration']
            diff_drive['angular']['z']['min_acceleration'] = -master_physical['max_angular_acceleration']
            
            # Update frame IDs from master config
            if 'diff_drive' in master_control:
                diff_drive_master = master_control['diff_drive']
                diff_drive['odom_frame_id'] = diff_drive_master.get('odom_frame_id', 'odom')
                diff_drive['base_frame_id'] = diff_drive_master.get('base_frame_id', 'base_link')
                diff_drive['enable_odom_tf'] = diff_drive_master.get('enable_odom_tf', True)
                diff_drive['open_loop'] = diff_drive_master.get('open_loop', True)
                
                # Update covariance matrices
                if 'pose_covariance_diagonal' in diff_drive_master:
                    diff_drive['pose_covariance_diagonal'] = diff_drive_master['pose_covariance_diagonal']
                if 'twist_covariance_diagonal' in diff_drive_master:
                    diff_drive['twist_covariance_diagonal'] = diff_drive_master['twist_covariance_diagonal']
            
            # Write updated config back to file
            with open(config_path, 'w') as file:
                yaml.dump(config, file, default_flow_style=False, indent=2)
            
            self.logger.info(f"Updated Gazebo controller config: {config_path}")
            
        except Exception as e:
            self.logger.error(f"Error updating Gazebo controller config: {e}")
    
    def get_parameter(self, parameter_path: str, default: Any = None) -> Any:
        """
        Get a parameter value from the master configuration.
        
        Args:
            parameter_path: Dot-separated path to the parameter (e.g., 'robot.hardware.arduino.baud_rate')
            default: Default value if parameter is not found
            
        Returns:
            The parameter value or default if not found.
        """
        try:
            keys = parameter_path.split('.')
            value = self.master_config
            
            for key in keys:
                value = value[key]
            
            return value
            
        except (KeyError, TypeError):
            return default
    
    def get_robot_config(self) -> Dict[str, Any]:
        """Get the complete robot configuration section."""
        return self.master_config.get('robot', {})
    
    def get_hardware_config(self) -> Dict[str, Any]:
        """Get the hardware configuration section."""
        return self.master_config.get('robot', {}).get('hardware', {})
    
    def get_safety_config(self) -> Dict[str, Any]:
        """Get the safety configuration section."""
        return self.master_config.get('robot', {}).get('safety', {})
    
    def get_physical_parameters(self) -> Dict[str, Any]:
        """Get the physical parameters section."""
        return self.master_config.get('robot', {}).get('physical_parameters', {})
    
    def get_operation_mode(self) -> str:
        """Get the current operation mode."""
        return self.operation_mode
    
    def is_simulation_mode(self) -> bool:
        """Check if currently in simulation mode."""
        return self.operation_mode == 'simulation'
    
    def is_hardware_mode(self) -> bool:
        """Check if currently in hardware mode."""
        return self.operation_mode == 'hardware'
    
    def get_mode_specific_config(self) -> Dict[str, Any]:
        """
        Get configuration parameters specific to the current operation mode.
        
        Returns:
            Dictionary containing mode-specific configuration parameters.
        """
        robot_config = self.get_robot_config()
        mode_config = {
            'mode': self.operation_mode,
            'use_simulation': self.is_simulation_mode(),
            'use_sim_time': self.is_simulation_mode(),
            'available_packages': self.available_packages,
        }
        
        if self.is_simulation_mode():
            mode_config.update({
                'simulation_world': robot_config.get('system', {}).get('simulation_world', 'empty.world'),
                'gazebo_available': self._is_gazebo_available(),
                'hardware_discovery_enabled': False,
            })
        else:
            mode_config.update({
                'hardware_discovery_enabled': True,
                'arduino_enabled': self._is_package_available('robot_hardware'),
                'camera_enabled': self._is_package_available('robot_sensors'),
                'lidar_enabled': self._is_package_available('robot_sensors'),
            })
        
        return mode_config
    
    def get_launch_parameters(self) -> Dict[str, str]:
        """
        Get launch parameters for the current mode.
        
        Returns:
            Dictionary of launch parameters suitable for ROS2 launch files.
        """
        mode_config = self.get_mode_specific_config()
        robot_config = self.get_robot_config()
        
        launch_params = {
            'use_sim_time': str(mode_config['use_sim_time']).lower(),
            'use_simulation': str(mode_config['use_simulation']).lower(),
        }
        
        if self.is_simulation_mode():
            launch_params.update({
                'use_gazebo': 'true',
                'use_hardware': 'false',
                'world': mode_config.get('simulation_world', 'empty.world'),
                'use_arduino': 'false',
                'use_camera': 'false',
                'use_lidar': 'false',
            })
        else:
            launch_params.update({
                'use_gazebo': 'false',
                'use_hardware': 'true',
                'use_arduino': str(mode_config.get('arduino_enabled', True)).lower(),
                'use_camera': str(mode_config.get('camera_enabled', True)).lower(),
                'use_lidar': str(mode_config.get('lidar_enabled', True)).lower(),
            })
        
        return launch_params
    
    def validate_mode_requirements(self) -> Tuple[bool, List[str]]:
        """
        Validate that all requirements for the current mode are met.
        
        Returns:
            Tuple of (is_valid, list_of_missing_requirements)
        """
        missing_requirements = []
        
        if self.is_simulation_mode():
            # Check simulation requirements
            if not self._is_package_available('robot_gazebo'):
                missing_requirements.append('robot_gazebo package')
            
            if not self._is_gazebo_available():
                missing_requirements.append('Gazebo installation')
            
            # Check for required simulation configuration
            robot_config = self.get_robot_config()
            system_config = robot_config.get('system', {})
            if 'simulation_world' not in system_config:
                missing_requirements.append('simulation_world configuration')
        
        else:  # hardware mode
            # Check hardware requirements
            required_packages = ['robot_hardware', 'robot_control']
            for package in required_packages:
                if not self._is_package_available(package):
                    missing_requirements.append(f'{package} package')
        
        return len(missing_requirements) == 0, missing_requirements


class ConfigurationManagerNode(Node):
    """
    ROS2 node wrapper for the Configuration Manager.
    
    Provides ROS2 services for configuration management and parameter access.
    """
    
    def __init__(self):
        super().__init__('configuration_manager')
        
        # Initialize configuration manager with mode detection
        mode = self.get_parameter('operation_mode').get_parameter_value().string_value if self.has_parameter('operation_mode') else None
        self.config_manager = ConfigurationManager(mode=mode)
        
        # Log detected mode and available packages
        self.get_logger().info(f"Operation mode: {self.config_manager.get_operation_mode()}")
        self.get_logger().info(f"Available packages: {self.config_manager.available_packages}")
        
        # Validate mode requirements
        is_valid, missing_requirements = self.config_manager.validate_mode_requirements()
        if not is_valid:
            self.get_logger().warning(f"Mode requirements not fully met: {missing_requirements}")
        
        # Validate configuration on startup
        validation_result = self.config_manager.validate_configuration()
        
        if not validation_result.is_valid:
            self.get_logger().error("Configuration validation failed!")
            for error in validation_result.errors:
                self.get_logger().error(f"  - {error}")
            raise RuntimeError("Invalid configuration")
        
        # Log warnings
        for warning in validation_result.warnings:
            self.get_logger().warning(f"Configuration warning: {warning}")
        
        # Check for conflicts
        conflicts = self.config_manager.detect_conflicts()
        if conflicts:
            self.get_logger().warning(f"Found {len(conflicts)} configuration conflicts:")
            for conflict in conflicts:
                self.get_logger().warning(
                    f"  - {conflict.parameter_name}: expected {conflict.expected_value}, "
                    f"got {conflict.actual_value} in {conflict.source_file}"
                )
        
        # Propagate parameters to ensure consistency
        try:
            self.config_manager.propagate_parameters()
            self.get_logger().info("Configuration parameters propagated successfully")
        except Exception as e:
            self.get_logger().error(f"Failed to propagate parameters: {e}")
        
        # Log mode-specific configuration
        mode_config = self.config_manager.get_mode_specific_config()
        self.get_logger().info(f"Mode-specific config: {mode_config}")
        
        self.get_logger().info("Configuration Manager initialized successfully")


def main(args=None):
    """Main entry point for the configuration manager node."""
    rclpy.init(args=args)
    
    try:
        node = ConfigurationManagerNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()