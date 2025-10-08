#!/usr/bin/env python3
"""
Parameter Reversion Script

This script ensures that all robot physical parameters are reverted to their
original Dojo values, clearing any robosync overrides that may be active.
"""

import os
import sys
import yaml
import logging
from pathlib import Path

# Add the robot_control module to the path
sys.path.insert(0, os.path.dirname(__file__))

try:
    from configuration_override import ConfigurationOverride
except ImportError:
    print("ConfigurationOverride not available, checking config files only")
    ConfigurationOverride = None


def get_original_dojo_parameters():
    """Get the original Dojo physical parameters."""
    return {
        'physical_parameters': {
            'wheel_base': 0.26,                    # Original Dojo value (meters)
            'wheel_radius': 0.033,                 # Original Dojo value (meters)
            'wheel_circumference': 0.207,          # Original Dojo value
            'encoder_ticks_per_rev': 20,           # This matches robosync, so keep it
            'max_linear_velocity': 0.5,            # Conservative limit
            'max_angular_velocity': 1.0            # Conservative limit
        },
        'communication_parameters': {
            'baud_rate': 115200,                   # Keep robosync compatibility
            'timeout': 1.0,                        # seconds
            'write_timeout': 1.0,                  # seconds
            'port': '/dev/ttyACM0'                # default Arduino port
        },
        'pid_parameters': {
            'kp': 20.0,                           # Keep robosync PID values (they work)
            'kd': 12.0,
            'ki': 0.0,
            'ko': 50,
            'sample_time': 0.1
        }
    }


def revert_configuration_file(config_path, original_params):
    """Revert a configuration file to original Dojo parameters."""
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        return False
    
    try:
        # Load current configuration
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        
        changes_made = False
        
        # Handle arduino_bridge configuration
        if 'arduino_bridge' in config and 'ros__parameters' in config['arduino_bridge']:
            params = config['arduino_bridge']['ros__parameters']
            
            # Revert physical parameters
            physical = original_params['physical_parameters']
            for param_name, original_value in physical.items():
                if param_name in params and params[param_name] != original_value:
                    print(f"Reverting {param_name}: {params[param_name]} -> {original_value}")
                    params[param_name] = original_value
                    changes_made = True
            
            # Keep communication parameters that work (baud_rate, timeout)
            # Keep PID parameters that work
            
        # Handle arduino_driver configuration
        elif 'arduino_driver' in config and 'ros__parameters' in config['arduino_driver']:
            params = config['arduino_driver']['ros__parameters']
            
            # Revert physical parameters
            physical = original_params['physical_parameters']
            for param_name, original_value in physical.items():
                if param_name in params and params[param_name] != original_value:
                    print(f"Reverting {param_name}: {params[param_name]} -> {original_value}")
                    params[param_name] = original_value
                    changes_made = True
        
        # Write back if changes were made
        if changes_made:
            with open(config_path, 'w') as file:
                yaml.dump(config, file, default_flow_style=False, indent=2)
            print(f"✓ Reverted parameters in {config_path}")
            return True
        else:
            print(f"✓ No changes needed in {config_path}")
            return True
            
    except Exception as e:
        print(f"✗ Error reverting {config_path}: {e}")
        return False


def revert_runtime_overrides():
    """Revert any runtime parameter overrides."""
    if ConfigurationOverride is None:
        print("ConfigurationOverride class not available")
        return True
    
    try:
        config_override = ConfigurationOverride()
        
        if config_override.is_override_active():
            print("Found active parameter overrides, reverting...")
            result = config_override.restore_original_parameters()
            
            if result.success:
                print(f"✓ Successfully reverted {len(result.overrides_applied)} runtime overrides")
                return True
            else:
                print(f"✗ Failed to revert runtime overrides: {result.errors}")
                return False
        else:
            print("✓ No active runtime overrides found")
            return True
            
    except Exception as e:
        print(f"✗ Error checking runtime overrides: {e}")
        return False


def main():
    """Main reversion function."""
    print("Reverting robot physical parameters to original Dojo values...\n")
    
    # Get original parameters
    original_params = get_original_dojo_parameters()
    
    # Find workspace root
    current_dir = Path(__file__).resolve()
    workspace_root = None
    for parent in current_dir.parents:
        if (parent / 'src').exists():
            workspace_root = str(parent)
            break
    
    if not workspace_root:
        print("✗ Could not find workspace root")
        return 1
    
    print(f"Workspace root: {workspace_root}")
    
    # Configuration files to check/revert
    config_files = [
        os.path.join(workspace_root, 'src/robot_control/config/arduino_config.yaml'),
        os.path.join(workspace_root, 'src/robot_hardware/config/rosarduino_bridge_config.yaml'),
        os.path.join(workspace_root, 'config/robot_config.yaml')
    ]
    
    success = True
    
    # Revert configuration files
    print("\nChecking configuration files...")
    for config_file in config_files:
        if not revert_configuration_file(config_file, original_params):
            success = False
    
    # Revert runtime overrides
    print("\nChecking runtime overrides...")
    if not revert_runtime_overrides():
        success = False
    
    # Summary
    print(f"\n{'='*50}")
    if success:
        print("🎉 Parameter reversion completed successfully!")
        print("\nOriginal Dojo physical parameters:")
        physical = original_params['physical_parameters']
        for param, value in physical.items():
            print(f"  {param}: {value}")
    else:
        print("❌ Some errors occurred during parameter reversion")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())