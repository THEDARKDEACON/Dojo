cmake_minimum_required(VERSION 3.8)
project(robot_description)

# Default to C++17
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
  set(CMAKE_CXX_EXTENSIONS OFF)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

# Find ROS 2 packages
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(urdf REQUIRED)
find_package(xacro REQUIRED)
find_package(gazebo_ros2_control REQUIRED)
find_package(gazebo_ros REQUIRED)
find_package(controller_manager REQUIRED)
find_package(hardware_interface REQUIRED)
find_package(pluginlib REQUIRED)

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

# Install model and resource files
install(
  DIRECTORY 
    urdf/
    rviz/
  DESTINATION share/${PROJECT_NAME}
  PATTERN "*"
)

# Install Python package
install(DIRECTORY
  robot_description/
  DESTINATION lib/python3.10/site-packages
)

# Install Python scripts
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/scripts")
  install(PROGRAMS
    scripts/display_robot.py
    DESTINATION lib/${PROJECT_NAME}
  )
endif()

# Install package.xml and setup files
install(FILES
  package.xml
  setup.py
  setup.cfg
  DESTINATION share/${PROJECT_NAME}
)

# Register the package with ament
ament_package()
