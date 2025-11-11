# Installation Guide for Robot RL Navigation

## Prerequisites

- ROS2 Humble or later
- Python 3.8+
- CUDA-capable GPU (recommended for training)

## Installation Steps

### 1. Install Python Dependencies

```bash
cd src/robot_rl_navigation
pip3 install -r requirements.txt
```

Or install individually:

```bash
pip3 install stable-baselines3 gymnasium torch numpy tensorboard
```

### 2. Build ROS2 Package

```bash
cd ~/Dojo  # Or your workspace root
colcon build --packages-select robot_rl_navigation
source install/setup.bash
```

### 3. Verify Installation

```bash
# Check if package is available
ros2 pkg list | grep robot_rl_navigation

# Check executables
ros2 pkg executables robot_rl_navigation
```

Expected output:
```
robot_rl_navigation navigation_env
robot_rl_navigation policy_manager
robot_rl_navigation rl_navigator
robot_rl_navigation train_agent
```

## Optional: GPU Support

For faster training with GPU acceleration:

### CUDA Installation

1. Install NVIDIA drivers
2. Install CUDA Toolkit (11.8 or later)
3. Install cuDNN

### PyTorch with CUDA

```bash
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

Verify GPU is available:

```bash
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'gymnasium'`

**Solution**:
```bash
pip3 install gymnasium
```

### CUDA Not Available

**Problem**: PyTorch not detecting GPU

**Solution**:
1. Check NVIDIA driver: `nvidia-smi`
2. Reinstall PyTorch with CUDA support
3. Verify CUDA version matches PyTorch

### Build Errors

**Problem**: Package fails to build

**Solution**:
```bash
# Clean build
rm -rf build/ install/ log/
colcon build --packages-select robot_rl_navigation --cmake-clean-cache
```

## Testing Installation

### Test NavigationEnv

```bash
# This will fail without ROS2 running, but tests imports
python3 -c "from robot_rl_navigation.navigation_env import NavigationEnv; print('OK')"
```

### Test Training Script

```bash
ros2 run robot_rl_navigation train_agent --help
```

### Test RL Navigator

```bash
ros2 run robot_rl_navigation rl_navigator --help
```

## Next Steps

After successful installation:

1. Read the [README.md](README.md) for usage instructions
2. Start training: See "Training a New Policy" section
3. Deploy trained policy: See "Using Trained Policy" section

## Support

For issues:
- Check [README.md](README.md) troubleshooting section
- Review [docs/TASK_10.2_10.6_COMPLETE.md](../../docs/TASK_10.2_10.6_COMPLETE.md)
- Open an issue on GitHub
