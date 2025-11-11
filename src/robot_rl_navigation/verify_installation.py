#!/usr/bin/env python3
"""
Verification script for robot_rl_navigation installation

This script checks if all dependencies are installed and the package
is properly configured.
"""

import sys
import importlib


def check_module(module_name, package_name=None):
    """Check if a Python module is available."""
    try:
        importlib.import_module(module_name)
        print(f"✓ {package_name or module_name}")
        return True
    except ImportError:
        print(f"✗ {package_name or module_name} - NOT INSTALLED")
        return False


def check_ros2():
    """Check if ROS2 is available."""
    try:
        import rclpy
        print("✓ ROS2 (rclpy)")
        return True
    except ImportError:
        print("✗ ROS2 (rclpy) - NOT INSTALLED")
        return False


def check_rl_libraries():
    """Check if RL libraries are available."""
    results = []
    
    # Check stable-baselines3
    results.append(check_module('stable_baselines3', 'stable-baselines3'))
    
    # Check gymnasium
    results.append(check_module('gymnasium', 'gymnasium'))
    
    # Check torch
    results.append(check_module('torch', 'torch (PyTorch)'))
    
    # Check numpy
    results.append(check_module('numpy', 'numpy'))
    
    # Check tensorboard
    results.append(check_module('tensorboard', 'tensorboard'))
    
    return all(results)


def check_ros2_packages():
    """Check if ROS2 message packages are available."""
    results = []
    
    packages = [
        ('geometry_msgs', 'geometry_msgs'),
        ('sensor_msgs', 'sensor_msgs'),
        ('nav_msgs', 'nav_msgs'),
        ('std_msgs', 'std_msgs'),
    ]
    
    for module, name in packages:
        results.append(check_module(module, name))
    
    return all(results)


def check_gpu():
    """Check if GPU is available for training."""
    try:
        import torch
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0)
            print(f"✓ GPU Available: {device_name} ({device_count} device(s))")
            return True
        else:
            print("⚠ GPU Not Available (CPU training will be slower)")
            return False
    except ImportError:
        print("⚠ Cannot check GPU (torch not installed)")
        return False


def check_package_imports():
    """Check if package modules can be imported."""
    print("\nChecking package modules...")
    
    modules = [
        'robot_rl_navigation',
        'robot_rl_navigation.navigation_env',
        'robot_rl_navigation.train_agent',
        'robot_rl_navigation.rl_navigator',
        'robot_rl_navigation.policy_manager',
    ]
    
    results = []
    for module in modules:
        try:
            importlib.import_module(module)
            print(f"✓ {module}")
            results.append(True)
        except ImportError as e:
            print(f"✗ {module} - {e}")
            results.append(False)
    
    return all(results)


def main():
    """Run all verification checks."""
    print("="*60)
    print("Robot RL Navigation - Installation Verification")
    print("="*60)
    
    all_ok = True
    
    # Check ROS2
    print("\n1. Checking ROS2...")
    if not check_ros2():
        all_ok = False
        print("   → Install ROS2 Humble or later")
    
    # Check ROS2 packages
    print("\n2. Checking ROS2 message packages...")
    if not check_ros2_packages():
        all_ok = False
        print("   → Install missing ROS2 packages")
    
    # Check RL libraries
    print("\n3. Checking RL libraries...")
    if not check_rl_libraries():
        all_ok = False
        print("   → Run: pip3 install -r requirements.txt")
    
    # Check GPU
    print("\n4. Checking GPU availability...")
    check_gpu()  # Warning only, not required
    
    # Check package imports
    print("\n5. Checking package modules...")
    if not check_package_imports():
        all_ok = False
        print("   → Build package: colcon build --packages-select robot_rl_navigation")
    
    # Summary
    print("\n" + "="*60)
    if all_ok:
        print("✓ ALL CHECKS PASSED")
        print("\nYou can now:")
        print("  1. Train a policy: ros2 run robot_rl_navigation train_agent")
        print("  2. Use RL navigation: ros2 launch robot_rl_navigation rl_navigation.launch.py")
    else:
        print("✗ SOME CHECKS FAILED")
        print("\nPlease install missing dependencies and try again.")
        print("See INSTALL.md for detailed instructions.")
    print("="*60)
    
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
