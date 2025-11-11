# Multi-Robot Swarm Testing Guide

Quick reference for testing the multi-robot swarm system (Task 11.6).

## Prerequisites

✓ robot_swarm package built
✓ All swarm nodes implemented
✓ Multi-robot simulation environment
⚠ Multiple robot instances configured

## Quick Start

### 1. Build Package
```bash
colcon build --packages-select robot_swarm
source install/setup.bash
```

### 2. Launch Multi-Robot Simulation
```bash
# Launch with 2 robots
ros2 launch robot_swarm multi_robot_simulation.launch.py num_robots:=2

# Or with 5 robots
ros2 launch robot_swarm multi_robot_simulation.launch.py num_robots:=5
```

### 3. Run Tests
```bash
python3 src/robot_swarm/comprehensive_swarm_test.py
```

## Test Scenarios

| Test | Robots | Duration | Requirements |
|------|--------|----------|--------------|
| Robot Discovery | 2-5 | 10s | 2.2.1 |
| Task Allocation | 2-5 | 20s | 2.2.2 |
| Map Sync | 2-5 | 10s | 2.2.3 |
| Formation (Line) | 2-5 | 15s | 2.2.5 |
| Formation (Wedge) | 2-5 | 15s | 2.2.5 |
| Formation (Circle) | 2-5 | 15s | 2.2.5 |
| Failure Handling | 2-5 | 15s | 2.2.4 |

## Success Criteria

- ✓ Robot Discovery: 100% within 10s
- ✓ Task Allocation: Efficient distribution
- ✓ Map Sync: <500ms latency
- ✓ Formation Control: <0.5m error
- ✓ Failure Handling: Automatic redistribution

## Test Metrics

1. Robot discovery rate
2. Task allocation efficiency
3. Map synchronization latency
4. Formation position accuracy
5. Failure recovery time
6. Communication reliability
7. Task distribution fairness

## Individual Component Testing

### SwarmCoordinator
```bash
ros2 run robot_swarm swarm_coordinator \
    --ros-args -p robot_id:=robot_0
```

### FormationController
```bash
ros2 run robot_swarm formation_controller \
    --ros-args \
    -p robot_id:=robot_0 \
    -p formation_type:=line \
    -p robot_index:=0 \
    -p num_robots:=3
```

### CollaborativeMapper
```bash
ros2 run robot_swarm collaborative_mapper \
    --ros-args -p robot_id:=robot_0
```

## Troubleshooting

### No robots discovered
**Solution**: Check DDS configuration and network connectivity

### Tasks not allocated
**Solution**: Verify SwarmCoordinator is running on all robots

### High map sync latency
**Solution**: Check network bandwidth and QoS settings

### Formation not maintained
**Solution**: Verify FormationController parameters and leader position

## Files

- `comprehensive_swarm_test.py` - Complete test suite
- `TASK_11.6_TEST_REPORT.md` - Detailed test report
- `swarm_test_results.json` - Test results (generated)

## Results

Test results will be saved to:
- `swarm_test_results.json` - Detailed results with metrics

## Contact

For issues or questions, refer to:
- Design document: `.kiro/specs/cutting-edge-features-implementation/design.md`
- Requirements: `.kiro/specs/cutting-edge-features-implementation/requirements.md`
- Tasks: `.kiro/specs/cutting-edge-features-implementation/tasks.md`
