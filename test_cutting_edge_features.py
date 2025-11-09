#!/usr/bin/env python3
"""
Modular Test System for Robot Features
Tests individual components and removes passed tests to keep things clean
"""

import subprocess
import time
import sys
import os
import json
from pathlib import Path

class ModularTestSystem:
    def __init__(self):
        self.test_results_file = "test_results.json"
        self.passed_tests = self.load_passed_tests()
        
    def load_passed_tests(self):
        """Load previously passed tests"""
        if os.path.exists(self.test_results_file):
            try:
                with open(self.test_results_file, 'r') as f:
                    return json.load(f).get('passed_tests', [])
            except:
                return []
        return []
    
    def save_passed_test(self, test_name):
        """Save a passed test and remove it from future runs"""
        if test_name not in self.passed_tests:
            self.passed_tests.append(test_name)
            
        test_data = {
            'passed_tests': self.passed_tests,
            'last_run': time.time()
        }
        
        with open(self.test_results_file, 'w') as f:
            json.dump(test_data, f, indent=2)
    
    def run_command(self, command, description, timeout=30):
        """Run a command with timeout and error handling"""
        print(f"🧪 Testing: {description}")
        
        try:
            result = subprocess.run(
                command.split() if isinstance(command, str) else command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                print(f"✅ PASS: {description}")
                return True
            else:
                print(f"❌ FAIL: {description}")
                if result.stderr:
                    print(f"   Error: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ TIMEOUT: {description} (>{timeout}s)")
            return False
        except Exception as e:
            print(f"💥 ERROR: {description} - {str(e)}")
            return False

class RobotFeatureTests:
    def __init__(self, test_system):
        self.test_system = test_system
    
    def test_dependencies(self):
        """Test system dependencies"""
        if "dependencies" in self.test_system.passed_tests:
            print("⏭️ Dependencies test already passed - skipping")
            return True
            
        print("\n🔍 Testing Dependencies")
        
        deps = [
            (["python3", "--version"], "Python 3"),
            (["ros2", "--version"], "ROS 2"),
            (["colcon", "--version"], "Colcon"),
        ]
        
        all_passed = True
        for cmd, name in deps:
            if not self.test_system.run_command(cmd, f"{name} installation", timeout=5):
                all_passed = False
        
        if all_passed:
            self.test_system.save_passed_test("dependencies")
        
        return all_passed
    
    def test_package_build(self):
        """Test package building"""
        if "package_build" in self.test_system.passed_tests:
            print("⏭️ Package build test already passed - skipping")
            return True
            
        print("\n🔨 Testing Package Build")
        
        build_cmd = ["colcon", "build", "--packages-select", "robot_semantic_slam", "--symlink-install"]
        if self.test_system.run_command(build_cmd, "Building robot_semantic_slam", timeout=120):
            self.test_system.save_passed_test("package_build")
            return True
        
        return False
    
    def test_launch_files(self):
        """Test launch file syntax"""
        print("\n🚀 Testing Launch Files")
        
        launch_files = [
            "src/robot_semantic_slam/launch/semantic_slam.launch.py",
            "src/robot_semantic_slam/launch/enhanced_visualization.launch.py", 
            "src/robot_semantic_slam/launch/advanced_safety.launch.py",
            "src/robot_semantic_slam/launch/semantic_interface.launch.py",
            "src/robot_semantic_slam/launch/cutting_edge_features.launch.py"
        ]
        
        all_passed = True
        for launch_file in launch_files:
            test_name = f"launch_{Path(launch_file).stem}"
            
            if test_name in self.test_system.passed_tests:
                print(f"⏭️ {launch_file} already passed - skipping")
                continue
                
            if os.path.exists(launch_file):
                cmd = ["python3", "-m", "py_compile", launch_file]
                if self.test_system.run_command(cmd, f"Syntax: {launch_file}", timeout=10):
                    self.test_system.save_passed_test(test_name)
                else:
                    all_passed = False
            else:
                print(f"❌ Launch file not found: {launch_file}")
                all_passed = False
        
        return all_passed
    
    def test_node_syntax(self):
        """Test node Python syntax"""
        print("\n🤖 Testing Node Syntax")
        
        nodes = [
            "semantic_slam_node",
            "enhanced_visualizer",
            "advanced_safety_system", 
            "semantic_interface"
        ]
        
        all_passed = True
        for node in nodes:
            test_name = f"node_{node}"
            
            if test_name in self.test_system.passed_tests:
                print(f"⏭️ {node} already passed - skipping")
                continue
                
            node_file = f"src/robot_semantic_slam/robot_semantic_slam/{node}.py"
            if os.path.exists(node_file):
                cmd = ["python3", "-m", "py_compile", node_file]
                if self.test_system.run_command(cmd, f"Syntax: {node}", timeout=10):
                    self.test_system.save_passed_test(test_name)
                else:
                    all_passed = False
            else:
                print(f"❌ Node file not found: {node_file}")
                all_passed = False
        
        return all_passed
    
    def test_package_installation(self):
        """Test package installation"""
        if "package_installation" in self.test_system.passed_tests:
            print("⏭️ Package installation test already passed - skipping")
            return True
            
        print("\n📦 Testing Package Installation")
        
        cmd = ["bash", "-c", "source install/setup.bash && ros2 pkg list | grep robot_semantic_slam"]
        if self.test_system.run_command(cmd, "Package installation check", timeout=10):
            self.test_system.save_passed_test("package_installation")
            return True
        
        return False
    
    def test_python_dependencies(self):
        """Test Python package dependencies"""
        if "python_dependencies" in self.test_system.passed_tests:
            print("⏭️ Python dependencies test already passed - skipping")
            return True
            
        print("\n🐍 Testing Python Dependencies")
        
        packages = ["ultralytics", "opencv-python", "numpy"]
        all_passed = True
        
        for package in packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"✅ {package} is available")
            except ImportError:
                print(f"⚠️ Installing {package}...")
                install_cmd = [sys.executable, "-m", "pip", "install", package]
                if not self.test_system.run_command(install_cmd, f"Installing {package}", timeout=60):
                    all_passed = False
        
        if all_passed:
            self.test_system.save_passed_test("python_dependencies")
        
        return all_passed

