cmake_minimum_required(VERSION 3.8)
project(robot_control)

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

# Install Python package using setup.py
ament_python_install_package(${PROJECT_NAME})

# Install Python executables
install(PROGRAMS
  robot_control/configuration_manager.py
  robot_control/control_manager.py
  robot_control/hardware_discovery.py
  robot_control/safety_supervisor.py
  robot_control/hardware_manager.py
  robot_control/arduino_bridge.py
  robot_control/camera_driver.py
  robot_control/lidar_driver.py
  robot_control/diagnostic_system.py
  robot_control/graceful_degradation.py
  robot_control/emergency_stop_handler.py
  robot_control/velocity_limiter.py
  robot_control/watchdog_system.py
  robot_control/test_enhanced_camera_driver.py
  DESTINATION lib/${PROJECT_NAME}
)

# Install launch files
install(
  DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
  PATTERN "*.launch.py"
  PATTERN "*.launch"
)

# Install config files
install(
  DIRECTORY config/
  DESTINATION share/${PROJECT_NAME}/config
  PATTERN "*.yaml"
  PATTERN "*.yml"
)

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
  # ament_enable_testing() # Commented out - not available in this ROS 2 installation
endif()

# Register the package with ament
ament_package()
