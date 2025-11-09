#!/bin/bash

# ROS 2 Build Script for Local Development
# Updated for the new Dojo robot architecture

set -e  # Exit on error

# Configuration
WORKSPACE_DIR="$(pwd)"
MAX_ATTEMPTS=3
BUILD_FLAGS="--symlink-install --event-handlers console_direct+"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if we're in a ROS workspace
check_workspace() {
    if [ ! -d "src" ]; then
        log_error "Not in a ROS workspace (no 'src' directory found)"
        log_info "Please run this script from your ROS workspace root"
        exit 1
    fi
    
    log_info "Building workspace: $WORKSPACE_DIR"
}

# Function to source ROS environment
source_ros() {
    if [ -f "/opt/ros/jazzy/setup.bash" ]; then
        log_info "Sourcing ROS 2 Jazzy environment"
        source "/opt/ros/jazzy/setup.bash"
    else
        log_error "ROS 2 Jazzy not found. Please install ROS 2 Jazzy first."
        exit 1
    fi
}

# Function to check system dependencies
check_system_dependencies() {
    log_info "Checking system dependencies..."
    
    local missing_system_deps=()
    local system_deps=("python3" "python3-pip" "python3-yaml" "python3-serial")
    
    for dep in "${system_deps[@]}"; do
        if ! dpkg -l | grep -q "^ii  $dep "; then
            missing_system_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_system_deps[@]} -gt 0 ]; then
        log_warning "Missing system dependencies:"
        for dep in "${missing_system_deps[@]}"; do
            echo "  - $dep"
        done
        
        log_info "Installing missing system dependencies..."
        if sudo apt update && sudo apt install -y "${missing_system_deps[@]}"; then
            log_success "System dependencies installed successfully"
        else
            log_error "Failed to install some system dependencies"
            return 1
        fi
    else
        log_success "All system dependencies satisfied"
    fi
    
    return 0
}

# Function to install ROS dependencies with better error handling
install_ros_dependencies() {
    log_info "Installing ROS package dependencies..."
    
    # Check if rosdep is initialized
    if [ ! -f "/etc/ros/rosdep/sources.list.d/20-default.list" ]; then
        log_info "Initializing rosdep..."
        if ! sudo rosdep init; then
            log_error "Failed to initialize rosdep"
            return 1
        fi
    fi
    
    # Update rosdep with retry logic
    local rosdep_attempts=3
    local rosdep_success=false
    
    for ((i=1; i<=rosdep_attempts; i++)); do
        log_info "Updating rosdep (attempt $i/$rosdep_attempts)..."
        if rosdep update; then
            rosdep_success=true
            break
        else
            log_warning "Rosdep update attempt $i failed"
            if [ $i -lt $rosdep_attempts ]; then
                sleep 2
            fi
        fi
    done
    
    if [ "$rosdep_success" = false ]; then
        log_error "Failed to update rosdep after $rosdep_attempts attempts"
        return 1
    fi
    
    # Install workspace dependencies with detailed error reporting
    log_info "Installing workspace dependencies..."
    if rosdep install --from-paths src --ignore-src -r -y; then
        log_success "ROS dependencies installed successfully"
    else
        log_error "Failed to install some ROS dependencies"
        log_info "Checking which packages have missing dependencies..."
        
        # Try to identify problematic packages
        rosdep check --from-paths src --ignore-src || true
        return 1
    fi
    
    return 0
}

