#!/usr/bin/env python3
"""
Comprehensive RL Navigation Testing Script

This script validates task 10.7 requirements:
- Test in multiple environments
- Measure success rate (target: 90%+)
- Measure collision rate (target: <5%)
- Compare performance vs Nav2 baseline

Since no trained model exists yet, this script provides:
1. System validation and readiness checks
2. Test framework for when models are available
3. Baseline performance measurement capability
4. Comparison metrics structure
"""

import os
import sys
import json
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import subprocess


@dataclass
class SystemCheck:
    """System validation check result."""
    component: str
    status: str  # 'pass', 'fail', 'warning'
    message: str


@dataclass
class EnvironmentTest:
    """Test configuration for an environment."""
    name: str
    world_file: str
    test_goals: List[tuple]
    spawn_position: tuple
    description: str


@dataclass
class PerformanceMetrics:
    """Performance metrics for comparison."""
    environment: str
    method: str  # 'RL' or 'Nav2'
    success_rate: float
    collision_rate: float
    avg_completion_time: float
    avg_path_length: float
    avg_path_efficiency: float  # straight_line_distance / actual_path_length


class RLNavigationValidator:
    """Comprehensive validation and testing for RL navigation."""
    
    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.test_environments = self._define_test_environments()
        self.system_checks: List[SystemCheck] = []
        
    def _define_test_environments(self) -> List[EnvironmentTest]:
        """Define test environments as per requirements."""
        return [
            EnvironmentTest(
                name='mapping_world',
                world_file='mapping_world.world',
                test_goals=[(5.0, 0.0), (0.0, 5.0), (-5.0, 0.0), (0.0, -5.0)],
                spawn_position=(0.0, 0.0, 0.1),
                description='Simple environment for basic navigation testing'
            ),
            EnvironmentTest(
                name='house',
                world_file='house.world',
                test_goals=[(3.0, 3.0), (-3.0, 3.0), (-3.0, -3.0), (3.0, -3.0)],
                spawn_position=(0.0, 0.0, 0.1),
                description='Residential environment with rooms and furniture'
            ),
            EnvironmentTest(
                name='office_small',
                world_file='office_small.world',
                test_goals=[(4.0, 2.0), (2.0, 4.0), (-2.0, 2.0), (2.0, -2.0)],
                spawn_position=(0.0, 0.0, 0.1),
                description='Office environment with cubicles'
            ),
            EnvironmentTest(
                name='warehouse',
                world_file='warehouse.world',
                test_goals=[(8.0, 0.0), (0.0, 8.0), (-8.0, 0.0), (0.0, -8.0)],
                spawn_position=(0.0, 0.0, 0.1),
                description='Large warehouse with shelves and obstacles'
            )
        ]
    
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are installed."""
        print("\n" + "="*70)
        print("CHECKING DEPENDENCIES")
        print("="*70)
        
        dependencies = {
            'stable-baselines3': 'stable_baselines3',
            'gymnasium': 'gymnasium',
            'torch': 'torch',
            'numpy': 'numpy',
        }
        
        all_ok = True
        for name, module in dependencies.items():
            try:
                __import__(module)
                self.system_checks.append(SystemCheck(
                    component=f'Dependency: {name}',
                    status='pass',
                    message='Installed'
                ))
                print(f"  ✓ {name:25s} - Installed")
            except ImportError:
                self.system_checks.append(SystemCheck(
                    component=f'Dependency: {name}',
                    status='fail',
                    message='Not installed'
                ))
                print(f"  ✗ {name:25s} - NOT INSTALLED")
                all_ok = False
        
        return all_ok
    
    def check_package_structure(self) -> bool:
        """Verify package structure is complete."""
        print("\n" + "="*70)
        print("CHECKING PACKAGE STRUCTURE")
        print("="*70)
        
        required_files = [
            ('robot_rl_navigation/__init__.py', 'Package init'),
            ('robot_rl_navigation/rl_navigator.py', 'RL Navigator node'),
            ('robot_rl_navigation/navigation_env.py', 'Navigation environment'),
            ('robot_rl_navigation/train_agent.py', 'Training script'),
            ('robot_rl_navigation/policy_manager.py', 'Policy manager'),
            ('config/rl_navigator_params.yaml', 'Navigator config'),
            ('config/training_params.yaml', 'Training config'),
            ('launch/rl_navigation.launch.py', 'Launch file'),
            ('package.xml', 'Package manifest'),
            ('setup.py', 'Setup script')
        ]
        
        all_ok = True
        for file_path, description in required_files:
            full_path = os.path.join(self.base_path, file_path)
            if os.path.exists(full_path):
                self.system_checks.append(SystemCheck(
                    component=f'File: {file_path}',
                    status='pass',
                    message='Exists'
                ))
                print(f"  ✓ {description:30s} - {file_path}")
            else:
                self.system_checks.append(SystemCheck(
                    component=f'File: {file_path}',
                    status='fail',
                    message='Missing'
                ))
                print(f"  ✗ {description:30s} - MISSING: {file_path}")
                all_ok = False
        
        return all_ok
    
    def check_trained_models(self) -> tuple:
        """Check for trained models."""
        print("\n" + "="*70)
        print("CHECKING TRAINED MODELS")
        print("="*70)
        
        models_dir = os.path.join(self.base_path, 'models')
        
        if not os.path.exists(models_dir):
            print(f"  ✗ Models directory not found: {models_dir}")
            self.system_checks.append(SystemCheck(
                component='Models directory',
                status='fail',
                message='Directory does not exist'
            ))
            return False, []
        
        # Look for model files
        model_files = [f for f in os.listdir(models_dir) if f.endswith('.zip')]
        
        if not model_files:
            print(f"  ⚠ No trained models found in {models_dir}")
            print(f"  → Run training first: ros2 run robot_rl_navigation train_agent")
            self.system_checks.append(SystemCheck(
                component='Trained models',
                status='warning',
                message='No models found - training required'
            ))
            return False, []
        
        print(f"  ✓ Found {len(model_files)} trained model(s):")
        for model in model_files:
            print(f"    - {model}")
            self.system_checks.append(SystemCheck(
                component=f'Model: {model}',
                status='pass',
                message='Available'
            ))
        
        return True, model_files
    
    def check_simulation_worlds(self) -> bool:
        """Check if simulation worlds exist."""
        print("\n" + "="*70)
        print("CHECKING SIMULATION WORLDS")
        print("="*70)
        
        worlds_dir = os.path.join(self.base_path, '../../robot_gazebo/worlds')
        
        if not os.path.exists(worlds_dir):
            print(f"  ✗ Worlds directory not found: {worlds_dir}")
            return False
        
        all_ok = True
        for env in self.test_environments:
            world_path = os.path.join(worlds_dir, env.world_file)
            if os.path.exists(world_path):
                print(f"  ✓ {env.name:20s} - {env.world_file}")
                self.system_checks.append(SystemCheck(
                    component=f'World: {env.name}',
                    status='pass',
                    message='Available'
                ))
            else:
                print(f"  ✗ {env.name:20s} - MISSING: {env.world_file}")
                self.system_checks.append(SystemCheck(
                    component=f'World: {env.name}',
                    status='fail',
                    message='World file not found'
                ))
                all_ok = False
        
        return all_ok
    
    def generate_test_plan(self):
        """Generate detailed test plan."""
        print("\n" + "="*70)
        print("TEST PLAN FOR RL NAVIGATION (Task 10.7)")
        print("="*70)
        
        print("\nTest Objectives:")
        print("  1. Test in multiple environments (4 worlds)")
        print("  2. Measure success rate (target: ≥90%)")
        print("  3. Measure collision rate (target: <5%)")
        print("  4. Compare performance vs Nav2 baseline")
        
        print("\nTest Environments:")
        for i, env in enumerate(self.test_environments, 1):
            print(f"\n  {i}. {env.name}")
            print(f"     Description: {env.description}")
            print(f"     World file: {env.world_file}")
            print(f"     Test goals: {len(env.test_goals)} waypoints")
            for j, goal in enumerate(env.test_goals, 1):
                print(f"       {j}) ({goal[0]:+.1f}, {goal[1]:+.1f})")
        
        print("\nTest Metrics to Collect:")
        metrics = [
            "Success rate (goal reached within timeout)",
            "Collision rate (obstacle contact)",
            "Average completion time",
            "Average path length",
            "Path efficiency (straight-line / actual)",
            "Average velocity",
            "Minimum obstacle clearance",
            "RL confidence scores",
            "Nav2 fallback frequency"
        ]
        for metric in metrics:
            print(f"  • {metric}")
        
        print("\nTest Procedure:")
        steps = [
            "1. Build and source the workspace",
            "2. Launch Gazebo with test environment",
            "3. Launch RL navigation system",
            "4. For each test goal:",
            "   a. Send navigation goal",
            "   b. Monitor robot progress",
            "   c. Record metrics",
            "   d. Detect success/collision/timeout",
            "5. Calculate statistics",
            "6. Repeat for Nav2 baseline",
            "7. Compare results"
        ]
        for step in steps:
            print(f"  {step}")
    
    def generate_test_commands(self):
        """Generate commands to run tests."""
        print("\n" + "="*70)
        print("TEST EXECUTION COMMANDS")
        print("="*70)
        
        print("\n1. Build the workspace:")
        print("   colcon build --packages-select robot_rl_navigation")
        print("   source install/setup.bash")
        
        print("\n2. Train RL policy (if not done):")
        print("   ros2 run robot_rl_navigation train_agent")
        
        print("\n3. Launch simulation with RL navigation:")
        print("   ros2 launch robot_gazebo complete_robot_simulation.launch.py \\")
        print("       world:=mapping_world \\")
        print("       use_rl_navigation:=true")
        
        print("\n4. Run comprehensive tests:")
        print("   python3 src/robot_rl_navigation/test_rl_navigation.py")
        
        print("\n5. Run baseline Nav2 tests:")
        print("   ros2 launch robot_gazebo complete_robot_simulation.launch.py \\")
        print("       world:=mapping_world \\")
        print("       use_rl_navigation:=false")
        print("   python3 src/robot_rl_navigation/test_rl_navigation.py")
    
    def create_test_report_template(self):
        """Create template for test results."""
        print("\n" + "="*70)
        print("TEST REPORT TEMPLATE")
        print("="*70)
        
        report = {
            "test_info": {
                "task": "10.7 Test and validate RL navigation",
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "requirements": [
                    "2.1.1: RL navigation system active",
                    "2.1.2: 90%+ success rate",
                    "2.1.3: <5% collision rate"
                ]
            },
            "system_validation": {
                "dependencies": "PASS/FAIL",
                "package_structure": "PASS/FAIL",
                "trained_models": "PASS/FAIL/WARNING",
                "simulation_worlds": "PASS/FAIL"
            },
            "test_results": {
                "rl_navigation": {
                    "total_tests": 0,
                    "success_rate": 0.0,
                    "collision_rate": 0.0,
                    "avg_completion_time": 0.0,
                    "avg_path_length": 0.0,
                    "avg_confidence": 0.0
                },
                "nav2_baseline": {
                    "total_tests": 0,
                    "success_rate": 0.0,
                    "collision_rate": 0.0,
                    "avg_completion_time": 0.0,
                    "avg_path_length": 0.0
                }
            },
            "comparison": {
                "success_rate_improvement": "TBD",
                "collision_rate_comparison": "TBD",
                "time_improvement": "TBD",
                "path_efficiency_improvement": "TBD"
            },
            "requirements_met": {
                "success_rate_target": False,
                "collision_rate_target": False,
                "multi_environment_testing": False
            }
        }
        
        report_file = os.path.join(self.base_path, 'test_report_template.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nTest report template created: {report_file}")
        print("\nThis template will be filled with actual results after testing.")
    
    def print_summary(self):
        """Print validation summary."""
        print("\n" + "="*70)
        print("VALIDATION SUMMARY")
        print("="*70)
        
        pass_count = sum(1 for c in self.system_checks if c.status == 'pass')
        fail_count = sum(1 for c in self.system_checks if c.status == 'fail')
        warn_count = sum(1 for c in self.system_checks if c.status == 'warning')
        
        print(f"\nTotal Checks: {len(self.system_checks)}")
        print(f"  ✓ Passed:   {pass_count}")
        print(f"  ✗ Failed:   {fail_count}")
        print(f"  ⚠ Warnings: {warn_count}")
        
        if fail_count > 0:
            print("\n⚠ SYSTEM NOT READY FOR TESTING")
            print("\nFailed checks:")
            for check in self.system_checks:
                if check.status == 'fail':
                    print(f"  • {check.component}: {check.message}")
        elif warn_count > 0:
            print("\n⚠ SYSTEM PARTIALLY READY")
            print("\nWarnings:")
            for check in self.system_checks:
                if check.status == 'warning':
                    print(f"  • {check.component}: {check.message}")
            print("\nYou can proceed with system validation, but training is required for full testing.")
        else:
            print("\n✓ SYSTEM READY FOR TESTING")
            print("\nAll components are in place. Proceed with test execution.")
        
        return fail_count == 0
    
    def run_validation(self):
        """Run complete validation."""
        print("\n" + "="*70)
        print("RL NAVIGATION SYSTEM VALIDATION - TASK 10.7")
        print("="*70)
        
        # Run all checks
        deps_ok = self.check_dependencies()
        struct_ok = self.check_package_structure()
        models_ok, models = self.check_trained_models()
        worlds_ok = self.check_simulation_worlds()
        
        # Generate test plan
        self.generate_test_plan()
        
        # Generate test commands
        self.generate_test_commands()
        
        # Create report template
        self.create_test_report_template()
        
        # Print summary
        system_ready = self.print_summary()
        
        # Save validation results
        validation_results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system_checks": [asdict(c) for c in self.system_checks],
            "system_ready": system_ready,
            "trained_models_available": models_ok,
            "models_found": models
        }
        
        results_file = os.path.join(self.base_path, 'validation_results.json')
        with open(results_file, 'w') as f:
            json.dump(validation_results, f, indent=2)
        
        print(f"\nValidation results saved to: {results_file}")
        
        return system_ready


def main():
    """Main function."""
    validator = RLNavigationValidator()
    system_ready = validator.run_validation()
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    
    if not system_ready:
        print("\n1. Fix failed system checks")
        print("2. Re-run this validation script")
    else:
        print("\n1. Train RL policy (if not done):")
        print("   ros2 run robot_rl_navigation train_agent")
        print("\n2. Run comprehensive tests:")
        print("   python3 src/robot_rl_navigation/test_rl_navigation.py")
        print("\n3. Compare with Nav2 baseline")
        print("\n4. Generate final test report")
    
    print("\n" + "="*70)
    
    return 0 if system_ready else 1


if __name__ == '__main__':
    sys.exit(main())
