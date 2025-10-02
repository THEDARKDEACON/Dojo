#!/bin/bash

# Exit on error
set -e

# Set workspace directory
WORKSPACE="/home/Dojo/Dojo"
cd "$WORKSPACE"

# Source ROS 2 environment
source /opt/ros/humble/setup.bash

# Function to fix common issues
fix_issues() {
    echo "🔧 Fixing common issues..."
    
    # Fix CMake files for Pi environment
    fix_cmake_files
    
    # Ensure rosdep is properly initialized
    if [ ! -f "/etc/ros/rosdep/sources.list.d/20-default.list" ]; then
        echo "🔄 Initializing rosdep..."
        sudo rosdep init || true
        rosdep update || true
    fi
    
    # Install system dependencies
    echo "📦 Installing system dependencies..."
    sudo apt-get update
    sudo apt-get install -y \
        python3-pip \
        python3-empy \
        python3-colcon-common-extensions \
        python3-vcstool \
        python3-setuptools \
        python3-wheel \
        ros-${ROS_DISTRO:-humble}-cv-bridge \
        ros-${ROS_DISTRO:-humble}-image-transport \
        python3-opencv
        
    # Install specific Python packages
    echo "📦 Installing Python packages..."
    # Install system package for empy
    sudo apt-get install -y python3-empy
    
    # Install other Python packages
    pip3 install --user --upgrade \
        'setuptools==59.6.0' \
        'wheel==0.37.1' \
        'packaging==21.3' \
        'setuptools-scm==6.4.2' \
        'empy==3.3.4'
        
    # Verify empy installation
    if ! python3 -c "import em; print('empy version:', em.VERSION)" &>/dev/null; then
        echo "❌ Error: empy is not properly installed."
        echo "Trying alternative installation method..."
        sudo -H pip3 install empy==3.3.4
    fi
}

# Function to fix CMake files for Pi environment
fix_cmake_files() {
    echo "🔧 Fixing CMake files for Pi environment..."
    
    # Fix robot_control CMakeLists.txt - remove ament_enable_testing
    if [ -f "src/robot_control/CMakeLists.txt" ]; then
        echo "  🔧 Fixing robot_control CMakeLists.txt..."
        sed -i 's/ament_enable_testing()/# ament_enable_testing() # Commented out - not available in this ROS 2 installation/g' src/robot_control/CMakeLists.txt
        # Also fix any other testing-related issues
        sed -i 's/if(BUILD_TESTING)/if(BUILD_TESTING AND FALSE)/g' src/robot_control/CMakeLists.txt
    fi
    
    # Fix robot_description CMakeLists.txt - make gazebo dependencies optional
    if [ -f "src/robot_description/CMakeLists.txt" ]; then
        echo "  🔧 Fixing robot_description CMakeLists.txt..."
        sed -i 's/find_package(gazebo_ros2_control REQUIRED)/find_package(gazebo_ros2_control QUIET)/g' src/robot_description/CMakeLists.txt
        sed -i 's/find_package(gazebo_ros REQUIRED)/find_package(gazebo_ros QUIET)/g' src/robot_description/CMakeLists.txt
        # Also make other gazebo packages optional
        sed -i 's/find_package(gazebo_dev REQUIRED)/find_package(gazebo_dev QUIET)/g' src/robot_description/CMakeLists.txt
        sed -i 's/find_package(gazebo_msgs REQUIRED)/find_package(gazebo_msgs QUIET)/g' src/robot_description/CMakeLists.txt
    fi
    
    # Fix robot_bringup dependencies - make them optional in CMakeLists if it exists
    if [ -f "src/robot_bringup/CMakeLists.txt" ]; then
        echo "  🔧 Fixing robot_bringup CMakeLists.txt..."
        # Make sure it doesn't fail if some packages aren't found
        sed -i 's/find_package(\([^)]*\) REQUIRED)/find_package(\1 QUIET)/g' src/robot_bringup/CMakeLists.txt
    fi
    
    # Clean any Docker-specific CMake cache files
    find . -name "CMakeCache.txt" -delete 2>/dev/null || true
    find . -name "CMakeFiles" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # Clean environment variables that might cause issues
    unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH 2>/dev/null || true
    
    echo "  ✅ CMake files fixed for Pi environment"
}

