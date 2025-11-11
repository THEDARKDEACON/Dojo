#!/bin/bash
# Verification script for Task 9.2 optimizations
# Checks that all optimization changes are in place

echo "=========================================="
echo "Task 9.2 Optimization Verification"
echo "=========================================="
echo ""

PASS=0
FAIL=0

# Function to check if a string exists in a file
check_optimization() {
    local file=$1
    local pattern=$2
    local description=$3
    
    if grep -q "$pattern" "$file"; then
        echo "✅ $description"
        ((PASS++))
    else
        echo "❌ $description"
        ((FAIL++))
    fi
}

echo "Checking Semantic SLAM optimizations..."
check_optimization "src/robot_semantic_slam/robot_semantic_slam/semantic_slam_node.py" "skip_frames" "Frame skipping parameter"
check_optimization "src/robot_semantic_slam/robot_semantic_slam/semantic_slam_node.py" "self.yolo_model.fuse()" "YOLO model fusion"
check_optimization "src/robot_semantic_slam/robot_semantic_slam/semantic_slam_node.py" "detection_frequency" "Detection frequency parameter"
check_optimization "src/robot_semantic_slam/robot_semantic_slam/semantic_slam_node.py" "verbose=False" "YOLO verbose disabled"

echo ""
echo "Checking Point Cloud Processor optimizations..."
check_optimization "src/robot_semantic_slam/robot_semantic_slam/pointcloud_processor.py" "voxel_size', 0.08" "Increased voxel size"
check_optimization "src/robot_semantic_slam/robot_semantic_slam/pointcloud_processor.py" "max_points', 500000" "Reduced max points"
check_optimization "src/robot_semantic_slam/robot_semantic_slam/pointcloud_processor.py" "accumulation_time', 8.0" "Reduced accumulation time"
check_optimization "src/robot_semantic_slam/robot_semantic_slam/pointcloud_processor.py" "cleanup_frequency" "Cleanup frequency parameter"

echo ""
echo "Checking Performance Dashboard optimizations..."
check_optimization "src/robot_semantic_slam/robot_semantic_slam/performance_dashboard.py" "update_rate', 0.5" "Reduced update rate"
check_optimization "src/robot_semantic_slam/robot_semantic_slam/performance_dashboard.py" "enable_detailed_markers" "Detailed markers parameter"
check_optimization "src/robot_semantic_slam/robot_semantic_slam/performance_dashboard.py" "if not self.enable_detailed_markers" "Conditional marker publishing"

echo ""
echo "Checking profiler script..."
if [ -f "profile_priority1_performance.py" ]; then
    echo "✅ Performance profiler script exists"
    ((PASS++))
    
    if [ -x "profile_priority1_performance.py" ]; then
        echo "✅ Performance profiler is executable"
        ((PASS++))
    else
        echo "❌ Performance profiler is not executable"
        ((FAIL++))
    fi
else
    echo "❌ Performance profiler script missing"
    ((FAIL++))
fi

echo ""
echo "Checking documentation..."
if [ -f "TASK_9.2_OPTIMIZATIONS.md" ]; then
    echo "✅ Optimization documentation exists"
    ((PASS++))
else
    echo "❌ Optimization documentation missing"
    ((FAIL++))
fi

echo ""
echo "=========================================="
echo "Verification Results"
echo "=========================================="
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "✅ All optimizations verified successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Build the workspace: colcon build --symlink-install"
    echo "2. Source the workspace: source install/setup.bash"
    echo "3. Run performance profiler: python3 profile_priority1_performance.py"
    echo "4. Review results: cat performance_profile_report.json"
    exit 0
else
    echo "❌ Some optimizations are missing or incorrect"
    echo "Please review the failed checks above"
    exit 1
fi
