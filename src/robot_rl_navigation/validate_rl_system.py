#!/usr/bin/env python3
"""
Quick validation script for RL Navigation system.

Validates that all components are properly installed and configured.
"""

import os
import sys

def check_dependencies():
    """Check if all required dependencies are installed."""
    print("Checking dependencies...")
    
    dependencies = {
        'stable-baselines3': 'stable_baselines3',
        'gymnasium': 'gymnasium',
        'torch': 'torch',
        'numpy': 'numpy',
        'rclpy': 'rclpy'
    }
    
    missing = []
    for name, module in dependencies.items():
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name} - NOT FOUND")
            missing.append(name)
    
    return len(missing) == 0, missing


def check_package_structure():
    """Check if package structure is correct."""
    print("\nChecking package structure...")
    
    required_files = [
        'robot_rl_navigation/__init__.py',
        'robot_rl_navigation/rl_navigator.py',
        'robot_rl_navigation/navigation_env.py',
        'robot_rl_navigation/train_agent.py',
        'robot_rl_navigation/policy_manager.py',
        'config/rl_navigator_params.yaml',
        'config/training_params.yaml',
        'launch/rl_navigation.launch.py',
        'package.xml',
        'setup.py'
    ]
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    missing = []
    
    for file in required_files:
        file_path = os.path.join(base_path, file)
        if os.path.exists(file_path):
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} - NOT FOUND")
            missing.append(file)
    
    return len(missing) == 0, missing


def check_model_directory():
    """Check if model directory exists."""
    print("\nChecking model directory...")
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(base_path, 'models')
    
    if os.path.exists(models_dir):
        print(f"  ✓ Models directory exists: {models_dir}")
        
        # List any existing models
        models = [f for f in os.listdir(models_dir) if f.endswith('.zip')]
        if models:
            print(f"  Found {len(models)} trained model(s):")
            for model in models:
                print(f"    - {model}")
        else:
            print("  ⚠ No trained models found (run train_agent.py to train)")
        
        return True
    else:
        print(f"  ✗ Models directory not found: {models_dir}")
        print("  Creating models directory...")
        os.makedirs(models_dir, exist_ok=True)
        return True


def test_import_modules():
    """Test importing all RL navigation modules."""
    print("\nTesting module imports...")
    
    modules = [
        'robot_rl_navigation',
        'robot_rl_navigation.rl_navigator',
        'robot_rl_navigation.navigation_env',
        'robot_rl_navigation.train_agent',
        'robot_rl_navigation.policy_manager'
    ]
    
    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except Exception as e:
            print(f"  ✗ {module} - ERROR: {e}")
            failed.append(module)
    
    return len(failed) == 0, failed


def main():
    """Main validation function."""
    print("="*60)
    print("RL NAVIGATION SYSTEM VALIDATION")
    print("="*60)
    
    all_passed = True
    
    # Check dependencies
    deps_ok, missing_deps = check_dependencies()
    if not deps_ok:
        print(f"\n⚠ Missing dependencies: {', '.join(missing_deps)}")
        print("Install with: pip install stable-baselines3 gymnasium torch")
        all_passed = False
    
    # Check package structure
    struct_ok, missing_files = check_package_structure()
    if not struct_ok:
        print(f"\n⚠ Missing files: {', '.join(missing_files)}")
        all_passed = False
    
    # Check model directory
    models_ok = check_model_directory()
    if not models_ok:
        all_passed = False
    
    # Test imports
    if deps_ok and struct_ok:
        imports_ok, failed_imports = test_import_modules()
        if not imports_ok:
            print(f"\n⚠ Failed imports: {', '.join(failed_imports)}")
            all_passed = False
    
    # Final summary
    print("\n" + "="*60)
    if all_passed:
        print("✓ ALL VALIDATION CHECKS PASSED")
        print("\nRL Navigation system is ready to use!")
        print("\nNext steps:")
        print("  1. Train a policy: ros2 run robot_rl_navigation train_agent")
        print("  2. Test navigation: ros2 launch robot_rl_navigation rl_navigation.launch.py")
        print("  3. Run tests: python3 test_rl_navigation.py")
    else:
        print("✗ SOME VALIDATION CHECKS FAILED")
        print("\nPlease fix the issues above before using the RL navigation system.")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