# Function to verify Python environment
verify_python_environment() {
    echo "🔍 Verifying Python environment..."
    
    # Check for Python version
    local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    local major=$(echo $python_version | cut -d. -f1)
    local minor=$(echo $python_version | cut -d. -f2)
    
    if [[ $major -lt 3 ]] || { [[ $major -eq 3 ]] && [[ $minor -lt 8 ]]; }; then
        echo "❌ Python 3.8 or higher is required. Found Python $python_version"
        return 1
    fi
    
    # Check for required packages
    local required_pkgs=("setuptools" "wheel" "packaging" "em")
    for pkg in "${required_pkgs[@]}"; do
        if ! python3 -c "import $pkg" &>/dev/null; then
            echo "❌ Missing required Python package: $pkg"
            return 1
        fi
    done
    
    echo "✅ Python environment looks good!"
    return 0
}

# Function to build a single package
build_package() {
    local pkg=$1
    echo "📦 Building package: $pkg"
    
    # Clean environment variables that might cause conflicts
    unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH 2>/dev/null || true
    source /opt/ros/humble/setup.bash
    
    # Source workspace if it exists
    if [ -f "$WORKSPACE/install/setup.bash" ]; then
        source "$WORKSPACE/install/setup.bash"
    fi
    
    # Special handling for packages with known issues
    case "$pkg" in
        "robot_description")
            echo "  🔧 Building robot_description with gazebo dependencies made optional..."
            if colcon build \
                --packages-select "$pkg" \
                --symlink-install \
                --allow-overriding "$pkg" \
                --cmake-args \
                    -DCMAKE_BUILD_TYPE=Release \
                    -DBUILD_TESTING=OFF \
                    -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
                    -DCMAKE_INSTALL_PREFIX="$WORKSPACE/install"; then
                echo "✅ Successfully built $pkg (with gazebo dependencies optional)"
            else
                echo "❌ Failed to build $pkg"
                return 1
            fi
            ;;
        "robot_control")
            echo "  🔧 Building robot_control with special CMake args..."
            if colcon build \
                --packages-select "$pkg" \
                --symlink-install \
                --allow-overriding "$pkg" \
                --cmake-args \
                    -DCMAKE_BUILD_TYPE=Release \
                    -DBUILD_TESTING=OFF \
                    -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
                    -DCMAKE_INSTALL_PREFIX="$WORKSPACE/install"; then
                echo "✅ Successfully built $pkg (with fixes)"
            else
                echo "❌ Failed to build $pkg"
                return 1
            fi
            ;;
        *)
            # Detect ament_python packages (presence of setup.py) and build without CMake args
            if [ -f "src/$pkg/setup.py" ]; then
                # Python package
                if colcon build \
                    --packages-select "$pkg" \
                    --symlink-install \
                    --cmake-args -DBUILD_TESTING=OFF; then
                    echo "✅ Successfully built $pkg (ament_python)"
                else
                    echo "❌ Failed to build $pkg (ament_python)"
                    return 1
                fi
            else
                # CMake/ament_cmake packages
                if colcon build \
                    --packages-select "$pkg" \
                    --symlink-install \
                    --cmake-args \
                        -DCMAKE_BUILD_TYPE=Release \
                        -DBUILD_TESTING=OFF \
                        -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
                        -DCMAKE_INSTALL_PREFIX="$WORKSPACE/install" \
                        --allow-overriding "$pkg"; then
                    echo "✅ Successfully built $pkg"
                else
                    echo "❌ Failed to build $pkg"
                    return 1
                fi
            fi
            ;;
    esac
    
    # Source the workspace to make the package available
    if [ -f "$WORKSPACE/install/setup.bash" ]; then
        source "$WORKSPACE/install/setup.bash"
    fi
    return 0
}

