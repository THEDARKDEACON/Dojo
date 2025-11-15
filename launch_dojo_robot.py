#!/usr/bin/env python3
"""
Simple launcher for Dojo Robot simulation.
Provides an easy interface to launch the complete system.
"""

import sys
import subprocess
from pathlib import Path


def main():
    """Launch the Dojo Robot simulation."""
    
    print("\n" + "=" * 80)
    print("🤖 Dojo Robot - Complete System Launcher")
    print("=" * 80)
    print("\nLaunching with all cutting-edge features enabled:")
    print("  ✅ Semantic SLAM with YOLO object detection")
    print("  ✅ Gaussian Splatting 3D reconstruction")
    print("  ✅ 3D point cloud visualization")
    print("  ✅ Real-time performance dashboard")
    print("  ✅ Advanced safety system")
    print("  ✅ Natural language interface")
    print("=" * 80 + "\n")
    
    # Parse simple arguments
    world = "mapping_world"
    if len(sys.argv) > 1:
        world = sys.argv[1]
        print(f"Using world: {world}\n")
    
    # Build the launch command
    launch_cmd = [
        'ros2', 'launch', 'robot_gazebo', 'complete_robot_simulation.launch.py',
        f'world:={world}'
    ]
    
    try:
        # Source and launch
        source_cmd = (
            "source /opt/ros/jazzy/setup.bash && "
            "source install/setup.bash && "
            f"{' '.join(launch_cmd)}"
        )
        
        result = subprocess.run(
            ['bash', '-c', source_cmd],
            cwd=Path.cwd(),
            check=False
        )
        
        print("\n🏁 Simulation ended")
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == '__main__':
    print("\n💡 Tip: Disable features with launch arguments:")
    print("   ros2 launch robot_gazebo complete_robot_simulation.launch.py \\")
    print("       gaussian_splatting:=false semantic_slam:=false\n")
    sys.exit(main())
