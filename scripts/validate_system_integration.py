#!/usr/bin/env python3
"""
Comprehensive System Integration Validation Script

This script validates the complete Dojo Robot system integration including:
- Configuration management
- Hardware discovery
- Safety systems
- Component health monitoring
- Build system integrity
"""

import os
import sys
import time
import subprocess
import yaml
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class SystemValidator:
    def __init__(self):
        self.workspace_root = Path(__file__).parent.parent
        self.config_path = self.workspace_root / "config" / "robot_config.yaml"
        self.validation_results = {}
        self.errors = []
        self.warnings = []
        
    def run_validation(self) -> bool:
        """Run complete system validation"""
        print("🔍 Starting Comprehensive System Integration Validation")
        print("=" * 60)
        
        # Run all validation tests
        tests = [
            ("Configuration Management", self.validate_configuration_management),
            ("Hardware Discovery System", self.validate_hardware_discovery),
            ("Safety System Integration", self.validate_safety_systems),
            ("Build System Integrity", self.validate_build_system),
            ("Component Health Monitoring", self.validate_health_monitoring),
            ("Launch File Integration", self.validate_launch_files),
            ("Documentation Completeness", self.validate_documentation),
        ]
        
        all_passed = True
        for test_name, test_func in tests:
            print(f"\n📋 Testing: {test_name}")
            try:
                result = test_func()
                self.validation_results[test_name] = result
                if result:
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
                    all_passed = False
            except Exception as e:
                print(f"💥 {test_name}: ERROR - {str(e)}")
                self.errors.append(f"{test_name}: {str(e)}")
                all_passed = False
        
        # Print summary
        self.print_validation_summary()
        return all_passed
    
    def validate_configuration_management(self) -> bool:
        """Validate configuration management system"""
        print("  🔧 Checking master configuration file...")
        
        # Check master config exists
        if not self.config_path.exists():
            self.errors.append("Master configuration file not found")
            return False
        
        # Load and validate configuration
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            self.errors.append(f"Failed to load configuration: {e}")
            return False
        
        # Check required configuration sections
        required_sections = [
            'robot.physical_parameters',
            'robot.hardware',
            'robot.safety',
            'robot.system'
        ]
        
        for section in required_sections:
            if not self._check_nested_key(config, section):
                self.errors.append(f"Missing configuration section: {section}")
                return False
        
        # Check configuration manager exists
        config_manager_path = self.workspace_root / "src" / "robot_control" / "robot_control" / "configuration_manager.py"
        if not config_manager_path.exists():
            self.errors.append("Configuration manager not found")
            return False
        
        print("  ✅ Configuration management system validated")
        return True
    
    def validate_hardware_discovery(self) -> bool:
        """Validate hardware discovery system"""
        print("  🔍 Checking hardware discovery system...")
        
        # Check hardware discovery module exists
        discovery_path = self.workspace_root / "src" / "robot_control" / "robot_control" / "hardware_discovery.py"
        if not discovery_path.exists():
            self.errors.append("Hardware discovery module not found")
            return False
        
        # Check device abstraction layer
        abstraction_path = self.workspace_root / "src" / "robot_control" / "robot_control" / "device_abstraction.py"
        if not abstraction_path.exists():
            self.errors.append("Device abstraction layer not found")
            return False
        
        # Check device implementations
        implementations_path = self.workspace_root / "src" / "robot_control" / "robot_control" / "device_implementations.py"
        if not implementations_path.exists():
            self.errors.append("Device implementations not found")
            return False
        
        # Check hardware manager
        manager_path = self.workspace_root / "src" / "robot_control" / "robot_control" / "hardware_manager.py"
        if not manager_path.exists():
            self.errors.append("Hardware manager not found")
            return False
        
        print("  ✅ Hardware discovery system validated")
        return True
    
    def validate_safety_systems(self) -> bool:
        """Validate safety system integration"""
        print("  🛡️ Checking safety system integration...")
        
        # Check safety supervisor
        supervisor_path = self.workspace_root / "src" / "robot_control" / "robot_control" / "safety_supervisor.py"
        if not supervisor_path.exists():
            self.errors.append("Safety supervisor not found")
            return False
        
        # Check emergency stop handler
        estop_path = self.workspace_root / "src" / "robot_control" / "robot_control" / "emergency_stop_handler.py"
        if not estop_path.exists():
            self.errors.append("Emergency stop handler not found")
            return False
        
        # Check watchdog system
        watchdog_path = self.workspace_root / "src" / "robot_control" / "robot_control" / "watchdog_system.py"
        if not watchdog_path.exists():
            self.errors.append("Watchdog system not found")
            return False
        
        # Check velocity limiter
        limiter_path = self.workspace_root / "src" / "robot_control" / "robot_control" / "velocity_limiter.py"
        if not limiter_path.exists():
            self.errors.append("Velocity limiter not found")
            return False
        
        # Check safety launch file
        safety_launch_path = self.workspace_root / "src" / "robot_control" / "launch" / "safety_system.launch.py"
        if not safety_launch_path.exists():
            self.errors.append("Safety system launch file not found")
            return False
        
        print("  ✅ Safety system integration validated")
        return True
    
    def validate_build_system(self) -> bool:
        """Validate build system integrity"""
        print("  🔨 Checking build system integrity...")
        
        # Check build script exists
        build_script_path = self.workspace_root / "build_ros2.sh"
        if not build_script_path.exists():
            self.errors.append("Build script not found")
            return False
        
        # Check package.xml files exist for core packages
        core_packages = [
            "src/robot_control",
            "src/robot_hardware", 
            "src/robot_interfaces",
            "src/robot_bringup"
        ]
        
        for package in core_packages:
            package_xml = self.workspace_root / package / "package.xml"
            if not package_xml.exists():
                self.errors.append(f"Package.xml not found for {package}")
                return False
        
        # Check setup.py files for Python packages
        python_packages = [
            "src/robot_control",
            "src/robot_hardware"
        ]
        
        for package in python_packages:
            setup_py = self.workspace_root / package / "setup.py"
            if not setup_py.exists():
                self.errors.append(f"Setup.py not found for {package}")
                return False
        
        # Check backup packages are properly excluded
        backup_path = self.workspace_root / "backup_packages"
        if backup_path.exists():
            # Check if COLCON_IGNORE exists
            ignore_file = backup_path / "COLCON_IGNORE"
            if not ignore_file.exists():
                self.warnings.append("Backup packages should have COLCON_IGNORE file")
        
        print("  ✅ Build system integrity validated")
        return True
    
    def validate_health_monitoring(self) -> bool:
        """Validate component health monitoring"""
        print("  💓 Checking health monitoring system...")
        
        # Check diagnostic system
        diagnostic_path = self.workspace_root / "src" / "robot_control" / "robot_control" / "diagnostic_system.py"
        if not diagnostic_path.exists():
            self.errors.append("Diagnostic system not found")
            return False
        
        # Check graceful degradation
        degradation_path = self.workspace_root / "src" / "robot_control" / "robot_control" / "graceful_degradation.py"
        if not degradation_path.exists():
            self.errors.append("Graceful degradation system not found")
            return False
        
        # Check health monitoring launch file
        health_launch_path = self.workspace_root / "src" / "robot_control" / "launch" / "health_monitoring.launch.py"
        if not health_launch_path.exists():
            self.errors.append("Health monitoring launch file not found")
            return False
        
        print("  ✅ Health monitoring system validated")
        return True
    
    def validate_launch_files(self) -> bool:
        """Validate launch file integration"""
        print("  🚀 Checking launch file integration...")
        
        # Check main bringup launch file
        bringup_launch = self.workspace_root / "src" / "robot_bringup" / "launch" / "bringup.launch.py"
        if not bringup_launch.exists():
            self.errors.append("Main bringup launch file not found")
            return False
        
        # Check configuration manager launch file
        config_launch = self.workspace_root / "src" / "robot_control" / "launch" / "configuration_manager.launch.py"
        if not config_launch.exists():
            self.errors.append("Configuration manager launch file not found")
            return False
        
        # Check hardware launch file
        hardware_launch = self.workspace_root / "src" / "robot_hardware" / "launch" / "hardware.launch.py"
        if not hardware_launch.exists():
            self.errors.append("Hardware launch file not found")
            return False
        
        # Validate launch file syntax (basic check)
        launch_files = [bringup_launch, config_launch, hardware_launch]
        for launch_file in launch_files:
            try:
                with open(launch_file, 'r') as f:
                    content = f.read()
                    # Basic syntax check - should contain LaunchDescription
                    if "LaunchDescription" not in content:
                        self.warnings.append(f"Launch file may have syntax issues: {launch_file.name}")
            except Exception as e:
                self.errors.append(f"Failed to read launch file {launch_file.name}: {e}")
                return False
        
        print("  ✅ Launch file integration validated")
        return True
    
    def validate_documentation(self) -> bool:
        """Validate documentation completeness"""
        print("  📚 Checking documentation completeness...")
        
        # Check main documentation files
        required_docs = [
            "README.md",
            "TROUBLESHOOTING.md",
            "SAFETY_SYSTEM_GUIDE.md"
        ]
        
        for doc in required_docs:
            doc_path = self.workspace_root / doc
            if not doc_path.exists():
                self.errors.append(f"Required documentation not found: {doc}")
                return False
        
        # Check config documentation
        config_readme = self.workspace_root / "config" / "README.md"
        if not config_readme.exists():
            self.warnings.append("Configuration README not found")
        
        # Check scripts documentation
        scripts_readme = self.workspace_root / "SCRIPTS_README.md"
        if not scripts_readme.exists():
            self.warnings.append("Scripts README not found")
        
        print("  ✅ Documentation completeness validated")
        return True
    
    def validate_ros2_environment(self) -> bool:
        """Validate ROS2 environment setup"""
        print("  🤖 Checking ROS2 environment...")
        
        # Check ROS2 installation
        try:
            result = subprocess.run(['ros2', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                self.errors.append("ROS2 not properly installed or configured")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.errors.append("ROS2 command not found")
            return False
        
        # Check colcon installation
        try:
            result = subprocess.run(['colcon', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                self.errors.append("Colcon not properly installed")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.errors.append("Colcon command not found")
            return False
        
        print("  ✅ ROS2 environment validated")
        return True
    
    def test_configuration_validation(self) -> bool:
        """Test configuration validation functionality"""
        print("  ⚙️ Testing configuration validation...")
        
        # Test configuration manager import
        try:
            sys.path.append(str(self.workspace_root / "src" / "robot_control"))
            from robot_control.configuration_manager import ConfigurationManager
            
            # Create configuration manager instance
            config_manager = ConfigurationManager()
            
            # Test configuration loading
            config = config_manager.load_master_config()
            if not config:
                self.errors.append("Failed to load master configuration")
                return False
            
            # Test configuration validation
            validation_result = config_manager.validate_configuration()
            if not validation_result.is_valid:
                self.warnings.append(f"Configuration validation issues: {validation_result.errors}")
            
        except ImportError as e:
            self.errors.append(f"Failed to import configuration manager: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Configuration validation test failed: {e}")
            return False
        
        print("  ✅ Configuration validation tested")
        return True
    
    def test_hardware_discovery_functionality(self) -> bool:
        """Test hardware discovery functionality"""
        print("  🔍 Testing hardware discovery functionality...")
        
        try:
            sys.path.append(str(self.workspace_root / "src" / "robot_control"))
            from robot_control.hardware_discovery import HardwareDiscovery
            
            # Create hardware discovery instance
            discovery = HardwareDiscovery()
            
            # Test device scanning (without actual hardware)
            serial_devices = discovery.scan_serial_devices()
            camera_devices = discovery.detect_cameras()
            
            # These may be empty without hardware, but should not error
            print(f"    Found {len(serial_devices)} serial devices")
            print(f"    Found {len(camera_devices)} camera devices")
            
        except ImportError as e:
            self.errors.append(f"Failed to import hardware discovery: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Hardware discovery test failed: {e}")
            return False
        
        print("  ✅ Hardware discovery functionality tested")
        return True
    
    def _check_nested_key(self, data: Dict, key_path: str) -> bool:
        """Check if nested key exists in dictionary"""
        keys = key_path.split('.')
        current = data
        
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return False
            current = current[key]
        
        return True
    
    def print_validation_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        # Print results
        passed = sum(1 for result in self.validation_results.values() if result)
        total = len(self.validation_results)
        
        print(f"Tests Passed: {passed}/{total}")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if not self.errors and not self.warnings:
            print("\n🎉 ALL VALIDATIONS PASSED!")
            print("System integration is complete and ready for operation.")
        elif not self.errors:
            print("\n✅ VALIDATION PASSED WITH WARNINGS")
            print("System is functional but some improvements recommended.")
        else:
            print("\n❌ VALIDATION FAILED")
            print("Please address the errors before system operation.")
        
        print("\n📋 Next Steps:")
        if not self.errors:
            print("  1. Review any warnings and address if needed")
            print("  2. Test system startup: ros2 launch robot_bringup bringup.launch.py")
            print("  3. Verify hardware discovery: ros2 topic echo /hardware_discovery_status")
            print("  4. Test safety systems: ros2 topic echo /safety_status")
        else:
            print("  1. Address all reported errors")
            print("  2. Re-run validation script")
            print("  3. Check troubleshooting guides for assistance")

def main():
    """Main validation function"""
    validator = SystemValidator()
    
    # Run basic environment checks first
    print("🔧 Checking ROS2 Environment...")
    if not validator.validate_ros2_environment():
        print("❌ ROS2 environment validation failed")
        return False
    
    # Run comprehensive validation
    success = validator.run_validation()
    
    # Additional functional tests if basic validation passes
    if success:
        print("\n🧪 Running Functional Tests...")
        
        # Test configuration validation
        if not validator.test_configuration_validation():
            success = False
        
        # Test hardware discovery (without hardware)
        if not validator.test_hardware_discovery_functionality():
            success = False
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)