# Main build function
build_workspace() {
    echo "🚀 Starting build process on Raspberry Pi..."
    
    # Fix common issues first
    fix_issues
    
    # Verify Python environment
    if ! verify_python_environment; then
        echo "❌ Python environment verification failed. Please fix the issues above and try again."
        exit 1
    fi
    
    # Clean previous builds if they exist
    if [ -d "build" ] || [ -d "install" ] || [ -d "log" ]; then
        echo "🧹 Cleaning previous build artifacts..."
        rm -rf build/ install/ log/
    fi
    
    # Create required directories that might be missing
    mkdir -p src/robot_description/config
    touch src/robot_description/config/.keep
    
    # Get list of all packages
    echo "🔍 Discovering all packages in the workspace..."
    local all_packages=($(colcon list -n))
    
    # Validate that core new architecture packages exist
    local required_packages=("robot_hardware" "robot_interfaces" "robot_control" "robot_bringup" "robot_perception")
    for req_pkg in "${required_packages[@]}"; do
        if [[ ! " ${all_packages[@]} " =~ " ${req_pkg} " ]]; then
            echo "⚠️  Warning: Required package '$req_pkg' not found. Make sure you have the latest repository."
        fi
    done
    
    # Define packages to exclude (only packages that truly don't exist or are simulation-only)
    local excluded_packages=(
        "robot_gazebo"          # Simulation only
        "gazebo_ros2_control"   # Not available on ARM64
        "gazebo_ros"            # Not available on ARM64  
        "gazebo_plugins"        # Not available on ARM64
        "gazebo_ros_control"    # Not available on ARM64
        "gazebo_dev"            # Not available on ARM64
        "gazebo_msgs"           # Not available on ARM64
        "gazebo_ros_pkgs"       # Not available on ARM64
        "gazebo_simulator"      # Not available on ARM64
        "rviz"                  # GUI - not needed on headless Pi
        "rviz2"                 # GUI - not needed on headless Pi
        "rviz_common"           # GUI - not needed on headless Pi
        "rviz_default_plugins"  # GUI - not needed on headless Pi
        "rviz_rendering"        # GUI - not needed on headless Pi
        "rviz_visual_tools"     # GUI - not needed on headless Pi
    )
    
    # Define packages that need special handling due to CMake issues
    local problematic_packages=(
        "robot_description"  # Has gazebo dependencies - we'll make them optional
        "robot_control"      # Has ament_enable_testing issue - we'll fix it
    )
    
    # Filter out excluded packages
    local packages=()
    local excluded_count=0
    
    for pkg in "${all_packages[@]}"; do
        local exclude=0
        for excluded in "${excluded_packages[@]}"; do
            if [[ "$pkg" == "$excluded" ]]; then
                exclude=1
                excluded_count=$((excluded_count + 1))
                echo "ℹ️  Excluding package: $pkg (simulation/URDF related)"
                break
            fi
        done
        
        # Check for problematic packages (we'll handle these specially)
        for problematic in "${problematic_packages[@]}"; do
            if [[ "$pkg" == "$problematic" ]]; then
                echo "ℹ️  Including problematic package with special handling: $pkg"
                break
            fi
        done
        
        if [[ $exclude -eq 0 ]]; then
            packages+=("$pkg")
        fi
    done
    
    echo "📦 Found ${#all_packages[@]} total packages, excluded $excluded_count packages"
    echo "📦 Will build ${#packages[@]} packages: ${packages[*]}"
    
    echo "📦 Packages to build (${#packages[@]}): ${packages[*]}"
    
    # Filter out packages that don't exist in the workspace
    local filtered_packages=()
    for pkg in "${packages[@]}"; do
        if [[ " ${all_packages[*]} " =~ " $pkg " ]]; then
            filtered_packages+=("$pkg")
        fi
    done
    
    # Update packages with filtered list
    packages=("${filtered_packages[@]}")
    
    # Don't add back excluded packages - they were excluded for a reason
    echo "✅ Final package list (${#packages[@]} packages): ${packages[*]}"
    
    # Prioritize essential packages for ROSArduinoBridge
    local priority_packages=("robot_interfaces" "robot_hardware" "robot_control" "robot_description" "robot_bringup")
    local reordered_packages=()
    
    # Add priority packages first (if they exist)
    for priority_pkg in "${priority_packages[@]}"; do
        if [[ " ${packages[@]} " =~ " ${priority_pkg} " ]]; then
            reordered_packages+=("$priority_pkg")
        fi
    done
    
    # Add remaining packages
    for pkg in "${packages[@]}"; do
        if [[ ! " ${reordered_packages[@]} " =~ " ${pkg} " ]]; then
            reordered_packages+=("$pkg")
        fi
    done
    
    packages=("${reordered_packages[@]}")
    echo "📦 Build order (prioritizing ROSArduinoBridge essentials): ${packages[*]}"
    
    # Build packages one by one with dependency handling
    local success=true
    local remaining_attempts=3
    local built_packages=()
    
    while [ $remaining_attempts -gt 0 ]; do
        success=true
        local built_something=false
        
        for pkg in "${packages[@]}"; do
            # Skip if already built successfully
            if [[ " ${built_packages[@]} " =~ " ${pkg} " ]]; then
                continue
            fi
            
            echo "🔍 Checking dependencies for $pkg..."
            local deps_met=true
            
            # Get package dependencies
            local deps=$(colcon info "$pkg" 2>/dev/null | grep '^\s*'"$pkg"'\s' | grep -oP '\S+$' || echo "")
            
            # Check if all dependencies are built
            for dep in $deps; do
                if [ ! -f "$WORKSPACE/install/$dep/share/$dep/package.sh" ]; then
                    echo "  ⏳ Waiting for dependency: $dep"
                    deps_met=false
                    break
                fi
            done
            
            # Try to build the package with special handling for ros2arduino_bridge
            if $deps_met; then
                echo "🚀 Building $pkg (attempt $((4 - remaining_attempts))/3)"
                if ! build_package "$pkg"; then
                    success=false
                else
                    built_something=true
                    built_packages+=("$pkg")
                fi
            fi
        done
        
        # If we didn't build anything this round, we're either done or stuck
        if [ "$built_something" = false ]; then
            if [ "$success" = true ]; then
                echo "✅ All buildable packages have been built successfully"
                break
            else
                remaining_attempts=$((remaining_attempts - 1))
                if [ $remaining_attempts -gt 0 ]; then
                    echo "⚠️  No progress made this round, but there are still build failures"
                    echo "   Remaining attempts: $remaining_attempts"
                else
                    echo "❌ Giving up after maximum retry attempts"
                    success=false
                    break
                fi
            fi
        fi
    done
    
    if [ "$success" = true ]; then
        echo "✨ Build completed successfully!"
        echo ""
        echo "📦 Built packages: ${built_packages[*]}"
        echo ""
        echo "🚀 Next steps:"
        echo "  1. Source the workspace:"
        echo "     source $WORKSPACE/install/setup.bash"
        echo ""
        echo "  2. For ROSArduinoBridge testing:"
        echo "     - Upload Arduino sketch: $WORKSPACE/firmware/arduino/ROSArduinoBridge/ROSArduinoBridge.ino"
        echo "     - Test hardware: ros2 launch robot_hardware hardware.launch.py protocol:=rosarduino_bridge"
        echo ""
        echo "  3. For full robot launch:"
        echo "     ros2 launch robot_bringup bringup.launch.py arduino_protocol:=rosarduino_bridge"
        echo ""
        echo "  4. Test communication:"
        echo "     ros2 topic pub /cmd_vel geometry_msgs/Twist \"linear: {x: 0.1}\""
        echo "     ros2 topic echo /odom"
        echo ""
    else
        echo "❌ Build failed for some packages"
        echo "📦 Successfully built: ${built_packages[*]}"
        echo "❌ Failed packages may need manual attention"
        exit 1
    fi
}

# Run the build
build_workspace
