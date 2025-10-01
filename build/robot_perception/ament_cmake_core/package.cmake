set(_AMENT_PACKAGE_NAME "robot_perception")
set(robot_perception_VERSION "0.2.0")
set(robot_perception_MAINTAINER "robosync <robosync@example.com>")
set(robot_perception_BUILD_DEPENDS "rclpy" "std_msgs" "builtin_interfaces" "sensor_msgs" "sensor_msgs_py" "vision_msgs" "laser_geometry" "geometry_msgs" "tf2_ros" "tf2_geometry_msgs" "cv_bridge" "image_geometry" "image_transport" "camera_info_manager" "visualization_msgs" "rqt_image_view" "rviz2")
set(robot_perception_BUILDTOOL_DEPENDS "ament_cmake" "ament_cmake_python" "python_cmake_module" "python3-setuptools")
set(robot_perception_BUILD_EXPORT_DEPENDS "rclpy" "sensor_msgs" "sensor_msgs_py" "vision_msgs" "geometry_msgs" "tf2_ros" "tf2_geometry_msgs" "cv_bridge" "image_transport" "visualization_msgs")
set(robot_perception_BUILDTOOL_EXPORT_DEPENDS )
set(robot_perception_EXEC_DEPENDS "rclpy" "std_msgs" "builtin_interfaces" "sensor_msgs" "sensor_msgs_py" "vision_msgs" "laser_geometry" "geometry_msgs" "tf2_ros" "tf2_geometry_msgs" "cv_bridge" "image_geometry" "image_transport" "camera_info_manager" "visualization_msgs" "rqt_image_view" "rviz2" "python3-numpy" "python3-opencv" "python3-yaml" "python3-scipy" "python3-scikit-learn" "python3-torch" "python3-torchvision" "ultralytics" "onnxruntime")
set(robot_perception_TEST_DEPENDS "ament_copyright" "ament_flake8" "ament_pep257" "python3-pytest" "python3-pytest-cov" "python3-pytest-mock")
set(robot_perception_GROUP_DEPENDS )
set(robot_perception_MEMBER_OF_GROUPS )
set(robot_perception_DEPRECATED "")
set(robot_perception_EXPORT_TAGS)
list(APPEND robot_perception_EXPORT_TAGS "<build_type>ament_cmake</build_type>")
list(APPEND robot_perception_EXPORT_TAGS "<build_type>ament_python</build_type>")
list(APPEND robot_perception_EXPORT_TAGS "<python_package><packages>
        <package>robot_perception</package>
        <package>robot_perception.nodes</package>
        <package>robot_perception.utils</package>
      </packages></python_package>")
