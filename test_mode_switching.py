#!/usr/bin/env python3
"""
Test script for mode-specific configuration system.
"""

import os
import sys
import tempfile
import yaml
from pathlib import Path

# Add the robot_control package to the path
sys.path.insert(0, str(Path(__file__).parent / 'src' / 'robot_control'))

from robot_control.configuration_manager import ConfigurationManager
from robot_control.launch_utils import LaunchModeManager


def test_configuration_manager():
    """Test the configuration manager mode detection and configuration."""
    print("Testing Configuration Manager...")
    
    # Test with simulation mode
    print("\n1. Testing simulation mode:")
    config_manager = ConfigurationManager(mode='simulation')
    
    print(f"   Operation mode: {config_manager.get_operation_mode()}")
    print(f"   Is simulation: {config_manager.is_simulation_mode()}")
    print(f"   Is hardware: {config_manager.is_hardware_mode()}")
    
    mode_config = config_manager.get_mode_specific_config()
    print(f"   Use simulation: {mode_config['use_simulation']}")
    print(f"   Use sim time: {mode_config['use_sim_time']}")
    
    launch_params = config_manager.get_launch_parameters()
    print(f"   Launch params: {launch_params}")
    
    # Test with hardware mode
    print("\n2. Testing hardware mode:")
    config_manager = ConfigurationManager(mode='hardware')
    
    print(f"   Operation mode: {config_manager.get_operation_mode()}")
    print(f"   Is simulation: {config_manager.is_simulation_mode()}")
    print(f"   Is hardware: {config_manager.is_hardware_mode()}")
    
    mode_config = config_manager.get_mode_specific_config()
    print(f"   Use simulation: {mode_config['use_simulation']}")
    print(f"   Use sim time: {mode_config['use_sim_time']}")
    
    launch_params = config_manager.get_launch_parameters()
    print(f"   Launch params: {launch_params}")


def test_launch_mode_manager():
    """Test the launch mode manager."""
    print("\n\nTesting Launch Mode Manager...")
    
    mode_manager = LaunchModeManager()
    
    print(f"Available packages: {mode_manager.available_packages}")
    print(f"Gazebo available: {mode_manager.is_gazebo_available()}")
    
    detected_mode = mode_manager.detect_operation_mode()
    print(f"Detected mode: {detected_mode}")
    
    launch_args = mode_manager.get_launch_arguments()
    print(f"Launch arguments: {launch_args}")
    
    # Test mode validation
    for mode in ['simulation', 'hardware']:
        is_valid, missing = mode_manager.validate_mode_requirements(mode)
        print(f"{mode} mode valid: {is_valid}, missing: {missing}")


def test_configuration_validation():
    """Test configuration validation."""
    print("\n\nTesting Configuration Validation...")
    
    config_manager = ConfigurationManager()
    
    # Test validation
    validation_result = config_manager.validate_configuration()
    print(f"Configuration valid: {validation_result.is_valid}")
    
    if validation_result.errors:
        print("Errors:")
        for error in validation_result.errors:
            print(f"  - {error}")
    
    if validation_result.warnings:
        print("Warnings:")
        for warning in validation_result.warnings:
            print(f"  - {warning}")
    
    if validation_result.conflicts:
        print("Conflicts:")
        for conflict in validation_result.conflicts:
            print(f"  - {conflict.parameter_name}: {conflict.description}")


def main():
    """Run all tests."""
    print("Mode-Specific Configuration System Test")
    print("=" * 50)
    
    try:
        test_configuration_manager()
        test_launch_mode_manager()
        test_configuration_validation()
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"\nERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())