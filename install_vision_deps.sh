#!/bin/bash

# Install Vision Detection Dependencies
# This script installs the required packages for vision detection functionality

set -e

echo "🔧 Installing Vision Detection Dependencies..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if pip is available
if ! command -v pip3 >/dev/null 2>&1; then
    log_error "pip3 not found. Please install python3-pip first:"
    echo "sudo apt update && sudo apt install python3-pip"
    exit 1
fi

log_info "Installing PyTorch and vision dependencies..."

# Install PyTorch (CPU version for compatibility)
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install ultralytics (YOLO)
pip3 install ultralytics

# Install ONNX runtime
pip3 install onnxruntime

# Install additional vision dependencies
pip3 install opencv-python pillow

log_success "Vision detection dependencies installed successfully!"

echo ""
log_info "To enable vision detection, launch with:"
echo "ros2 launch complete_robot_simulation.launch.py vision:=true"

echo ""
log_info "To test vision detection:"
echo "./test_essential_functionality.sh"