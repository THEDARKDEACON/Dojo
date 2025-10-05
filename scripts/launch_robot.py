#!/usr/bin/env python3
"""
Robot Launch Helper Script

Provides an easy way to launch the robot in different modes with proper
configuration and validation.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


def check_ros_environment():
    """Check if ROS2 environment is properly set up."""
    if 'ROS_DISTRO' not in os.environ:
        print("ERROR: ROS2 environment not sourced. Please run:")
        print("source /opt/ros/<distro>/setup.bash")
        print("source install/setup.bash")
        return False
    
    print(f"Using ROS2 {os.environ['ROS_DISTRO']}")
    return True


def check_workspace():
    """Check if we're in a valid ROS2 workspace."""
    current_dir = Path.cwd()
    
    # Look for workspace indicators
    if not (current_dir / 'src').exists():
        print("ERROR: Not in a ROS2 workspace root directory.")
        print("Please run this script from the workspace root (where src/ directory exists).")
        return False
    
    # Check if robot packages exist
    robot_packages = ['robot_bringup', 'robot_control', 'robot_description']
    missing_packages = []
    
    for package in robot_packages:
        if not (current_dir / 'src' / package).exists():
            missing_packages.append(package)
    
    if missing_packages:
        print(f"ERROR: Missing required packages: {missing_packages}")
        print("Please ensure all robot packages are built and available.")
        return False
    
    return True


def detect_available_modes():
    """Detect which modes are available based on installed packages."""
    modes = {}
    
    # Check simulation mode
    try:
        result = subprocess.run(['ros2', 'pkg', 'list'], capture_output=True, text=True)
        packages = result.stdout.split('\n')
        
        has_gazebo = any('gazebo' in pkg for pkg in packages)
        has_robot_gazebo = 'robot_gazebo' in packages
        
        modes['simulation'] = has_gazebo and has_robot_gazebo
        modes['hardware'] = 'robot_hardware' in packages
        
    except subprocess.CalledProcessError:
        print("WARNING: Could not detect available packages")
        modes['simulation'] = False
        modes['hardware'] = True
    
    return modes


def launch_robot(mode, **kwargs):
    """Launch the robot in the specified mode."""
    # Set environment variables based on mode
    env = os.environ.copy()
    
    if mode == 'simulation':
        env['USE_SIMULATION'] = 'true'
        env['USE_GAZEBO'] = 'true'
    else:
        env['USE_SIMULATION'] = 'false'
        env['USE_GAZEBO'] = 'false'
    
    # Build launch command
    cmd = [
        'ros2', 'launch', 'robot_bringup', 'bringup.launch.py',
        f'operation_mode:={mode}'
    ]
    
    # Add optional arguments
    if kwargs.get('world'):
        cmd.extend([f'world:={kwargs["world"]}'])
    
    if kwargs.get('perception'):
        cmd.extend(['use_perception:=true'])
    
    if kwargs.get('navigation'):
        cmd.extend(['use_navigation:=true'])
    
    if kwargs.get('no_gui') and mode == 'simulation':
        cmd.extend(['gui:=false'])
    
    print(f"Launching robot in {mode} mode...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, env=env, check=True)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Launch failed with exit code {e.returncode}")
        return False
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        return True
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Launch the Dojo robot in different modes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s simulation                    # Launch in simulation mode
  %(prog)s hardware                      # Launch in hardware mode
  %(prog)s simulation --world office.world  # Launch with specific world
  %(prog)s hardware --perception         # Launch hardware with perception
  %(prog)s --auto                        # Auto-detect best mode
        """
    )
    
    parser.add_argument('mode', nargs='?', choices=['simulation', 'hardware', 'auto'],
                       default='auto', help='Launch mode')
    parser.add_argument('--world', help='Gazebo world file (simulation only)')
    parser.add_argument('--perception', action='store_true',
                       help='Enable perception stack')
    parser.add_argument('--navigation', action='store_true',
                       help='Enable navigation stack')
    parser.add_argument('--no-gui', action='store_true',
                       help='Run Gazebo without GUI (simulation only)')
    parser.add_argument('--list-modes', action='store_true',
                       help='List available modes and exit')
    
    args = parser.parse_args()
    
    # Check environment
    if not check_ros_environment():
        sys.exit(1)
    
    if not check_workspace():
        sys.exit(1)
    
    # Detect available modes
    available_modes = detect_available_modes()
    
    if args.list_modes:
        print("Available modes:")
        for mode, available in available_modes.items():
            status = "✓" if available else "✗"
            print(f"  {status} {mode}")
        sys.exit(0)
    
    # Determine launch mode
    if args.mode == 'auto':
        if available_modes['simulation']:
            launch_mode = 'simulation'
            print("Auto-detected simulation mode (Gazebo available)")
        elif available_modes['hardware']:
            launch_mode = 'hardware'
            print("Auto-detected hardware mode")
        else:
            print("ERROR: No valid modes available")
            sys.exit(1)
    else:
        launch_mode = args.mode
        if not available_modes[launch_mode]:
            print(f"ERROR: {launch_mode} mode is not available")
            print("Run with --list-modes to see available modes")
            sys.exit(1)
    
    # Launch robot
    success = launch_robot(
        launch_mode,
        world=args.world,
        perception=args.perception,
        navigation=args.navigation,
        no_gui=args.no_gui
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()