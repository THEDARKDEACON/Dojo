cmake_minimum_required(VERSION 3.8)
project(robot_gazebo)

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

# Gazebo packages (Harmonic)
find_package(ros_gz_sim REQUIRED)
find_package(ros_gz_bridge REQUIRED)
find_package(ros_gz_image REQUIRED)

# Control and hardware
find_package(ros2_control REQUIRED)
find_package(ros2_controllers REQUIRED)
find_package(controller_manager REQUIRED)
find_package(hardware_interface REQUIRED)
find_package(pluginlib REQUIRED)
find_package(std_srvs REQUIRED)

# Robot description and control
find_package(urdf REQUIRED)
find_package(xacro REQUIRED)

# Install Python package using setup.py
ament_python_install_package(${PROJECT_NAME})

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
)

# Install RViz configuration files
install(
  DIRECTORY rviz/
  DESTINATION share/${PROJECT_NAME}/rviz
  PATTERN "*.rviz"
)

# Install world files
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/worlds")
  install(
    DIRECTORY worlds/
    DESTINATION share/${PROJECT_NAME}/worlds
    PATTERN "*.world"
    PATTERN "*.sdf"
  )
endif()

# Install models
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/models")
  install(
    DIRECTORY models/
    DESTINATION share/${PROJECT_NAME}/models
  )
endif()

# Install Python scripts
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/scripts")
  install(
    DIRECTORY scripts/
    DESTINATION lib/${PROJECT_NAME}
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
endif()

# Export include directories
ament_export_include_directories(include)

# Export dependencies
ament_export_dependencies(
  rclcpp
  rclpy
  std_msgs
  sensor_msgs
  geometry_msgs
  nav_msgs
  tf2_ros
  tf2_geometry_msgs
  ros_gz_sim
  ros_gz_bridge
  ros_gz_image

  ros2_control
  ros2_controllers
  controller_manager
  hardware_interface
  pluginlib
  urdf
  xacro
  rcl_interfaces
  std_srvs
)

# Register the package with ament
ament_package(
  CONFIG_EXTRAS "${PROJECT_NAME}-extras.cmake"
)
