#!/usr/bin/env python3
"""
Test script for ConfigurationOverride class

Simple test to verify the configuration override functionality works correctly.
"""

import sys
import os
import tempfile
import yaml
from pathlib import Path

# Add the robot_control module to the path
sys.path.insert(0, os.path.dirname(__file__))

from configuration_override import ConfigurationOverride, OverrideResult


def test_robosync_parameter_validation():
    """Test robosync parameter validation."""
    print("Testing robosync parameter validation...")
    
    config_override = ConfigurationOverride()
    result = config_override.validate_robosync_parameters()
    
    print(f"Validation success: {result.success}")
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
    
    assert result.success, f"Parameter validation failed: {result.errors}"
    print("✓ Parameter validation passed")


def test_parameter_definitions():
    """Test that all required robosync parameters are defined."""
    print("\nTesting parameter definitions...")
    
    config_override = ConfigurationOverride()
    params = config_override.get_robosync_parameter_summary()
    
    # Check physical parameters
    physical = params['physical_parameters']
    assert physical['wheel_base'] == 0.19, f"Expected wheel_base 0.19, got {physical['wheel_base']}"
    assert physical['wheel_radius'] == 0.035, f"Expected wheel_radius 0.035, got {physical['wheel_radius']}"
    assert physical['encoder_ticks_per_rev'] == 20, f"Expected encoder_ticks_per_rev 20, got {physical['encoder_ticks_per_rev']}"
    
    # Check communication parameters
    comm = params['communication_parameters']
    assert comm['baud_rate'] == 115200, f"Expected baud_rate 115200, got {comm['baud_rate']}"
    
    # Check PID parameters
    pid = params['pid_parameters']
    assert pid['kp'] == 20.0, f"Expected kp 20.0, got {pid['kp']}"
    assert pid['kd'] == 12.0, f"Expected kd 12.0, got {pid['kd']}"
    assert pid['ki'] == 0.0, f"Expected ki 0.0, got {pid['ki']}"
    assert pid['ko'] == 50, f"Expected ko 50, got {pid['ko']}"
    
    print("✓ All required parameters are correctly defined")


def test_config_file_override():
    """Test configuration file override functionality."""
    print("\nTesting configuration file override...")
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
        test_config = {
            'arduino_bridge': {
                'ros__parameters': {
                    'wheel_base': 0.26,  # Original Dojo value
                    'wheel_radius': 0.033,  # Original Dojo value
                    'baud_rate': 57600,  # Different baud rate
                    'encoder_ticks_per_rev': 40,  # Different encoder value
                    'pid': {
                        'kp': 10.0,  # Different PID values
                        'kd': 5.0,
                        'ki': 1.0,
                        'ko': 25
                    }
                }
            }
        }
        yaml.dump(test_config, temp_file, default_flow_style=False)
        temp_file_path = temp_file.name
    
    try:
        # Create ConfigurationOverride with modified config path
        config_override = ConfigurationOverride()
        config_override.config_file_paths['arduino_config'] = temp_file_path
        
        # Apply overrides
        result = config_override.apply_robosync_overrides()
        print(f"Override application success: {result.success}")
        print(f"Overrides applied: {len(result.overrides_applied)}")
        
        # Verify the file was modified
        with open(temp_file_path, 'r') as file:
            modified_config = yaml.safe_load(file)
        
        params = modified_config['arduino_bridge']['ros__parameters']
        
        # Check that robosync values were applied
        assert params['wheel_base'] == 0.19, f"Expected wheel_base 0.19, got {params['wheel_base']}"
        assert params['wheel_radius'] == 0.035, f"Expected wheel_radius 0.035, got {params['wheel_radius']}"
        assert params['baud_rate'] == 115200, f"Expected baud_rate 115200, got {params['baud_rate']}"
        assert params['encoder_ticks_per_rev'] == 20, f"Expected encoder_ticks_per_rev 20, got {params['encoder_ticks_per_rev']}"
        
        # Check PID parameters
        assert params['pid']['kp'] == 20.0, f"Expected kp 20.0, got {params['pid']['kp']}"
        assert params['pid']['kd'] == 12.0, f"Expected kd 12.0, got {params['pid']['kd']}"
        assert params['pid']['ki'] == 0.0, f"Expected ki 0.0, got {params['pid']['ki']}"
        assert params['pid']['ko'] == 50, f"Expected ko 50, got {params['pid']['ko']}"
        
        print("✓ Configuration file override successful")
        
        # Test restoration
        restore_result = config_override.restore_original_parameters()
        print(f"Restoration success: {restore_result.success}")
        
        # Verify original values were restored
        with open(temp_file_path, 'r') as file:
            restored_config = yaml.safe_load(file)
        
        restored_params = restored_config['arduino_bridge']['ros__parameters']
        assert restored_params['wheel_base'] == 0.26, f"Expected restored wheel_base 0.26, got {restored_params['wheel_base']}"
        assert restored_params['wheel_radius'] == 0.033, f"Expected restored wheel_radius 0.033, got {restored_params['wheel_radius']}"
        
        print("✓ Parameter restoration successful")
        
    finally:
        # Clean up temporary file
        os.unlink(temp_file_path)


def test_override_status():
    """Test override status tracking."""
    print("\nTesting override status tracking...")
    
    config_override = ConfigurationOverride()
    
    # Initially no overrides should be active
    assert not config_override.is_override_active(), "Expected no active overrides initially"
    assert len(config_override.get_current_overrides()) == 0, "Expected no current overrides initially"
    
    print("✓ Initial override status correct")


def main():
    """Run all tests."""
    print("Running ConfigurationOverride tests...\n")
    
    try:
        test_robosync_parameter_validation()
        test_parameter_definitions()
        test_config_file_override()
        test_override_status()
        
        print("\n🎉 All tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())