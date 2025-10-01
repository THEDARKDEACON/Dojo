cmake_minimum_required(VERSION 3.8)
project(robot_navigation)

# Default to C++17
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
  set(CMAKE_CXX_EXTENSIONS OFF)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(ament_cmake_test REQUIRED)

# Core ROS 2 packages
find_package(rclcpp REQUIRED)
find_package(rclpy REQUIRED)
find_package(std_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(rcl_interfaces REQUIRED)

# Navigation2 core components
find_package(navigation2 REQUIRED)
find_package(nav2_common REQUIRED)
find_package(nav2_util REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(nav2_lifecycle_manager REQUIRED)

# Navigation2 components (only essential ones, add more as needed)
find_package(nav2_amcl REQUIRED)
find_package(nav2_behavior_tree REQUIRED)
find_package(nav2_bt_navigator REQUIRED)
find_package(nav2_controller REQUIRED)
find_package(nav2_core REQUIRED)
find_package(nav2_costmap_2d REQUIRED)
find_package(nav2_planner REQUIRED)

# SLAM and Localization
find_package(slam_toolbox REQUIRED)
find_package(robot_localization REQUIRED)

# Visualization
find_package(rviz_common REQUIRED)
find_package(rviz_rendering REQUIRED)

# Find Python dependencies
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

# Set Python install path
set(PYTHON_INSTALL_DIR "${PYTHON3_INSTALL_DIR}")

# Add include directories
include_directories(
  include
  ${rclcpp_INCLUDE_DIRS}
  ${rclpy_INCLUDE_DIRS}
  ${nav2_common_INCLUDE_DIRS}
)

# Install Python modules
install(
  DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/robot_navigation/
  DESTINATION ${PYTHON_INSTALL_DIR}/robot_navigation
  USE_SOURCE_PERMISSIONS
)

# Install launch files
install(
  DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
  PATTERN "*.launch.py"
  PATTERN "*.launch"
)

# Install configuration files
install(
  DIRECTORY config/
  DESTINATION share/${PROJECT_NAME}/config
  PATTERN "*.yaml"
  PATTERN "*.yml"
  PATTERN "*.rviz"
)

# Install maps
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/maps")
  install(
    DIRECTORY maps/
    DESTINATION share/${PROJECT_NAME}/maps
    PATTERN "*.pgm"
    PATTERN "*.yaml"
    PATTERN "*.png"
  )
endif()

# Install Python scripts
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/scripts")
  install(
    PROGRAMS scripts/
    DESTINATION lib/${PROJECT_NAME}
    USE_SOURCE_PERMISSIONS
  )
endif()

# Install package.xml and setup files
install(
  FILES
    package.xml
    setup.py
    setup.cfg
  DESTINATION share/${PROJECT_NAME}
)

# Add tests
if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  find_package(ament_cmake_gtest REQUIRED)
  find_package(ament_cmake_pytest REQUIRED)
  
  # Linting
  ament_lint_auto_find_test_dependencies()
  
  # Python tests - only add if test directory exists
  if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/test")
    ament_add_pytest_test(
      python_tests 
      "${CMAKE_CURRENT_SOURCE_DIR}/test"
      PYTHON_EXECUTABLE "${PYTHON_EXECUTABLE}"
    )
  endif()
  
  # C++ tests can be added here
  # ament_add_gtest(...)
  
  # Enable testing after adding all tests
  ament_enable_testing()
endif()

# Install Python entry points
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/robot_navigation/scripts")
  install(
    PROGRAMS
      ${CMAKE_CURRENT_SOURCE_DIR}/robot_navigation/scripts/*
    DESTINATION lib/${PROJECT_NAME}
    USE_SOURCE_PERMISSIONS
  )
endif()

# Export include directories
ament_export_include_directories(include)

# Export dependencies for other packages
ament_export_dependencies(
  rclcpp
  rclpy
  std_msgs
  sensor_msgs
  geometry_msgs
  nav_msgs
  tf2_ros
  tf2_geometry_msgs
  rcl_interfaces
  nav2_common
  nav2_msgs
  nav2_util
  nav2_behavior_tree
  nav2_bt_navigator
  nav2_controller
  nav2_core
  nav2_costmap_2d
  nav2_lifecycle_manager
  nav2_map_server
  nav2_navfn_planner
  nav2_planner
  slam_toolbox
  robot_localization
  rviz_common
  rviz_default_plugins
  rviz_rendering
)

# Install launch files
install(
  DIRECTORY
    launch
  DESTINATION share/${PROJECT_NAME}
)

# Register the package with ament
ament_package()
