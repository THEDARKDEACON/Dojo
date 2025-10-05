#!/usr/bin/env python3
"""
System Structure Validation Script

This script validates the file structure and code integrity of the Dojo Robot system
without requiring ROS2 to be running.
"""

import os
import sys
import yaml
import ast
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class StructureValidator:
    def __init__(self):
        self.workspace_root = Path(__file__).parent.parent
        self.config_path = self.workspace_root / "config" / "robot_config.yaml"
        self.validation_results = {}
        self.errors = []
        self.warnings = []
        
    def run_validation(self) -> bool:
        """Run complete structure validation"""
        print("🔍 Starting System Structure Validation")
        print("=" * 60)
        
        # Run all validation tests
        tests = [
            ("Configuration Files", self.validate_configuration_files),
            ("Python Code Structure", self.validate_python_code),
            ("Launch Files", self.validate_launch_files),
            ("Package Structure", self.validate_package_structure),
            ("Documentation", self.validate_documentation),
            ("Build System", self.validate_build_system),
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
    
    def validate_configuration_files(self) -> bool:
        """Validate configuration file structure and content"""
        print("  ⚙️ Checking configuration files...")
        
        # Check master config exists and is valid YAML
        if not self.config_path.exists():
            self.errors.append("Master configuration file not found")
            return False
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            self.errors.append(f"Failed to load configuration: {e}")
            return False
        
        # Check required configuration sections
        required_sections = [
            ('robot', dict),
            ('robot.physical_parameters', dict),
            ('robot.hardware', dict),
            ('robot.safety', dict),
            ('robot.system', dict)
        ]
        
        for section_path, expected_type in required_sections:
            if not self._check_nested_key_type(config, section_path, expected_type):
                self.errors.append(f"Missing or invalid configuration section: {section_path}")
                return False
        
        # Check specific required parameters
        required_params = [
            'robot.physical_parameters.wheel_base',
            'robot.physical_parameters.wheel_radius',
            'robot.physical_parameters.max_linear_velocity',
            'robot.physical_parameters.max_angular_velocity',
            'robot.safety.emergency_stop_timeout',
            'robot.safety.obstacle_stop_distance',
            'robot.safety.command_timeout',
            'robot.safety.watchdog_interval'
        ]
        
        for param in required_params:
            if not self._check_nested_key(config, param):
                self.errors.append(f"Missing required parameter: {param}")
                return False
        
        print("  ✅ Configuration files validated")
        return True
    
    def validate_python_code(self) -> bool:
        """Validate Python code structure and syntax"""
        print("  🐍 Checking Python code structure...")
        
        # Core Python modules to check
        core_modules = [
            "src/robot_control/robot_control/configuration_manager.py",
            "src/robot_control/robot_control/hardware_discovery.py",
            "src/robot_control/robot_control/device_abstraction.py",
            "src/robot_control/robot_control/device_implementations.py",
            "src/robot_control/robot_control/hardware_manager.py",
            "src/robot_control/robot_control/safety_supervisor.py",
            "src/robot_control/robot_control/emergency_stop_handler.py",
            "src/robot_control/robot_control/watchdog_system.py",
            "src/robot_control/robot_control/velocity_limiter.py",
            "src/robot_control/robot_control/diagnostic_system.py",
            "src/robot_control/robot_control/graceful_degradation.py"
        ]
        
        for module_path in core_modules:
            full_path = self.workspace_root / module_path
            if not full_path.exists():
                self.errors.append(f"Core module not found: {module_path}")
                return False
            
            # Check Python syntax
            try:
                with open(full_path, 'r') as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError as e:
                self.errors.append(f"Syntax error in {module_path}: {e}")
                return False
            except Exception as e:
                self.errors.append(f"Failed to parse {module_path}: {e}")
                return False
        
        # Check for required classes in key modules
        class_checks = [
            ("src/robot_control/robot_control/configuration_manager.py", "ConfigurationManager"),
            ("src/robot_control/robot_control/hardware_discovery.py", "HardwareDiscovery"),
            ("src/robot_control/robot_control/safety_supervisor.py", "SafetySupervisor"),
            ("src/robot_control/robot_control/hardware_manager.py", "EnhancedHardwareManager")
        ]
        
        for module_path, class_name in class_checks:
            full_path = self.workspace_root / module_path
            try:
                with open(full_path, 'r') as f:
                    content = f.read()
                if f"class {class_name}" not in content:
                    self.warnings.append(f"Expected class {class_name} not found in {module_path}")
            except Exception as e:
                self.warnings.append(f"Could not check class in {module_path}: {e}")
        
        print("  ✅ Python code structure validated")
        return True
    
    def validate_launch_files(self) -> bool:
        """Validate launch file structure"""
        print("  🚀 Checking launch files...")
        
        # Core launch files to check
        launch_files = [
            "src/robot_bringup/launch/bringup.launch.py",
            "src/robot_control/launch/configuration_manager.launch.py",
            "src/robot_control/launch/safety_system.launch.py",
            "src/robot_control/launch/health_monitoring.launch.py",
            "src/robot_hardware/launch/hardware.launch.py"
        ]
        
        for launch_file in launch_files:
            full_path = self.workspace_root / launch_file
            if not full_path.exists():
                self.errors.append(f"Launch file not found: {launch_file}")
                return False
            
            # Check Python syntax
            try:
                with open(full_path, 'r') as f:
                    content = f.read()
                ast.parse(content)
                
                # Check for LaunchDescription
                if "LaunchDescription" not in content:
                    self.warnings.append(f"Launch file may be missing LaunchDescription: {launch_file}")
                
            except SyntaxError as e:
                self.errors.append(f"Syntax error in {launch_file}: {e}")
                return False
            except Exception as e:
                self.errors.append(f"Failed to parse {launch_file}: {e}")
                return False
        
        print("  ✅ Launch files validated")
        return True
    
    def validate_package_structure(self) -> bool:
        """Validate ROS2 package structure"""
        print("  📦 Checking package structure...")
        
        # Core packages to check
        packages = [
            "src/robot_control",
            "src/robot_hardware",
            "src/robot_interfaces",
            "src/robot_bringup"
        ]
        
        for package in packages:
            package_path = self.workspace_root / package
            
            # Check package.xml exists
            package_xml = package_path / "package.xml"
            if not package_xml.exists():
                self.errors.append(f"package.xml not found for {package}")
                return False
            
            # Check package.xml is valid XML
            try:
                import xml.etree.ElementTree as ET
                ET.parse(package_xml)
            except Exception as e:
                self.errors.append(f"Invalid package.xml for {package}: {e}")
                return False
            
            # Check setup.py for Python packages
            if package in ["src/robot_control", "src/robot_hardware"]:
                setup_py = package_path / "setup.py"
                if not setup_py.exists():
                    self.errors.append(f"setup.py not found for {package}")
                    return False
                
                # Check setup.py syntax
                try:
                    with open(setup_py, 'r') as f:
                        content = f.read()
                    ast.parse(content)
                except Exception as e:
                    self.errors.append(f"Invalid setup.py for {package}: {e}")
                    return False
        
        print("  ✅ Package structure validated")
        return True
    
    def validate_documentation(self) -> bool:
        """Validate documentation completeness"""
        print("  📚 Checking documentation...")
        
        # Required documentation files
        required_docs = [
            ("README.md", "Main documentation"),
            ("TROUBLESHOOTING.md", "Troubleshooting guide"),
            ("SAFETY_SYSTEM_GUIDE.md", "Safety system guide")
        ]
        
        for doc_file, description in required_docs:
            doc_path = self.workspace_root / doc_file
            if not doc_path.exists():
                self.errors.append(f"{description} not found: {doc_file}")
                return False
            
            # Check file is not empty
            try:
                with open(doc_path, 'r') as f:
                    content = f.read().strip()
                if len(content) < 100:  # Minimum content check
                    self.warnings.append(f"{description} appears to be too short: {doc_file}")
            except Exception as e:
                self.warnings.append(f"Could not read {doc_file}: {e}")
        
        # Check for additional documentation
        optional_docs = [
            ("config/README.md", "Configuration documentation"),
            ("SCRIPTS_README.md", "Scripts documentation"),
            ("MODE_SWITCHING_README.md", "Mode switching documentation")
        ]
        
        for doc_file, description in optional_docs:
            doc_path = self.workspace_root / doc_file
            if not doc_path.exists():
                self.warnings.append(f"Optional {description} not found: {doc_file}")
        
        print("  ✅ Documentation validated")
        return True
    
    def validate_build_system(self) -> bool:
        """Validate build system files"""
        print("  🔨 Checking build system...")
        
        # Check build script
        build_script = self.workspace_root / "build_ros2.sh"
        if not build_script.exists():
            self.errors.append("Build script not found: build_ros2.sh")
            return False
        
        # Check build script is executable
        if not os.access(build_script, os.X_OK):
            self.warnings.append("Build script is not executable")
        
        # Check for backup packages exclusion
        backup_path = self.workspace_root / "backup_packages"
        if backup_path.exists():
            ignore_file = backup_path / "COLCON_IGNORE"
            if not ignore_file.exists():
                self.warnings.append("Backup packages should have COLCON_IGNORE file")
        
        # Check requirements file
        requirements_file = self.workspace_root / "requirements.txt"
        if not requirements_file.exists():
            self.warnings.append("Requirements file not found")
        
        print("  ✅ Build system validated")
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
    
    def _check_nested_key_type(self, data: Dict, key_path: str, expected_type: type) -> bool:
        """Check if nested key exists and has expected type"""
        keys = key_path.split('.')
        current = data
        
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return False
            current = current[key]
        
        return isinstance(current, expected_type)
    
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
            print("System structure is complete and ready for ROS2 testing.")
        elif not self.errors:
            print("\n✅ VALIDATION PASSED WITH WARNINGS")
            print("System structure is good but some improvements recommended.")
        else:
            print("\n❌ VALIDATION FAILED")
            print("Please address the errors before proceeding.")
        
        print("\n📋 Next Steps:")
        if not self.errors:
            print("  1. Set up ROS2 environment")
            print("  2. Build the workspace: ./build_ros2.sh")
            print("  3. Test system startup: ros2 launch robot_bringup bringup.launch.py")
            print("  4. Run full integration validation with ROS2")
        else:
            print("  1. Address all reported errors")
            print("  2. Re-run structure validation")
            print("  3. Check implementation files and fix issues")

def main():
    """Main validation function"""
    validator = StructureValidator()
    success = validator.run_validation()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)