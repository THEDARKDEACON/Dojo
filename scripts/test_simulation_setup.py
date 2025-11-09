#!/usr/bin/env python3
"""
Test script to verify simulation setup
Checks if all required packages and files are available
"""

import os
import sys
import subprocess
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and report status"""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} - NOT FOUND")
        return False

def check_ros_package(package_name):
    """Check if a ROS package is available"""
    try:
        result = subprocess.run(['ros2', 'pkg', 'prefix', package_name], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ ROS Package: {package_name}")
            return True
        else:
            print(f"❌ ROS Package: {package_name} - NOT FOUND")
            return False
    except Exception as e:
        print(f"❌ ROS Package: {package_name} - ERROR: {e}")
        return False

def main():
    print("🔍 Testing Dojo Robot Simulation Setup")
    print("=====================================")
    
    # Check workspace setup
    workspace_root = Path.cwd()
    print(f"📁 Workspace: {workspace_root}")
    
    # Check critical files
    files_to_check = [
        ("scripts/full_simulation.launch.py", "Full Simulation Launch"),
        ("scripts/launch_complete_simulation.sh", "Complete Simulation Script"),
        ("src/robot_description/urdf/robot.urdf", "Robot URDF"),
        ("src/robot_description/urdf/robot.urdf.xacro", "Robot URDF Xacro"),
        ("src/robot_description/rviz/robot_simulation.rviz", "RViz Config"),
        ("config/nav2_params.yaml", "Navigation Parameters"),
        ("install/setup.bash", "Workspace Build")
    ]
    
    print("\n📋 Checking Required Files:")
    all_files_ok = True
    for file_path, description in files_to_check:
        if not check_file_exists(file_path, description):
            all_files_ok = False
    
    # Check ROS packages
    print("\n📦 Checking ROS Packages:")
    required_packages = [
        "ros_gz_sim",
        "robot_state_publisher",
        "joint_state_publisher", 
        "slam_toolbox",
        "nav2_bringup",
        "rviz2",
        "teleop_twist_keyboard"
    ]
    
    all_packages_ok = True
    for package in required_packages:
        if not check_ros_package(package):
            all_packages_ok = False
    
    # Summary
    print("\n📊 SUMMARY:")
    if all_files_ok and all_packages_ok:
        print("🎉 All checks passed! Simulation should work correctly.")
        print("\n🚀 To start the simulation, run:")
        print("   ./scripts/launch_complete_simulation.sh")
        print("\n🎮 To control the robot, run in a separate terminal:")
        print("   source install/setup.bash")
        print("   ros2 run teleop_twist_keyboard teleop_twist_keyboard")
        return 0
    else:
        print("⚠️  Some issues found. Please fix them before running simulation.")
        if not all_files_ok:
            print("   - Missing files detected")
        if not all_packages_ok:
            print("   - Missing ROS packages detected")
            print("   - Install missing packages with: sudo apt install ros-humble-<package-name>")
        return 1

if __name__ == "__main__":
    sys.exit(main())