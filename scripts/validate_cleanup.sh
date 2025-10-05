#!/bin/bash

# Cleanup Validation Script
# This script validates the system integrity before and after cleanup operations
# Requirements: 6.1, 6.2

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Global variables
WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATION_LOG="${WORKSPACE_ROOT}/validation_report.log"
ERRORS_FOUND=0

# Initialize validation log
init_validation_log() {
    echo "Cleanup Validation Report - $(date)" > "$VALIDATION_LOG"
    echo "========================================" >> "$VALIDATION_LOG"
    echo "" >> "$VALIDATION_LOG"
}

# Function to validate build system
validate_build_system() {
    log_info "Validating build system..."
    
    cd "$WORKSPACE_ROOT"
    
    # Check if we're in a ROS2 workspace
    if [[ ! -f "src" ]] || [[ ! -d "src" ]]; then
        log_error "Not in a valid ROS2 workspace (no src directory found)"
        echo "ERROR: Invalid ROS2 workspace structure" >> "$VALIDATION_LOG"
        ((ERRORS_FOUND++))
        return 1
    fi
    
    # Test clean build
    log_info "Testing clean build process..."
    if [[ -d "build" ]]; then
        rm -rf build
    fi
    if [[ -d "install" ]]; then
        rm -rf install
    fi
    
    # Source ROS2 if available
    if [[ -f "/opt/ros/humble/setup.bash" ]]; then
        source /opt/ros/humble/setup.bash
    elif [[ -f "/opt/ros/foxy/setup.bash" ]]; then
        source /opt/ros/foxy/setup.bash
    else
        log_warning "No ROS2 installation found, skipping build test"
        echo "WARNING: No ROS2 installation found" >> "$VALIDATION_LOG"
        return 0
    fi
    
    # Attempt to build workspace
    if colcon build --symlink-install 2>&1 | tee -a "$VALIDATION_LOG"; then
        log_success "Build system validation passed"
        echo "SUCCESS: Build system working" >> "$VALIDATION_LOG"
    else
        log_error "Build system validation failed"
        echo "ERROR: Build system failed" >> "$VALIDATION_LOG"
        ((ERRORS_FOUND++))
        return 1
    fi
    
    return 0
}

# Function to validate launch files
validate_launch_files() {
    log_info "Validating launch files for syntax errors..."
    
    local launch_files_found=0
    local launch_files_valid=0
    
    # Find all launch files in the workspace
    while IFS= read -r -d '' launch_file; do
        ((launch_files_found++))
        log_info "Checking launch file: $launch_file"
        
        # Check Python syntax
        if python3 -m py_compile "$launch_file" 2>/dev/null; then
            ((launch_files_valid++))
            echo "VALID: $launch_file" >> "$VALIDATION_LOG"
        else
            log_error "Syntax error in launch file: $launch_file"
            echo "ERROR: Syntax error in $launch_file" >> "$VALIDATION_LOG"
            ((ERRORS_FOUND++))
        fi
    done < <(find "$WORKSPACE_ROOT/src" -name "*.launch.py" -print0 2>/dev/null)
    
    log_info "Found $launch_files_found launch files, $launch_files_valid valid"
    echo "Launch files: $launch_files_found found, $launch_files_valid valid" >> "$VALIDATION_LOG"
    
    return 0
}

# Function to validate simulation capabilities
validate_simulation_capabilities() {
    log_info "Validating simulation launch capabilities..."
    
    # Check for Gazebo installation
    if command -v gazebo &> /dev/null; then
        log_success "Gazebo found in PATH"
        echo "SUCCESS: Gazebo installation found" >> "$VALIDATION_LOG"
    else
        log_warning "Gazebo not found in PATH"
        echo "WARNING: Gazebo not found" >> "$VALIDATION_LOG"
    fi
    
    # Check for key simulation launch files
    local sim_launch_files=(
        "src/robot_gazebo/launch/gazebo.launch.py"
        "src/robot_gazebo/launch/simulation.launch.py"
        "src/robot_description/launch/description.launch.py"
    )
    
    for launch_file in "${sim_launch_files[@]}"; do
        local full_path="$WORKSPACE_ROOT/$launch_file"
        if [[ -f "$full_path" ]]; then
            log_success "Found simulation launch file: $launch_file"
            echo "FOUND: $launch_file" >> "$VALIDATION_LOG"
        else
            log_warning "Missing simulation launch file: $launch_file"
            echo "MISSING: $launch_file" >> "$VALIDATION_LOG"
        fi
    done
    
    return 0
}

