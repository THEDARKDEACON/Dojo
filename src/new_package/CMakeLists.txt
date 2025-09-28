cmake_minimum_required(VERSION 3.5)
project(new_package)

# Default to C++14 if not set
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

# Dependencies
find_package(ament_cmake REQUIRED)
find_package(xacro REQUIRED)
find_package(robot_state_publisher REQUIRED)
find_package(gazebo_ros REQUIRED)
find_package(ament_lint_auto REQUIRED)

# Install URDF files
install(DIRECTORY urdf/
  DESTINATION share/${PROJECT_NAME}/urdf
)

# Install launch files
install(DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
)

# Install config files
install(DIRECTORY config/
  DESTINATION share/${PROJECT_NAME}/config
)

# Install world files
install(DIRECTORY worlds/
  DESTINATION share/${PROJECT_NAME}/worlds
)

# Conditionally install meshes
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/meshes")
  install(DIRECTORY meshes/
    DESTINATION share/${PROJECT_NAME}/meshes
  )
endif()

# Export dependencies
ament_export_dependencies(
  xacro
  robot_state_publisher
  gazebo_ros
)

# Linting support
ament_lint_auto_find_test_dependencies()

ament_package()
