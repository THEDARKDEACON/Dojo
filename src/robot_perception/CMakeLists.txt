cmake_minimum_required(VERSION 3.8)
project(robot_perception)

# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
endif()

# Find ament_cmake and Python
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

# Install Python package
ament_python_install_package(${PROJECT_NAME}
  PACKAGE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/${PROJECT_NAME}
)

# Install launch files
install(DIRECTORY
  launch/
  DESTINATION share/${PROJECT_NAME}/launch
  PATTERN "*.py"
  PATTERN "__pycache__" EXCLUDE
)

# Install config files
install(DIRECTORY
  config/
  DESTINATION share/${PROJECT_NAME}/config
)

# Install RViz config files
install(DIRECTORY
  rviz/
  DESTINATION share/${PROJECT_NAME}/rviz
  PATTERN "*.rviz"
)

# Install resource files
install(DIRECTORY
  resource/
  DESTINATION share/${PROJECT_NAME}/resource
)

# Install package.xml
install(
  FILES
    CMakeLists.txt
    package.xml
  DESTINATION
    share/${PROJECT_NAME}
)

# Install executable scripts
install(PROGRAMS
  scripts/camera_processor
  scripts/object_detector
  DESTINATION lib/${PROJECT_NAME}
)


# Add pytest tests if they exist
if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/test)
  find_package(ament_cmake_pytest REQUIRED)
  
  # Install test files
  install(DIRECTORY
    test/
    DESTINATION lib/${PYTHON_INSTALL_DIR}/${PROJECT_NAME}/test
    PATTERN "*.py"
    PATTERN "__pycache__" EXCLUDE
  )
  
  # Add pytest tests
  ament_add_pytest_test(
    test_robot_perception
    ${CMAKE_CURRENT_SOURCE_DIR}/test/test_robot_perception.py
    TIMEOUT 30
  )
  
  # Add specific test files if they exist
  if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/test/test_camera_processor.py)
    ament_add_pytest_test(
      test_camera_processor
      ${CMAKE_CURRENT_SOURCE_DIR}/test/test_camera_processor.py
      TIMEOUT 30
    )
  endif()
  
  if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/test/test_object_detector.py)
    ament_add_pytest_test(
      test_object_detector
      ${CMAKE_CURRENT_SOURCE_DIR}/test/test_object_detector.py
      TIMEOUT 30
    )
  endif()
  
  if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/test/test_perception_integrator.py)
    ament_add_pytest_test(
      test_perception_integrator
      ${CMAKE_CURRENT_SOURCE_DIR}/test/test_perception_integrator.py
      TIMEOUT 30
    )
  endif()
  
  # Add linters
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
  ament_lint_auto_python()
  
  # Add copyright and style checks
  ament_copyright()
  ament_pep257()
  ament_xmllint()
endif()

# Export dependencies
ament_export_dependencies(
  rclpy
  sensor_msgs
  std_msgs
  geometry_msgs
  visualization_msgs
  tf2_ros
  tf2_geometry_msgs
  cv_bridge
  image_transport
  vision_msgs
  sensor_msgs_py
)

# Finalize the package
ament_package()