# Function to validate hardware launch capabilities
validate_hardware_capabilities() {
    log_info "Validating hardware launch capabilities..."
    
    # Check for key hardware launch files
    local hw_launch_files=(
        "src/robot_bringup/launch/bringup.launch.py"
        "src/robot_control/launch/robot_control.launch.py"
    )
    
    for launch_file in "${hw_launch_files[@]}"; do
        local full_path="$WORKSPACE_ROOT/$launch_file"
        if [[ -f "$full_path" ]]; then
            log_success "Found hardware launch file: $launch_file"
            echo "FOUND: $launch_file" >> "$VALIDATION_LOG"
        else
            log_warning "Missing hardware launch file: $launch_file"
            echo "MISSING: $launch_file" >> "$VALIDATION_LOG"
        fi
    done
    
    return 0
}

# Function to validate package dependencies
validate_package_dependencies() {
    log_info "Validating package dependencies..."
    
    # Check for package.xml files and basic structure
    local packages_found=0
    
    while IFS= read -r -d '' package_xml; do
        ((packages_found++))
        local package_dir=$(dirname "$package_xml")
        local package_name=$(basename "$package_dir")
        
        log_info "Validating package: $package_name"
        
        # Check if package.xml is valid XML
        if xmllint --noout "$package_xml" 2>/dev/null; then
            echo "VALID: Package $package_name has valid package.xml" >> "$VALIDATION_LOG"
        else
            log_error "Invalid package.xml in package: $package_name"
            echo "ERROR: Invalid package.xml in $package_name" >> "$VALIDATION_LOG"
            ((ERRORS_FOUND++))
        fi
        
    done < <(find "$WORKSPACE_ROOT/src" -name "package.xml" -print0 2>/dev/null)
    
    log_info "Found $packages_found packages"
    echo "Packages found: $packages_found" >> "$VALIDATION_LOG"
    
    return 0
}

# Function to generate validation report
generate_validation_report() {
    log_info "Generating validation report..."
    
    echo "" >> "$VALIDATION_LOG"
    echo "========================================" >> "$VALIDATION_LOG"
    echo "Validation Summary - $(date)" >> "$VALIDATION_LOG"
    echo "========================================" >> "$VALIDATION_LOG"
    
    if [[ $ERRORS_FOUND -eq 0 ]]; then
        echo "OVERALL STATUS: PASSED" >> "$VALIDATION_LOG"
        log_success "All validations passed! System is ready for cleanup."
    else
        echo "OVERALL STATUS: FAILED ($ERRORS_FOUND errors found)" >> "$VALIDATION_LOG"
        log_error "Validation failed with $ERRORS_FOUND errors. Please fix issues before proceeding with cleanup."
    fi
    
    echo "" >> "$VALIDATION_LOG"
    echo "Full report saved to: $VALIDATION_LOG"
    
    # Display summary
    echo ""
    echo "========================================="
    echo "           VALIDATION SUMMARY"
    echo "========================================="
    if [[ $ERRORS_FOUND -eq 0 ]]; then
        echo -e "${GREEN}✓ System validation PASSED${NC}"
        echo -e "${GREEN}✓ Ready for cleanup operations${NC}"
    else
        echo -e "${RED}✗ System validation FAILED${NC}"
        echo -e "${RED}✗ $ERRORS_FOUND errors found${NC}"
        echo -e "${YELLOW}! Please review $VALIDATION_LOG for details${NC}"
    fi
    echo "========================================="
}

# Main validation function
run_full_validation() {
    log_info "Starting full system validation..."
    init_validation_log
    
    # Run all validation checks
    validate_build_system
    validate_launch_files
    validate_simulation_capabilities
    validate_hardware_capabilities
    validate_package_dependencies
    
    # Generate final report
    generate_validation_report
    
    # Return appropriate exit code
    if [[ $ERRORS_FOUND -eq 0 ]]; then
        return 0
    else
        return 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Cleanup Validation Script"
    echo ""
    echo "Options:"
    echo "  --full, -f          Run full validation (default)"
    echo "  --build, -b         Validate build system only"
    echo "  --launch, -l        Validate launch files only"
    echo "  --simulation, -s    Validate simulation capabilities only"
    echo "  --hardware, -h      Validate hardware capabilities only"
    echo "  --dependencies, -d  Validate package dependencies only"
    echo "  --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                  # Run full validation"
    echo "  $0 --build          # Test build system only"
    echo "  $0 --launch         # Check launch files only"
}

# Main script execution
main() {
    case "${1:-}" in
        --full|-f|"")
            run_full_validation
            ;;
        --build|-b)
            init_validation_log
            validate_build_system
            generate_validation_report
            ;;
        --launch|-l)
            init_validation_log
            validate_launch_files
            generate_validation_report
            ;;
        --simulation|-s)
            init_validation_log
            validate_simulation_capabilities
            generate_validation_report
            ;;
        --hardware|-h)
            init_validation_log
            validate_hardware_capabilities
            generate_validation_report
            ;;
        --dependencies|-d)
            init_validation_log
            validate_package_dependencies
            generate_validation_report
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"