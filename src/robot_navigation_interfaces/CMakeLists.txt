cmake_minimum_required(VERSION 3.8)
project(robot_navigation_interfaces)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(geometry_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "action/NavigateToObject.action"
  DEPENDENCIES geometry_msgs
)

ament_export_dependencies(rosidl_default_runtime geometry_msgs)

ament_package()
