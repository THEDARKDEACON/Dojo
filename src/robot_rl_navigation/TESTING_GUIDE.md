# RL Navigation Testing Guide

Quick reference for testing the RL navigation system (Task 10.7).

## Prerequisites

✓ All dependencies installed (stable-baselines3, gymnasium, torch)
✓ Package built and sourced
✓ Simulation worlds available
⚠ Trained RL policy required

## Quick Start

### 1. Validate System
```bash
cd src/robot_rl_navigation
python3 comprehensive_rl_test.py
```

### 2. Train Policy (if needed)
```bash
# Build and source
colcon build --packages-select robot_rl_navigation
source install/setup.bash

# Train (takes 2-4 hours)
ros2 run robot_rl_navigation train_agent
```

### 3. Run Tests
```bash
# Terminal 1: Launch simulation
ros2 launch robot_gazebo complete_robot_simulation.launch.py \
    world:=mapping_world \
    use_rl_navigation:=true

# Terminal 2: Run tests
python3 src/robot_rl_navigation/test_rl_navigation.py
```

## Test Environments

| Environment | Complexity | Test Goals |
|-------------|------------|------------|
| mapping_world | Simple | 4 waypoints |
| house | Medium | 4 waypoints |
| office_small | Medium | 4 waypoints |
| warehouse | High | 4 waypoints |

## Success Criteria

- ✓ Success Rate: ≥90%
- ✓ Collision Rate: <5%
- ✓ Multi-environment testing completed
- ✓ Nav2 comparison documented

## Test Metrics

1. Success rate (goal reached)
2. Collision rate (obstacle contact)
3. Average completion time
4. Average path length
5. Path efficiency
6. RL confidence scores
7. Nav2 fallback frequency

## Troubleshooting

### No trained model found
**Solution**: Run `ros2 run robot_rl_navigation train_agent`

### Simulation not starting
**Solution**: Check Gazebo installation and world files

### Low success rate (<90%)
**Solution**: Retrain with adjusted hyperparameters or longer training

### High collision rate (>5%)
**Solution**: Adjust reward function to penalize collisions more

## Files

- `comprehensive_rl_test.py` - System validation
- `test_rl_navigation.py` - Comprehensive testing
- `validate_rl_system.py` - Quick validation
- `TASK_10.7_TEST_REPORT.md` - Detailed test report
- `test_report_template.json` - Results template

## Results

Test results will be saved to:
- `rl_navigation_test_results.json` - Detailed results
- `validation_results.json` - System validation
- `test_report_template.json` - Report template

## Contact

For issues or questions, refer to:
- Design document: `.kiro/specs/cutting-edge-features-implementation/design.md`
- Requirements: `.kiro/specs/cutting-edge-features-implementation/requirements.md`
- Tasks: `.kiro/specs/cutting-edge-features-implementation/tasks.md`