# Function to install Python dependencies
install_python_dependencies() {
    log_info "Installing Python dependencies..."
    
    # Create requirements.txt if it doesn't exist
    if [ ! -f "requirements.txt" ]; then
        log_info "Creating requirements.txt with common robot dependencies..."
        cat > requirements.txt << EOF
# Core Python dependencies for Dojo Robot
PyYAML>=6.0
pyserial>=3.5
opencv-python>=4.5.0
numpy>=1.21.0
scipy>=1.7.0
matplotlib>=3.5.0
EOF
    fi
    
    # Install Python dependencies with better error handling
    if [ -f "requirements.txt" ]; then
        log_info "Installing Python dependencies from requirements.txt..."
        
        # Try pip3 first, then pip
        if command -v pip3 >/dev/null 2>&1; then
            if pip3 install -r requirements.txt; then
                log_success "Python dependencies installed successfully"
            else
                log_error "Failed to install Python dependencies with pip3"
                return 1
            fi
        elif command -v pip >/dev/null 2>&1; then
            if pip install -r requirements.txt; then
                log_success "Python dependencies installed successfully"
            else
                log_error "Failed to install Python dependencies with pip"
                return 1
            fi
        else
            log_error "Neither pip3 nor pip found - cannot install Python dependencies"
            return 1
        fi
    fi
    
    return 0
}

# Function to install dependencies with comprehensive error handling
install_dependencies() {
    log_info "Installing/updating dependencies..."
    
    # Install system dependencies first
    if ! check_system_dependencies; then
        log_error "Failed to install system dependencies"
        return 1
    fi
    
    # Install Python dependencies
    if ! install_python_dependencies; then
        log_error "Failed to install Python dependencies"
        return 1
    fi
    
    # Install ROS dependencies
    if ! install_ros_dependencies; then
        log_error "Failed to install ROS dependencies"
        return 1
    fi
    
    log_success "All dependencies installed successfully"
    return 0
}

