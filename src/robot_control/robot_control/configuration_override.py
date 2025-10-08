#!/usr/bin/env python3
"""
Configuration Override System for Arduino Integration Bypass Mode

Provides parameter override functionality to apply robosync-compatible parameters
during bypass mode operation, ensuring consistent motion behavior.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter


@dataclass
class ParameterOverride:
    """Represents a parameter override with original and new values."""
    parameter_name: str
    original_value: Any
    override_value: Any
    parameter_path: str
    description: str


@dataclass
class OverrideResult:
    """Result of parameter override operation."""
    success: bool
    overrides_applied: List[ParameterOverride]
    errors: List[str]
    warnings: List[str]


class ConfigurationOverride:
    """
    Configuration override system for bypass mode.
    
    Manages parameter overrides to apply robosync-compatible values during
    bypass mode operation, with the ability to restore original values
    when returning to normal mode.
    """
    
    def __init__(self, node: Optional[Node] = None):
        """
        Initialize the configuration override system.
        
        Args:
            node: Optional ROS2 node for parameter management
        """
        self.logger = logging.getLogger(__name__)
        self.node = node
        
        # Storage for original parameter values
        self.original_parameters: Dict[str, ParameterOverride] = {}
        self.override_active = False
        
        # Robosync-compatible parameter definitions
        self.robosync_parameters = self._define_robosync_parameters()
        
        # Configuration file paths that may need updating
        self.config_file_paths = self._get_config_file_paths()
    
    def _define_robosync_parameters(self) -> Dict[str, Dict[str, Any]]:
        """
        Define robosync-compatible parameter values.
        
        Returns:
            Dictionary containing robosync parameter definitions
        """
        return {
            'physical_parameters': {
                'wheel_base': 0.19,                    # robosync value (meters)
                'wheel_radius': 0.035,                 # robosync value (meters)
                'wheel_circumference': 0.219911,       # 2 * pi * 0.035
                'encoder_ticks_per_rev': 20,           # robosync value
                'max_linear_velocity': 0.5,            # conservative limit
                'max_angular_velocity': 1.0            # conservative limit
            },
            'communication_parameters': {
                'baud_rate': 115200,                   # robosync compatibility
                'timeout': 1.0,                        # seconds
                'write_timeout': 1.0,                  # seconds
                'port': '/dev/ttyACM0',               # default Arduino port
                'use_robosync_protocol': True
            },
            'pid_parameters': {
                'kp': 20.0,                           # robosync PID values
                'kd': 12.0,
                'ki': 0.0,
                'ko': 50,
                'sample_time': 0.1
            },
            'motor_parameters': {
                'motor_max': 255,                     # Arduino PWM max
                'motor_min': 0,                       # Arduino PWM min
                'max_speed': 0.5,                     # m/s
                'max_angular_speed': 1.0              # rad/s
            }
        }
    
    def _get_config_file_paths(self) -> Dict[str, str]:
        """
        Get paths to configuration files that may need parameter overrides.
        
        Returns:
            Dictionary mapping config names to file paths
        """
        # Find workspace root
        workspace_root = self._find_workspace_root()
        
        return {
            'arduino_config': os.path.join(
                workspace_root, 'src/robot_control/config/arduino_config.yaml'
            ),
            'control_params': os.path.join(
                workspace_root, 'src/robot_control/config/control_params.yaml'
            ),
            'hardware_config': os.path.join(
                workspace_root, 'src/robot_hardware/config/hardware_config.yaml'
            ),
            'rosarduino_bridge_config': os.path.join(
                workspace_root, 'src/robot_hardware/config/rosarduino_bridge_config.yaml'
            )
        }
    
    def _find_workspace_root(self) -> str:
        """Find the ROS2 workspace root directory."""
        current_dir = Path(__file__).resolve()
        
        # Look for workspace indicators (src, install, build directories)
        for parent in current_dir.parents:
            if (parent / 'src').exists():
                return str(parent)
        
        # Fallback to current directory's parent structure
        return str(current_dir.parents[4])  # Assuming we're in src/package/package/
    
    def validate_robosync_parameters(self) -> OverrideResult:
        """
        Validate robosync parameter definitions.
        
        Returns:
            OverrideResult with validation status
        """
        errors = []
        warnings = []
        
        try:
            # Validate physical parameters
            physical_params = self.robosync_parameters['physical_parameters']
            
            # Check wheel parameters consistency
            wheel_radius = physical_params['wheel_radius']
            wheel_circumference = physical_params['wheel_circumference']
            expected_circumference = 2 * 3.14159 * wheel_radius
            
            if abs(wheel_circumference - expected_circumference) > 0.001:
                warnings.append(
                    f"Wheel circumference {wheel_circumference} doesn't match "
                    f"calculated value {expected_circumference:.6f} from radius {wheel_radius}"
                )
            
            # Validate parameter ranges
            if physical_params['wheel_base'] <= 0:
                errors.append("Wheel base must be positive")
            
            if physical_params['wheel_radius'] <= 0:
                errors.append("Wheel radius must be positive")
            
            if physical_params['encoder_ticks_per_rev'] <= 0:
                errors.append("Encoder ticks per revolution must be positive")
            
            # Validate communication parameters
            comm_params = self.robosync_parameters['communication_parameters']
            
            valid_baud_rates = [9600, 19200, 38400, 57600, 115200, 230400]
            if comm_params['baud_rate'] not in valid_baud_rates:
                warnings.append(
                    f"Baud rate {comm_params['baud_rate']} may not be supported by all devices"
                )
            
            if comm_params['timeout'] <= 0:
                errors.append("Communication timeout must be positive")
            
            # Validate PID parameters
            pid_params = self.robosync_parameters['pid_parameters']
            
            if pid_params['kp'] < 0:
                warnings.append("Negative Kp value may cause instability")
            
            if pid_params['sample_time'] <= 0:
                errors.append("PID sample time must be positive")
            
            self.logger.info("Robosync parameter validation completed")
            
        except Exception as e:
            errors.append(f"Parameter validation error: {str(e)}")
        
        return OverrideResult(
            success=len(errors) == 0,
            overrides_applied=[],
            errors=errors,
            warnings=warnings
        )
    
    def apply_robosync_overrides(self) -> OverrideResult:
        """
        Apply robosync-compatible parameter overrides.
        
        Returns:
            OverrideResult with operation status and applied overrides
        """
        if self.override_active:
            return OverrideResult(
                success=False,
                overrides_applied=[],
                errors=["Parameter overrides are already active"],
                warnings=[]
            )
        
        overrides_applied = []
        errors = []
        warnings = []
        
        try:
            # Apply ROS parameter overrides if node is available
            if self.node:
                ros_overrides = self._apply_ros_parameter_overrides()
                overrides_applied.extend(ros_overrides)
            
            # Apply configuration file overrides
            file_overrides = self._apply_config_file_overrides()
            overrides_applied.extend(file_overrides)
            
            self.override_active = True
            self.logger.info(f"Applied {len(overrides_applied)} robosync parameter overrides")
            
        except Exception as e:
            errors.append(f"Error applying overrides: {str(e)}")
            self.logger.error(f"Failed to apply robosync overrides: {e}")
        
        return OverrideResult(
            success=len(errors) == 0,
            overrides_applied=overrides_applied,
            errors=errors,
            warnings=warnings
        )
    
    def _apply_ros_parameter_overrides(self) -> List[ParameterOverride]:
        """
        Apply parameter overrides to ROS2 node parameters.
        
        Returns:
            List of applied parameter overrides
        """
        overrides = []
        
        if not self.node:
            return overrides
        
        # Physical parameters
        physical_params = self.robosync_parameters['physical_parameters']
        for param_name, new_value in physical_params.items():
            try:
                # Get current parameter value
                current_param = self.node.get_parameter(param_name)
                original_value = current_param.value
                
                # Store original value
                override = ParameterOverride(
                    parameter_name=param_name,
                    original_value=original_value,
                    override_value=new_value,
                    parameter_path=f"ros_parameter.{param_name}",
                    description=f"Robosync physical parameter override"
                )
                
                # Apply new parameter value
                new_param = Parameter(param_name, Parameter.Type.DOUBLE, new_value)
                self.node.set_parameters([new_param])
                
                self.original_parameters[param_name] = override
                overrides.append(override)
                
                self.logger.debug(f"Override ROS parameter {param_name}: {original_value} -> {new_value}")
                
            except Exception as e:
                self.logger.warning(f"Could not override ROS parameter {param_name}: {e}")
        
        # Communication parameters
        comm_params = self.robosync_parameters['communication_parameters']
        for param_name, new_value in comm_params.items():
            try:
                current_param = self.node.get_parameter(param_name)
                original_value = current_param.value
                
                override = ParameterOverride(
                    parameter_name=param_name,
                    original_value=original_value,
                    override_value=new_value,
                    parameter_path=f"ros_parameter.{param_name}",
                    description=f"Robosync communication parameter override"
                )
                
                # Determine parameter type
                if isinstance(new_value, bool):
                    param_type = Parameter.Type.BOOL
                elif isinstance(new_value, int):
                    param_type = Parameter.Type.INTEGER
                elif isinstance(new_value, float):
                    param_type = Parameter.Type.DOUBLE
                else:
                    param_type = Parameter.Type.STRING
                
                new_param = Parameter(param_name, param_type, new_value)
                self.node.set_parameters([new_param])
                
                self.original_parameters[param_name] = override
                overrides.append(override)
                
                self.logger.debug(f"Override ROS parameter {param_name}: {original_value} -> {new_value}")
                
            except Exception as e:
                self.logger.warning(f"Could not override ROS parameter {param_name}: {e}")
        
        return overrides
    
    def _apply_config_file_overrides(self) -> List[ParameterOverride]:
        """
        Apply parameter overrides to configuration files.
        
        Returns:
            List of applied parameter overrides
        """
        overrides = []
        
        # Override Arduino configuration
        arduino_overrides = self._override_arduino_config()
        overrides.extend(arduino_overrides)
        
        # Override hardware configuration
        hardware_overrides = self._override_hardware_config()
        overrides.extend(hardware_overrides)
        
        return overrides
    
    def _override_arduino_config(self) -> List[ParameterOverride]:
        """Override Arduino configuration file with robosync parameters."""
        overrides = []
        config_path = self.config_file_paths.get('arduino_config')
        
        if not config_path or not os.path.exists(config_path):
            self.logger.warning(f"Arduino config file not found: {config_path}")
            return overrides
        
        try:
            # Load existing configuration
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
            
            # Get parameter section
            if 'arduino_bridge' not in config:
                config['arduino_bridge'] = {}
            if 'ros__parameters' not in config['arduino_bridge']:
                config['arduino_bridge']['ros__parameters'] = {}
            
            params = config['arduino_bridge']['ros__parameters']
            
            # Apply physical parameter overrides
            physical_params = self.robosync_parameters['physical_parameters']
            param_mappings = {
                'wheel_base': physical_params['wheel_base'],
                'wheel_radius': physical_params['wheel_radius'],
                'wheel_circumference': physical_params['wheel_circumference'],
                'encoder_ticks_per_rev': physical_params['encoder_ticks_per_rev'],
                'max_speed': physical_params['max_linear_velocity'],
                'max_angular_speed': physical_params['max_angular_velocity']
            }
            
            for param_name, new_value in param_mappings.items():
                original_value = params.get(param_name)
                if original_value != new_value:
                    override = ParameterOverride(
                        parameter_name=param_name,
                        original_value=original_value,
                        override_value=new_value,
                        parameter_path=f"{config_path}:arduino_bridge.ros__parameters.{param_name}",
                        description=f"Robosync physical parameter override in Arduino config"
                    )
                    
                    params[param_name] = new_value
                    self.original_parameters[f"arduino_config.{param_name}"] = override
                    overrides.append(override)
            
            # Apply communication parameter overrides
            comm_params = self.robosync_parameters['communication_parameters']
            comm_mappings = {
                'baud_rate': comm_params['baud_rate'],
                'timeout': comm_params['timeout'],
                'write_timeout': comm_params['write_timeout'],
                'port': comm_params['port']
            }
            
            for param_name, new_value in comm_mappings.items():
                original_value = params.get(param_name)
                if original_value != new_value:
                    override = ParameterOverride(
                        parameter_name=param_name,
                        original_value=original_value,
                        override_value=new_value,
                        parameter_path=f"{config_path}:arduino_bridge.ros__parameters.{param_name}",
                        description=f"Robosync communication parameter override in Arduino config"
                    )
                    
                    params[param_name] = new_value
                    self.original_parameters[f"arduino_config.{param_name}"] = override
                    overrides.append(override)
            
            # Apply PID parameter overrides
            pid_params = self.robosync_parameters['pid_parameters']
            if 'pid' not in params:
                params['pid'] = {}
            
            for param_name, new_value in pid_params.items():
                original_value = params['pid'].get(param_name)
                if original_value != new_value:
                    override = ParameterOverride(
                        parameter_name=f"pid.{param_name}",
                        original_value=original_value,
                        override_value=new_value,
                        parameter_path=f"{config_path}:arduino_bridge.ros__parameters.pid.{param_name}",
                        description=f"Robosync PID parameter override in Arduino config"
                    )
                    
                    params['pid'][param_name] = new_value
                    self.original_parameters[f"arduino_config.pid.{param_name}"] = override
                    overrides.append(override)
            
            # Write updated configuration back to file
            with open(config_path, 'w') as file:
                yaml.dump(config, file, default_flow_style=False, indent=2)
            
            self.logger.info(f"Applied {len(overrides)} overrides to Arduino config")
            
        except Exception as e:
            self.logger.error(f"Error overriding Arduino config: {e}")
        
        return overrides
    
    def _override_hardware_config(self) -> List[ParameterOverride]:
        """Override hardware configuration file with robosync parameters."""
        overrides = []
        config_path = self.config_file_paths.get('rosarduino_bridge_config')
        
        if not config_path or not os.path.exists(config_path):
            self.logger.warning(f"Hardware config file not found: {config_path}")
            return overrides
        
        try:
            # Load existing configuration
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
            
            # Apply robosync-specific overrides to hardware config
            # This would be similar to Arduino config but for hardware-specific parameters
            
            self.logger.info(f"Applied {len(overrides)} overrides to hardware config")
            
        except Exception as e:
            self.logger.error(f"Error overriding hardware config: {e}")
        
        return overrides
    
    def restore_original_parameters(self) -> OverrideResult:
        """
        Restore original parameter values, undoing all overrides.
        
        Returns:
            OverrideResult with restoration status
        """
        if not self.override_active:
            return OverrideResult(
                success=True,
                overrides_applied=[],
                errors=[],
                warnings=["No parameter overrides are currently active"]
            )
        
        restored_overrides = []
        errors = []
        warnings = []
        
        try:
            # Restore ROS parameters
            if self.node:
                ros_restored = self._restore_ros_parameters()
                restored_overrides.extend(ros_restored)
            
            # Restore configuration files
            file_restored = self._restore_config_files()
            restored_overrides.extend(file_restored)
            
            # Clear stored overrides
            self.original_parameters.clear()
            self.override_active = False
            
            self.logger.info(f"Restored {len(restored_overrides)} parameter overrides")
            
        except Exception as e:
            errors.append(f"Error restoring parameters: {str(e)}")
            self.logger.error(f"Failed to restore parameters: {e}")
        
        return OverrideResult(
            success=len(errors) == 0,
            overrides_applied=restored_overrides,
            errors=errors,
            warnings=warnings
        )
    
    def _restore_ros_parameters(self) -> List[ParameterOverride]:
        """Restore original ROS parameter values."""
        restored = []
        
        if not self.node:
            return restored
        
        for param_key, override in self.original_parameters.items():
            if override.parameter_path.startswith("ros_parameter."):
                try:
                    # Determine parameter type from original value
                    if isinstance(override.original_value, bool):
                        param_type = Parameter.Type.BOOL
                    elif isinstance(override.original_value, int):
                        param_type = Parameter.Type.INTEGER
                    elif isinstance(override.original_value, float):
                        param_type = Parameter.Type.DOUBLE
                    else:
                        param_type = Parameter.Type.STRING
                    
                    # Restore original parameter
                    restored_param = Parameter(
                        override.parameter_name, 
                        param_type, 
                        override.original_value
                    )
                    self.node.set_parameters([restored_param])
                    
                    restored.append(override)
                    self.logger.debug(
                        f"Restored ROS parameter {override.parameter_name}: "
                        f"{override.override_value} -> {override.original_value}"
                    )
                    
                except Exception as e:
                    self.logger.warning(f"Could not restore ROS parameter {override.parameter_name}: {e}")
        
        return restored
    
    def _restore_config_files(self) -> List[ParameterOverride]:
        """Restore original configuration file values."""
        restored = []
        
        # Group overrides by config file
        config_overrides = {}
        for param_key, override in self.original_parameters.items():
            if not override.parameter_path.startswith("ros_parameter."):
                config_file = override.parameter_path.split(':')[0]
                if config_file not in config_overrides:
                    config_overrides[config_file] = []
                config_overrides[config_file].append(override)
        
        # Restore each config file
        for config_file, overrides in config_overrides.items():
            try:
                file_restored = self._restore_single_config_file(config_file, overrides)
                restored.extend(file_restored)
            except Exception as e:
                self.logger.error(f"Error restoring config file {config_file}: {e}")
        
        return restored
    
    def _restore_single_config_file(self, config_file: str, overrides: List[ParameterOverride]) -> List[ParameterOverride]:
        """Restore original values in a single configuration file."""
        restored = []
        
        if not os.path.exists(config_file):
            self.logger.warning(f"Config file not found for restoration: {config_file}")
            return restored
        
        try:
            # Load current configuration
            with open(config_file, 'r') as file:
                config = yaml.safe_load(file)
            
            # Restore each override
            for override in overrides:
                # Parse parameter path to navigate config structure
                path_parts = override.parameter_path.split(':')[1].split('.')
                
                # Navigate to parameter location
                current_section = config
                for part in path_parts[:-1]:
                    if part in current_section:
                        current_section = current_section[part]
                    else:
                        self.logger.warning(f"Config path not found: {'.'.join(path_parts[:-1])}")
                        break
                else:
                    # Restore original value
                    param_name = path_parts[-1]
                    if param_name in current_section:
                        current_section[param_name] = override.original_value
                        restored.append(override)
                        self.logger.debug(
                            f"Restored config parameter {override.parameter_name}: "
                            f"{override.override_value} -> {override.original_value}"
                        )
            
            # Write restored configuration back to file
            with open(config_file, 'w') as file:
                yaml.dump(config, file, default_flow_style=False, indent=2)
            
            self.logger.info(f"Restored {len(restored)} parameters in {config_file}")
            
        except Exception as e:
            self.logger.error(f"Error restoring config file {config_file}: {e}")
        
        return restored
    
    def get_current_overrides(self) -> List[ParameterOverride]:
        """
        Get list of currently active parameter overrides.
        
        Returns:
            List of active parameter overrides
        """
        return list(self.original_parameters.values())
    
    def is_override_active(self) -> bool:
        """
        Check if parameter overrides are currently active.
        
        Returns:
            True if overrides are active, False otherwise
        """
        return self.override_active
    
    def get_robosync_parameter_summary(self) -> Dict[str, Any]:
        """
        Get summary of robosync parameter definitions.
        
        Returns:
            Dictionary containing robosync parameter summary
        """
        return {
            'physical_parameters': self.robosync_parameters['physical_parameters'].copy(),
            'communication_parameters': self.robosync_parameters['communication_parameters'].copy(),
            'pid_parameters': self.robosync_parameters['pid_parameters'].copy(),
            'motor_parameters': self.robosync_parameters['motor_parameters'].copy(),
            'override_active': self.override_active,
            'active_overrides_count': len(self.original_parameters)
        }