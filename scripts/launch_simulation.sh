#!/bin/bash
# Primary Simulation Launch Script for Dojo Robot
# Launches robot simulation with configurable options

echo "🚀 Starting Dojo Robot Simulation"
echo "=================================="

# Source the workspace
if [ -f "install/setup.bash" ]; then
    source install/setup.bash
    echo "✅ Workspace sourced"
else
    echo "❌ Error: install/setup.bash not found. Please build the workspace first."
    echo "Run: colcon build --symlink-install"
    exit 1
fi

# Check if Gazebo is available
if ! command -v gazebo &> /dev/null; then
    echo "❌ Error: Gazebo not found. Please install Gazebo:"
    echo "sudo apt install ros-humble-gazebo-ros-pkgs"
    exit 1
fi

# Set simulation environment
export USE_SIMULATION=true
export USE_GAZEBO=true

echo "🎮 Launching simulation..."
echo "Available worlds:"
echo "  - empty.world (default)"
echo "  - dojo_world.world"
echo "  - office_small.world"
echo "  - warehouse.world"
echo ""

# Parse command line arguments
WORLD="empty.world"
RVIZ="true"
GUI="true"
COMPLETE="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --world)
            WORLD="$2"
            shift 2
            ;;
        --no-rviz)
            RVIZ="false"
            shift
            ;;
        --no-gui)
            GUI="false"
            shift
            ;;
        --complete)
            COMPLETE="true"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --world WORLD    Specify Gazebo world file (default: empty.world)"
            echo "  --no-rviz       Don't launch RViz for visualization"
            echo "  --no-gui        Run Gazebo without GUI (headless)"
            echo "  --complete      Launch complete simulation with SLAM, navigation, and perception"
            echo "  --help, -h      Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                           # Launch basic simulation with RViz"
            echo "  $0 --world dojo_world.world # Launch with dojo world"
            echo "  $0 --no-rviz               # Launch without RViz"
            echo "  $0 --complete              # Launch complete simulation with all features"
            echo "  $0 --no-gui                # Launch headless"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "🌍 World: $WORLD"
echo "👁️  RViz: $RVIZ"
echo "🖥️  GUI: $GUI"
echo "🚀 Complete: $COMPLETE"
echo ""

# Kill any existing processes
echo "🧹 Cleaning up any existing processes..."
pkill -f gzserver || true
pkill -f gzclient || true
pkill -f rviz2 || true
sleep 2

# Launch the appropriate simulation
if [ "$COMPLETE" = "true" ]; then
    echo "🎮 Starting complete simulation with SLAM, navigation, and perception..."
    ros2 launch robot_gazebo complete_simulation.launch.py \
        world:=$WORLD \
        use_sim_time:=true \
        gui:=$GUI \
        use_rviz:=$RVIZ \
        use_slam:=true \
        use_nav2:=true \
        use_perception:=true \
        use_teleop:=true
else
    echo "🎮 Starting basic simulation..."
    ros2 launch robot_gazebo simulation.launch.py \
        world:=$WORLD \
        use_sim_time:=true \
        gui:=$GUI \
        rviz:=$RVIZ
fi

echo ""
echo "🎯 Simulation ended."
echo ""
echo "📋 To control the robot:"
echo "  ros2 run teleop_twist_keyboard teleop_twist_keyboard"
echo ""
echo "📊 Useful commands:"
echo "  ros2 topic list                    # List all topics"
echo "  ros2 topic echo /scan             # View laser data"
echo "  ros2 topic echo /odom             # View odometry"