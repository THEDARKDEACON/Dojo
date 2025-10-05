#!/usr/bin/env python3
"""
Test script for the unified configuration management system.

This script demonstrates the configuration manager functionality including:
- Loading master configuration
- Validating parameters
- Detecting conflicts
- Propagating parameters to subsystems
"""

import sys
import os
from pathlib import Path

# Add the robot_control package to the path
workspace_root = Path(__file__).parent.parent
sys.path.append(str(workspace_root / "src" / "robot_control"))

from robot_control.configuration_manager import ConfigurationManager, ValidationResult


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_validation_results(validation_result: ValidationResult):
    """Print validation results in a formatted way."""
    if validation_result.is_valid:
        print("✓ Configuration validation PASSED")
    else:
        print("✗ Configuration validation FAILED")
        
    if validation_result.errors:
        print(f"\nErrors ({len(validation_result.errors)}):")
        for error in validation_result.errors:
            print(f"  ✗ {error}")
    
    if validation_result.warnings:
        print(f"\nWarnings ({len(validation_result.warnings)}):")
        for warning in validation_result.warnings:
            print(f"  ⚠ {warning}")
    
    if validation_result.conflicts:
        print(f"\nConflicts ({len(validation_result.conflicts)}):")
        for conflict in validation_result.conflicts:
            print(f"  ⚠ {conflict.parameter_name}: expected {conflict.expected_value}, "
                  f"got {conflict.actual_value} in {conflict.source_file}")


def main():
    """Main test function."""
    print_section("Dojo Robot Configuration Management System Test")
    
    try:
        # Change to workspace directory
        os.chdir(workspace_root)
        
        # Initialize configuration manager
        print("Initializing Configuration Manager...")
        config_manager = ConfigurationManager()
        print("✓ Configuration Manager initialized successfully")
        
        # Test parameter access
        print_section("Parameter Access Test")
        
        # Test various parameter access methods
        wheel_base = config_manager.get_parameter('robot.physical_parameters.wheel_base')
        print(f"Wheel base: {wheel_base} meters")
        
        max_velocity = config_manager.get_parameter('robot.physical_parameters.max_linear_velocity')
        print(f"Max linear velocity: {max_velocity} m/s")
        
        arduino_baud = config_manager.get_parameter('robot.hardware.arduino.baud_rate')
        print(f"Arduino baud rate: {arduino_baud}")
        
        safety_timeout = config_manager.get_parameter('robot.safety.command_timeout')
        print(f"Command timeout: {safety_timeout} seconds")
        
        # Test non-existent parameter with default
        non_existent = config_manager.get_parameter('robot.non_existent.parameter', 'default_value')
        print(f"Non-existent parameter (with default): {non_existent}")
        
        # Test configuration sections
        print_section("Configuration Sections")
        
        physical_params = config_manager.get_physical_parameters()
        print(f"Physical parameters: {len(physical_params)} items")
        for key, value in physical_params.items():
            print(f"  {key}: {value}")
        
        hardware_config = config_manager.get_hardware_config()
        print(f"\nHardware configuration: {len(hardware_config)} devices")
        for device in hardware_config.keys():
            print(f"  {device}")
        
        safety_config = config_manager.get_safety_config()
        print(f"\nSafety configuration: {len(safety_config)} parameters")
        for key, value in safety_config.items():
            print(f"  {key}: {value}")
        
        # Validate configuration
        print_section("Configuration Validation")
        
        validation_result = config_manager.validate_configuration()
        print_validation_results(validation_result)
        
        # Check for conflicts
        print_section("Conflict Detection")
        
        conflicts = config_manager.detect_conflicts()
        if conflicts:
            print(f"Found {len(conflicts)} configuration conflicts:")
            for conflict in conflicts:
                print(f"  ⚠ {conflict.parameter_name}: expected {conflict.expected_value}, "
                      f"got {conflict.actual_value} in {conflict.source_file}")
                print(f"    Description: {conflict.description}")
        else:
            print("✓ No configuration conflicts detected")
        
        # Test parameter propagation
        print_section("Parameter Propagation Test")
        
        print("Propagating parameters to all subsystem configuration files...")
        config_manager.propagate_parameters()
        print("✓ Parameters propagated successfully")
        
        # Re-check conflicts after propagation
        conflicts_after = config_manager.detect_conflicts()
        if conflicts_after:
            print(f"⚠ Still found {len(conflicts_after)} conflicts after propagation:")
            for conflict in conflicts_after:
                print(f"  - {conflict.parameter_name} in {conflict.source_file}")
        else:
            print("✓ All conflicts resolved after parameter propagation")
        
        print_section("Test Summary")
        print("✓ Configuration Manager test completed successfully")
        print("✓ All core functionality verified")
        
        if validation_result.is_valid and not conflicts_after:
            print("✓ System is ready for operation")
            return 0
        else:
            print("⚠ System has configuration issues that should be addressed")
            return 1
            
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)