# Function to detect and report missing dependencies
detect_missing_dependencies() {
    log_info "Detecting missing dependencies..."
    
    local missing_deps=()
    local missing_python_deps=()
    local missing_ros_deps=()
    
    # Check system packages
    local system_packages=("python3" "python3-pip" "python3-yaml" "python3-serial" "python3-opencv")
    for pkg in "${system_packages[@]}"; do
        if ! dpkg -l | grep -q "^ii  $pkg "; then
            missing_deps+=("$pkg")
        fi
    done
    
    # Check Python packages
    local python_packages=("yaml" "serial" "cv2" "numpy" "scipy")
    for pkg in "${python_packages[@]}"; do
        if ! python3 -c "import $pkg" 2>/dev/null; then
            missing_python_deps+=("$pkg")
        fi
    done
    
    # Check ROS packages
    local ros_packages=("rclpy" "std_msgs" "geometry_msgs" "sensor_msgs" "tf2_ros")
    for pkg in "${ros_packages[@]}"; do
        if ! python3 -c "import $pkg" 2>/dev/null; then
            missing_ros_deps+=("$pkg")
        fi
    done
    
    # Report findings
    local has_missing=false
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        has_missing=true
        log_error "Missing system packages:"
        for dep in "${missing_deps[@]}"; do
            echo "  ❌ $dep"
        done
        echo ""
        log_info "Install with: sudo apt install ${missing_deps[*]}"
        echo ""
    fi
    
    if [ ${#missing_python_deps[@]} -gt 0 ]; then
        has_missing=true
        log_error "Missing Python packages:"
        for dep in "${missing_python_deps[@]}"; do
            echo "  ❌ $dep"
        done
        echo ""
        log_info "Install with: pip3 install -r requirements.txt"
        echo ""
    fi
    
    if [ ${#missing_ros_deps[@]} -gt 0 ]; then
        has_missing=true
        log_error "Missing ROS packages:"
        for dep in "${missing_ros_deps[@]}"; do
            echo "  ❌ $dep"
        done
        echo ""
        log_info "Install with: rosdep install --from-paths src --ignore-src -r -y"
        echo ""
    fi
    
    if [ "$has_missing" = true ]; then
        log_error "Missing dependencies detected. Run with --deps to install automatically."
        return 1
    else
        log_success "All dependencies are satisfied"
        return 0
    fi
}

# Function to validate build results
validate_build_results() {
    log_info "Validating build results..."
    
    local validation_errors=()
    
    # Check if install directory was created
    if [ ! -d "install" ]; then
        validation_errors+=("Install directory not created")
    fi
    
    # Check if setup.bash exists
    if [ ! -f "install/setup.bash" ]; then
        validation_errors+=("Setup script not generated")
    fi
    
    # Check for core packages in install directory
    local core_packages=("robot_interfaces" "robot_description" "robot_control" "robot_bringup")
    for pkg in "${core_packages[@]}"; do
        if [ ! -d "install/$pkg" ]; then
            validation_errors+=("Core package not installed: $pkg")
        fi
    done
    
    # Check for Python package installations
    if [ -d "install" ]; then
        local python_packages_found=false
        for pkg_dir in install/*/lib/python*/site-packages/; do
            if [ -d "$pkg_dir" ]; then
                python_packages_found=true
                break
            fi
        done
        
        if [ "$python_packages_found" = false ]; then
            validation_errors+=("No Python packages found in install directory")
        fi
    fi
    
    # Report validation results
    if [ ${#validation_errors[@]} -gt 0 ]; then
        log_error "Build validation failed:"
        for error in "${validation_errors[@]}"; do
            echo "  ❌ $error"
        done
        return 1
    else
        log_success "Build validation passed"
        return 0
    fi
}

# Function to perform post-build checks
post_build_checks() {
    log_info "Performing post-build checks..."
    
    # Source the workspace and check if packages are available
    if [ -f "install/setup.bash" ]; then
        log_info "Testing workspace sourcing..."
        
        # Test in a subshell to avoid affecting current environment
        (
            source install/setup.bash
            
            # Check if ROS packages are discoverable
            if command -v ros2 >/dev/null 2>&1; then
                log_info "Checking package discovery..."
                
                # Try to list packages (this will fail gracefully if packages aren't found)
                if ros2 pkg list | grep -q "robot_"; then
                    log_success "Robot packages are discoverable"
                else
                    log_warning "Robot packages may not be properly installed"
                fi
            else
                log_warning "ROS 2 not available for package testing"
            fi
        )
    else
        log_error "Cannot perform post-build checks - setup.bash not found"
        return 1
    fi
    
    return 0
}

# Function to generate build report
generate_build_report() {
    log_info "Generating build report..."
    
    local report_file="build_report.txt"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    cat > "$report_file" << EOF
Dojo Robot Build Report
Generated: $timestamp
Workspace: $(pwd)

=== Build Configuration ===
ROS Distribution: ${ROS_DISTRO:-"Not set"}
Python Version: $(python3 --version 2>/dev/null || echo "Not available")
Build Flags: $BUILD_FLAGS

=== Package Summary ===
EOF
    
    # Add package information
    if [ -d "install" ]; then
        echo "Installed Packages:" >> "$report_file"
        for pkg_dir in install/*/; do
            if [ -d "$pkg_dir" ]; then
                pkg_name=$(basename "$pkg_dir")
                echo "  - $pkg_name" >> "$report_file"
            fi
        done
    else
        echo "No packages installed" >> "$report_file"
    fi
    
    echo "" >> "$report_file"
    echo "=== Build Status ===" >> "$report_file"
    
    # Add validation results
    if validate_build_results >/dev/null 2>&1; then
        echo "Build Status: SUCCESS" >> "$report_file"
    else
        echo "Build Status: FAILED" >> "$report_file"
    fi
    
    echo "" >> "$report_file"
    echo "=== Next Steps ===" >> "$report_file"
    echo "To use the workspace:" >> "$report_file"
    echo "  source install/setup.bash" >> "$report_file"
    echo "" >> "$report_file"
    echo "To launch the robot:" >> "$report_file"
    echo "  ros2 launch robot_bringup bringup.launch.py" >> "$report_file"
    
    log_success "Build report generated: $report_file"
}

# Function to clean build artifacts
clean_build() {
    log_info "Cleaning previous build artifacts..."
    rm -rf build/ install/ log/
    mkdir -p build install log
}

# Function to clean legacy packages from install directory
clean_legacy_packages() {
    log_info "Cleaning legacy packages from install directory..."
    
    # Legacy packages that should be removed from install
    local legacy_packages=(
        "arduino_bridge"
        "ros2arduino_bridge"
        "robot_sensors"
        "vision_system"
        "nv21_converter_pkg"
        "robot_launch"
    )
    
    for pkg in "${legacy_packages[@]}"; do
        if [ -d "install/$pkg" ]; then
            log_info "Removing legacy package from install: $pkg"
            rm -rf "install/$pkg"
        fi
    done
}

# Function to get package list in dependency order
get_build_order() {
    # Packages that should be excluded from build (legacy/redundant)
    local excluded_packages=(
        "arduino_bridge"        # Replaced by robot_hardware
        "ros2arduino_bridge"    # Replaced by robot_hardware  
        "robot_sensors"         # Replaced by robot_hardware
        "vision_system"         # Replaced by robot_perception
        "camera_ws"             # Replaced by robot_hardware
        "nv21_converter_pkg"    # Legacy package
        "robot_launch"          # Replaced by robot_bringup
        "camera_ros"            # Legacy camera package
        "libcamera"             # Legacy camera package
        "sllidar_ros2"          # Legacy LiDAR package
    )
    
    # Get all packages in workspace
    local all_packages=($(colcon list -n 2>/dev/null || echo ""))
    
    # Filter out excluded packages
    local filtered_packages=()
    for pkg in "${all_packages[@]}"; do
        local exclude=false
        for excluded in "${excluded_packages[@]}"; do
            if [ "$pkg" = "$excluded" ]; then
                exclude=true
                # Log to stderr to avoid interfering with package list
                echo "⚠️  Excluding legacy/redundant package: $pkg" >&2
                break
            fi
        done
        if [ "$exclude" = false ]; then
            filtered_packages+=("$pkg")
        fi
    done
    
    # Recommended build order for new architecture
    local build_order=(
        "robot_interfaces"      # Custom messages (no dependencies)
        "robot_description"     # Robot models (depends on interfaces)
        "robot_hardware"        # Hardware drivers (depends on interfaces)
        "robot_control"         # High-level control (depends on hardware)
        "robot_perception"      # Computer vision (optional)
        "robot_navigation"      # Navigation (optional)
        "robot_gazebo"          # Simulation (depends on description)
        "robot_bringup"         # System orchestration (depends on all)
    )
    
    # Build packages in order, then add any remaining
    local ordered_packages=()
    
    # Add packages in preferred order
    for pkg in "${build_order[@]}"; do
        if [[ " ${filtered_packages[*]} " =~ " $pkg " ]]; then
            ordered_packages+=("$pkg")
        fi
    done
    
    # Add any remaining packages not in the predefined order
    for pkg in "${filtered_packages[@]}"; do
        if [[ ! " ${ordered_packages[*]} " =~ " $pkg " ]]; then
            ordered_packages+=("$pkg")
            # Log to stderr to avoid interfering with package list
            echo "ℹ️  Adding package not in predefined order: $pkg" >&2
        fi
    done
    
    echo "${ordered_packages[@]}"
}

# Function to validate package exclusion (backup_packages removed during cleanup)
validate_package_exclusion() {
    log_info "Backup packages have been removed during codebase cleanup..."
    # Note: backup_packages directory was removed as part of codebase cleanup
    # This function is kept for compatibility but no longer performs backup package validation
    
    log_success "Package exclusion validation complete"
}

# Function to validate configuration before build
validate_configuration() {
    log_info "Validating robot configuration..."
    
    # Check if master configuration file exists
    if [ ! -f "config/robot_config.yaml" ]; then
        log_error "Master configuration file not found: config/robot_config.yaml"
        log_info "Please ensure the configuration file exists before building"
        return 1
    fi
    
    # Check if configuration validation script exists
    if [ ! -f "scripts/test_configuration.py" ]; then
        log_warning "Configuration validation script not found, skipping validation"
        return 0
    fi
    
    # Run configuration validation
    log_info "Running configuration validation script..."
    if python3 scripts/test_configuration.py; then
        log_success "Configuration validation passed"
        return 0
    else
        log_error "Configuration validation failed"
        log_info "Please fix configuration issues before building"
        return 1
    fi
}

# Function to check hardware dependencies
check_hardware_dependencies() {
    log_info "Checking hardware dependencies..."
    
    # Check for required hardware interfaces
    local missing_deps=()
    
    # Check for serial port access (for Arduino)
    if [ ! -d "/dev/serial" ] && [ ! -e "/dev/ttyACM0" ] && [ ! -e "/dev/ttyUSB0" ]; then
        log_warning "No serial devices detected - Arduino functionality may be limited"
    fi
    
    # Check for camera devices
    if [ ! -d "/dev/v4l" ] && [ ! -e "/dev/video0" ]; then
        log_warning "No camera devices detected - camera functionality may be limited"
    fi
    
    # Check for Python dependencies
    local python_deps=("yaml" "serial" "cv2")
    for dep in "${python_deps[@]}"; do
        if ! python3 -c "import $dep" 2>/dev/null; then
            missing_deps+=("python3-$dep")
        fi
    done
    
    # Check for ROS 2 packages
    local ros_deps=("rclpy" "std_msgs" "geometry_msgs" "sensor_msgs")
    for dep in "${ros_deps[@]}"; do
        if ! python3 -c "import $dep" 2>/dev/null; then
            missing_deps+=("ros-jazzy-$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_warning "Missing dependencies detected:"
        for dep in "${missing_deps[@]}"; do
            echo "  - $dep"
        done
        log_info "Consider installing missing dependencies with: sudo apt install ${missing_deps[*]}"
    else
        log_success "All hardware dependencies satisfied"
    fi
    
    return 0
}

# Function to build workspace
build_workspace() {
    log_info "Starting build process..."
    
    # Get packages to build
    local packages=($(get_build_order))
    
    if [ ${#packages[@]} -eq 0 ]; then
        log_warning "No packages found to build"
        return 0
    fi
    
    log_info "Found ${#packages[@]} packages to build:"
    for pkg in "${packages[@]}"; do
        echo "  - $pkg"
    done
    
    # Try building all packages at once first (fastest)
    log_info "Attempting to build all packages..."
    
    # Capture build output for analysis
    local build_log="build_output.log"
    
    if colcon build $BUILD_FLAGS --packages-select "${packages[@]}" 2>&1 | tee "$build_log"; then
        log_success "All packages built successfully!"
        
        # Validate build results
        if validate_build_results; then
            log_success "Build validation passed"
        else
            log_warning "Build completed but validation failed"
        fi
        
        return 0
    else
        log_warning "Batch build failed, analyzing errors..."
        
        # Analyze build log for common issues
        if grep -q "CMake Error" "$build_log"; then
            log_error "CMake configuration errors detected"
        fi
        
        if grep -q "No module named" "$build_log"; then
            log_error "Python import errors detected - check dependencies"
        fi
        
        if grep -q "fatal error.*No such file" "$build_log"; then
            log_error "Missing header files detected - check dependencies"
        fi
    fi
    
    log_warning "Batch build failed, trying individual package builds..."
    
    # Build packages individually if batch build fails
    local failed_packages=()
    
    for pkg in "${packages[@]}"; do
        log_info "Building package: $pkg"
        
        local attempt=1
        local success=false
        
        while [ $attempt -le $MAX_ATTEMPTS ] && [ "$success" = false ]; do
            if [ $attempt -gt 1 ]; then
                log_info "Retry attempt $attempt for $pkg"
                # Clean package-specific build artifacts
                rm -rf "build/$pkg" "install/$pkg"
            fi
            
            # Capture individual package build output
            local pkg_log="build_${pkg}_attempt_${attempt}.log"
            
            if colcon build $BUILD_FLAGS --packages-select "$pkg" 2>&1 | tee "$pkg_log"; then
                log_success "Successfully built $pkg"
                success=true
                
                # Source the workspace after each successful build
                if [ -f "install/setup.bash" ]; then
                    source install/setup.bash
                fi
                
                # Clean up successful build log
                rm -f "$pkg_log"
            else
                log_warning "Build attempt $attempt failed for $pkg"
                
                # Analyze failure for specific package
                if grep -q "CMake Error" "$pkg_log"; then
                    log_error "  → CMake configuration error in $pkg"
                elif grep -q "No module named" "$pkg_log"; then
                    log_error "  → Python import error in $pkg - check dependencies"
                elif grep -q "fatal error.*No such file" "$pkg_log"; then
                    log_error "  → Missing header files in $pkg - check dependencies"
                else
                    log_error "  → Unknown build error in $pkg - check $pkg_log"
                fi
                
                ((attempt++))
            fi
        done
        
        if [ "$success" = false ]; then
            log_error "Failed to build $pkg after $MAX_ATTEMPTS attempts"
            failed_packages+=("$pkg")
        fi
    done
    
    # Report results
    if [ ${#failed_packages[@]} -eq 0 ]; then
        log_success "All packages built successfully!"
    else
        log_error "Failed to build ${#failed_packages[@]} packages:"
        for pkg in "${failed_packages[@]}"; do
            echo "  - $pkg"
        done
        return 1
    fi
}

# Function to run tests (optional)
run_tests() {
    if [ "$1" = "--test" ]; then
        log_info "Running tests..."
        colcon test --packages-select $(get_build_order | tr ' ' '\n' | head -5 | tr '\n' ' ') || log_warning "Some tests failed"
        colcon test-result --verbose || true
    fi
}

# Function to display usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --clean     Clean build artifacts before building"
    echo "  --deps      Install dependencies before building"
    echo "  --test      Run tests after building"
    echo "  --skip-validation  Skip configuration validation"
    echo "  --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Standard build"
    echo "  $0 --clean --deps     # Clean build with dependency installation"
    echo "  $0 --test             # Build and run tests"
}

# Main execution
main() {
    local clean_build_flag=false
    local install_deps_flag=false
    local run_tests_flag=false
    local skip_validation_flag=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean)
                clean_build_flag=true
                shift
                ;;
            --deps)
                install_deps_flag=true
                shift
                ;;
            --test)
                run_tests_flag=true
                shift
                ;;
            --skip-validation)
                skip_validation_flag=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Execute build steps
    check_workspace
    source_ros
    
    # Validate backup packages are properly excluded
    validate_package_exclusion
    
    # Always clean legacy packages to prevent conflicts
    clean_legacy_packages
    
    # Validate configuration before building (unless skipped)
    if [ "$skip_validation_flag" = false ]; then
        if ! validate_configuration; then
            log_error "Configuration validation failed, aborting build"
            log_info "Use --skip-validation to bypass this check"
            exit 1
        fi
    else
        log_warning "Skipping configuration validation as requested"
    fi
    
    # Check hardware dependencies
    check_hardware_dependencies
    
    if [ "$install_deps_flag" = true ]; then
        if ! install_dependencies; then
            log_error "Dependency installation failed, aborting build"
            exit 1
        fi
    else
        # Always check dependencies even if not installing
        if ! detect_missing_dependencies; then
            log_warning "Missing dependencies detected, but continuing build"
            log_info "Use --deps flag to install dependencies automatically"
        fi
    fi
    
    if [ "$clean_build_flag" = true ]; then
        clean_build
    fi
    
    # Build the workspace
    if build_workspace; then
        log_success "Build completed successfully!"
        
        # Perform post-build validation
        if validate_build_results; then
            log_success "Build validation passed"
        else
            log_warning "Build validation failed - some issues detected"
        fi
        
        # Perform post-build checks
        post_build_checks
        
        # Generate build report
        generate_build_report
        
    else
        log_error "Build failed!"
        log_info "Check the build logs for detailed error information"
        exit 1
    fi
    
    if [ "$run_tests_flag" = true ]; then
        run_tests --test
    fi
    
    # Final instructions
    log_success "Build process completed!"
    echo ""
    log_info "To use the workspace, run:"
    echo "  source install/setup.bash"
    echo ""
    log_info "To launch the robot system:"
    echo "  ros2 launch robot_bringup bringup.launch.py"
    echo ""
    log_info "To visualize the robot:"
    echo "  ros2 launch robot_description display.launch.py"
    echo ""
    log_info "Build report saved to: build_report.txt"
}

# Run main function with all arguments
main "$@"