def main():
    """Main test runner"""
    print("🤖 ROBOT FEATURES MODULAR TEST SYSTEM")
    print("=" * 50)
    
    test_system = ModularTestSystem()
    robot_tests = RobotFeatureTests(test_system)
    
    # Define test sequence
    tests = [
        (robot_tests.test_dependencies, "System Dependencies"),
        (robot_tests.test_python_dependencies, "Python Dependencies"),
        (robot_tests.test_package_build, "Package Build"),
        (robot_tests.test_package_installation, "Package Installation"),
        (robot_tests.test_launch_files, "Launch Files"),
        (robot_tests.test_node_syntax, "Node Syntax"),
    ]
    
    # Run tests
    results = []
    for test_func, test_name in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        result = test_func()
        results.append((test_name, result))
        
        if not result:
            print(f"⚠️ {test_name} failed - continuing...")
    
    # Summary
    print(f"\n{'='*50}")
    print("🏁 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    print(f"Passed tests saved: {len(test_system.passed_tests)} total")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n🚀 Launch individual features:")
        print("  • Semantic SLAM: ros2 launch robot_semantic_slam semantic_slam.launch.py")
        print("  • Enhanced Viz: ros2 launch robot_semantic_slam enhanced_visualization.launch.py")
        print("  • Advanced Safety: ros2 launch robot_semantic_slam advanced_safety.launch.py")
        print("  • Natural Language: ros2 launch robot_semantic_slam semantic_interface.launch.py")
        print("  • All Features: ros2 launch robot_semantic_slam cutting_edge_features.launch.py")
        return 0
    else:
        print(f"\n⚠️ {total - passed} tests failed. Fix issues and re-run.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)