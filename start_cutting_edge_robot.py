#!/usr/bin/env python3
"""
🚀 Start Advanced Robot Features
Quick launcher for semantic SLAM, enhanced visualization, and advanced safety
"""

import subprocess
import sys
import time
import os
import signal

class CuttingEdgeRobotLauncher:
    def __init__(self):
        self.processes = []
        self.running = False
        
    def print_banner(self):
        """Print startup banner"""
        print("""
🚀 ═══════════════════════════════════════════════════════════════════════════════
   ADVANCED ROBOT FEATURES - AI-POWERED AUTONOMOUS SYSTEM
   🤖 Semantic SLAM • 🎯 Object Detection • 🛡️ Advanced Safety • 🗣️ Natural Language
═══════════════════════════════════════════════════════════════════════════════ 🚀

🔥 FEATURES LAUNCHING:
   ✨ YOLO-powered object detection and semantic mapping
   🎨 Real-time 3D visualization with performance dashboard  
   🛡️ Predictive collision avoidance and multi-layer safety
   🗣️ Natural language command interface ("go to chair")
   📊 AI-powered autonomous exploration and navigation
   🧠 Intelligent decision making and spatial understanding

🎯 READY FOR ADVANCED ROBOTICS!
""")
    
    def check_dependencies(self):
        """Check if system is ready"""
        print("🔍 Checking system readiness...")
        
        # Check ROS 2
        try:
            result = subprocess.run(['ros2', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print("  ✅ ROS 2 is ready")
            else:
                print("  ❌ ROS 2 not found")
                return False
        except FileNotFoundError:
            print("  ❌ ROS 2 not installed")
            return False
        
        # Check if workspace is built
        if os.path.exists('install/setup.bash'):
            print("  ✅ Workspace is built")
        else:
            print("  ⚠️ Workspace not built - run 'colcon build' first")
            return False
        
        print("  🚀 System ready for launch!")
        return True
    
    def install_python_deps(self):
        """Install required Python packages"""
        print("\n📦 Installing AI dependencies...")
        
        packages = [
            'ultralytics',  # YOLO
            'opencv-python',
            'numpy',
            'scipy'
        ]
        
        for package in packages:
            try:
                print(f"  Installing {package}...")
                subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
                             check=True, capture_output=True)
                print(f"  ✅ {package} ready")
            except subprocess.CalledProcessError:
                print(f"  ⚠️ {package} installation failed (may already be installed)")
    
    def source_workspace(self):
        """Source the ROS 2 workspace"""
        print("\n🔧 Sourcing workspace...")
        # This will be handled by the launch command
        return True
    
    def launch_system(self, world='mapping_world', mode='full'):
        """Launch the cutting-edge robot system"""
        print(f"\n🚀 Launching Cutting-Edge Robot System...")
        print(f"   World: {world}")
        print(f"   Mode: {mode}")
        
        # Build launch command
        cmd = [
            'bash', '-c',
            'source install/setup.bash && ros2 launch complete_robot_simulation.launch.py'
        ]
        
        # Add world parameter
        cmd[-1] += f' world:={world}.world'
        
        # Add mode-specific parameters
        if mode == 'full':
            cmd[-1] += ' slam:=true navigation:=false vision:=true autonomous_exploration:=true'
        elif mode == 'demo':
            cmd[-1] += ' slam:=true navigation:=false vision:=false autonomous_exploration:=true gui:=true'
        elif mode == 'headless':
            cmd[-1] += ' slam:=true navigation:=false vision:=true autonomous_exploration:=true gui:=false rviz:=false'
        
        print(f"   Command: {cmd[-1]}")
        print("\n🎬 Starting system...")
        
        try:
            # Start the main process
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                     universal_newlines=True, bufsize=1)
            self.processes.append(process)
            self.running = True
            
            print("✅ System launched successfully!")
            print("\n🎮 CONTROL INTERFACE:")
            print("   📝 Send text commands: ros2 topic pub /text_command std_msgs/String \"data: 'go to chair'\"")
            print("   📊 Monitor performance: ros2 topic echo /performance_metrics")
            print("   🗺️ View semantic map: ros2 topic echo /semantic_map")
            print("   🛡️ Safety status: ros2 topic echo /safety_status")
            print("\n💬 EXAMPLE COMMANDS:")
            print("   • 'go to chair' - Navigate to nearest chair")
            print("   • 'find bottle' - Locate and report bottle positions")
            print("   • 'explore kitchen' - Autonomously map kitchen area")
            print("   • 'list objects' - Show all detected objects")
            print("   • 'stop' - Emergency stop")
            print("\n🔥 Press Ctrl+C to shutdown gracefully")
            
            # Monitor output
            while self.running:
                output = process.stdout.readline()
                if output:
                    print(output.strip())
                elif process.poll() is not None:
                    break
                    
        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested...")
            self.shutdown()
        except Exception as e:
            print(f"\n💥 Launch failed: {e}")
            self.shutdown()
    
    def send_test_commands(self):
        """Send test commands to demonstrate capabilities"""
        print("\n🧪 Sending test commands in 30 seconds...")
        time.sleep(30)
        
        test_commands = [
            "list objects",
            "explore room", 
            "find chair",
            "status"
        ]
        
        for cmd in test_commands:
            print(f"🤖 Sending: '{cmd}'")
            try:
                subprocess.run([
                    'bash', '-c',
                    f'source install/setup.bash && ros2 topic pub --once /text_command std_msgs/String "data: \'{cmd}\'"'
                ], check=True, capture_output=True)
                time.sleep(5)
            except subprocess.CalledProcessError:
                print(f"  ⚠️ Failed to send command: {cmd}")
    
    def shutdown(self):
        """Gracefully shutdown all processes"""
        print("\n🔄 Shutting down cutting-edge robot system...")
        self.running = False
        
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print("  ✅ Process terminated gracefully")
            except subprocess.TimeoutExpired:
                process.kill()
                print("  ⚡ Process force killed")
            except Exception as e:
                print(f"  ⚠️ Error shutting down process: {e}")
        
        print("🏁 Shutdown complete. Thanks for using the advanced robot system!")

def main():
    launcher = CuttingEdgeRobotLauncher()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        launcher.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Print banner
    launcher.print_banner()
    
    # Check system
    if not launcher.check_dependencies():
        print("❌ System not ready. Please fix the issues above.")
        return 1
    
    # Install dependencies
    launcher.install_python_deps()
    
    # Parse command line arguments
    world = 'mapping_world'
    mode = 'full'
    
    if len(sys.argv) > 1:
        world = sys.argv[1]
    if len(sys.argv) > 2:
        mode = sys.argv[2]
    
    # Launch system
    try:
        launcher.launch_system(world, mode)
    except KeyboardInterrupt:
        launcher.shutdown()
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)