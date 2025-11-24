# Dojo Robot - ROS 2 Navigation & Exploration System

## Overview
This project integrates the **Husarion ROSbot XL** with a custom navigation and exploration stack ("Dojo"). It features SLAM, Nav2, Autonomous Exploration, Semantic Mapping, and Gaussian Splatting data collection.

## Key Packages
*   **`rosbot_xl_*`**: Vendor packages for robot description, control, and simulation.
*   **`robot_navigation`**: Custom Nav2 configuration and `autonomous_explorer` node.
*   **`robot_semantic_slam`**: Semantic mapping features.
*   **`dojo_navigation`**: (New) Survey planning and advanced navigation logic.
*   **`dojo_semantic`**: (New) Semantic navigation logic.

## Installation
1.  **Dependencies**:
    ```bash
    sudo apt install ros-humble-desktop
    sudo apt install ros-humble-nav2-bringup ros-humble-slam-toolbox
    pip3 install -r requirements.txt # If available
    ```

2.  **Build**:
    ```bash
    colcon build --symlink-install
    source install/setup.bash
    ```

## Usage

### 1. Main Simulation Launch
Launches Gazebo, Robot, SLAM, Nav2, and Exploration.
```bash
ros2 launch launch_dojo_rosbot_xl.py world:=office slam:=true navigation:=true autonomous_exploration:=true gui:=true rviz:=true
```

**Key Arguments:**
*   `world`: Gazebo world name (e.g., `office`, `maze`).
*   `slam`: Enable SLAM (`true`/`false`).
*   `navigation`: Enable Nav2 (`true`/`false`).
*   `autonomous_exploration`: Enable frontier-based exploration (`true`/`false`).
*   `gaussian_splatting`: Enable spin behavior for data collection (`true`/`false`).

### 2. Gaussian Splat Data Collection
**Step 1: Start Simulation** (as above, with `gaussian_splatting:=true`)

**Step 2: Run Pipeline Manager** (on Laptop)
```bash
python3 scripts/splat_pipeline_manager.py
```
This script orchestrates the survey, data transfer, and training.

**Manual Triggering:**
*   **Survey Planner**: `ros2 run dojo_navigation survey_planner`
*   **Semantic Navigator**: `ros2 run dojo_semantic dynamic_navigator`

## Troubleshooting

### Robot Not Spawning / No TF
*   Ensure `use_sim_time` is `true` in `src/rosbot_xl_controller/config/diff_drive.yaml`.
*   Check `ros2 topic echo /tf` to see if `odom` -> `base_link` is being published.

### Nav2 Issues
*   Ensure SLAM is running and publishing `/map`.
*   Check global costmap: `ros2 topic echo /global_costmap/costmap`.

### Build Errors
*   If you see "duplicate package" errors, ensure you don't have backup folders (like `sim_ws`) inside your workspace.
*   Run `colcon build --packages-select <package_name>` to isolate issues.
