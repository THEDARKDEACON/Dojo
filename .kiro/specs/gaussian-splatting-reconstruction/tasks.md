# Implementation Plan

- [x] 1. Set up project structure and package configuration
  - Create `src/robot_gaussian_splat` ROS2 package directory structure
  - Write `package.xml` with dependencies (rclpy, sensor_msgs, visualization_msgs, message_filters, cv_bridge)
  - Write `setup.py` with package metadata and entry points
  - Create `__init__.py` files for Python package structure
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Implement data models and core data structures
  - [x] 2.1 Create GaussianPrimitive dataclass
    - Define position, covariance, color, opacity, and timestamp attributes
    - Implement `to_dict()` and `from_dict()` serialization methods
    - Implement `to_ply_vertex()` for PLY export format
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [x] 2.2 Create SplatModel class
    - Implement primitive storage with list structure
    - Create octree spatial indexing for efficient queries
    - Implement metadata tracking (creation time, frame count, bounds)
    - Add `add_primitive()`, `get_bounds()`, and `query_region()` methods
    - _Requirements: 3.1, 3.2, 3.5_

- [ ] 3. Implement SplatGenerator component
  - [x] 3.1 Create SplatGenerator class initialization
    - Accept camera_info parameter for intrinsics
    - Initialize KDTree for neighbor searches
    - Set up configuration parameters (neighbor count, radius)
    - _Requirements: 2.1, 2.2_
  
  - [x] 3.2 Implement color projection from camera to 3D points
    - Write `project_color()` method using camera intrinsics
    - Handle points outside camera FOV
    - Validate image bounds and handle edge cases
    - _Requirements: 2.2_
  
  - [x] 3.3 Implement covariance computation from local geometry
    - Write `find_neighbors()` using KDTree spatial search
    - Implement `compute_covariance()` using PCA on neighbors
    - Handle cases with insufficient neighbors (use default covariance)
    - _Requirements: 2.3_
  
  - [x] 3.4 Implement opacity calculation based on point density
    - Write `compute_opacity()` using local point density
    - Normalize opacity values to [0.0, 1.0] range
    - _Requirements: 2.4_
  
  - [x] 3.5 Implement main splat generation pipeline
    - Write `generate_splats()` method coordinating all steps
    - Filter invalid points (NaN, Inf) from point cloud
    - Process each valid 3D point into a GaussianPrimitive
    - Return list of generated primitives
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 6.2_

- [x] 4. Implement ReconstructionManager component
  - [x] 4.1 Create ReconstructionManager class
    - Initialize with max_primitives parameter
    - Create SplatModel instance for storage
    - Set up thread locks for concurrent access
    - _Requirements: 3.1, 3.2, 3.5_
  
  - [x] 4.2 Implement primitive accumulation
    - Write `add_primitives()` method to add new primitives to model
    - Update octree spatial index when adding primitives
    - Track total primitive count
    - _Requirements: 3.1, 3.2_
  
  - [x] 4.3 Implement downsampling mechanism
    - Write `downsample()` method using voxel grid filtering
    - Trigger automatically when primitive count exceeds max_primitives
    - Use adaptive voxel size based on scene bounds
    - Log downsampling operations
    - _Requirements: 3.5_
  
  - [x] 4.4 Implement PLY export functionality
    - Write `export_ply()` method using plyfile library
    - Include position, color, covariance, and opacity in PLY format
    - Handle file I/O errors gracefully
    - _Requirements: 5.1, 5.3_
  
  - [x] 4.5 Implement JSON export functionality
    - Write `export_json()` method with complete primitive parameters
    - Serialize numpy arrays to lists for JSON compatibility
    - Include metadata in export
    - _Requirements: 5.2_
  
  - [x] 4.6 Implement utility methods
    - Write `get_primitive_count()` to return current count
    - Write `get_primitives_for_visualization()` to return limited subset
    - Write `clear()` to reset model
    - Write `get_statistics()` to return model stats
    - _Requirements: 3.3, 3.4, 4.2_

- [x] 5. Implement SensorSynchronizer component
  - [x] 5.1 Create SensorSynchronizer class
    - Initialize with ROS2 node and sync_tolerance parameter
    - Set up message_filters.ApproximateTimeSynchronizer
    - Configure queue size and slop (tolerance) parameters
    - _Requirements: 1.3, 1.4_
  
  - [x] 5.2 Implement data validation
    - Write `validate_data()` method to check image and pointcloud validity
    - Validate image encoding (RGB8, BGR8)
    - Check for NaN/Inf values in point clouds
    - Filter corrupted or invalid data
    - _Requirements: 6.1, 6.2_
  
  - [x] 5.3 Set up synchronized callback registration
    - Write `setup_subscribers()` to create image and pointcloud subscribers
    - Register synchronized callback with ApproximateTimeSynchronizer
    - Handle subscription errors
    - _Requirements: 1.1, 1.2, 1.3_

- [x] 6. Implement VisualizationPublisher component
  - [x] 6.1 Create VisualizationPublisher class
    - Initialize with node, rate, and limit parameters
    - Create publisher for visualization_msgs/MarkerArray
    - Set up timer for periodic publishing
    - _Requirements: 4.1, 4.4_
  
  - [x] 6.2 Implement marker creation from primitives
    - Write `create_marker()` to convert GaussianPrimitive to Marker
    - Use SPHERE markers with color and scale from primitive
    - Set marker lifetime and frame_id
    - _Requirements: 4.1_
  
  - [x] 6.3 Implement visualization publishing
    - Write `publish_markers()` to publish MarkerArray
    - Limit to max visualization_limit primitives
    - Sample primitives uniformly if count exceeds limit
    - _Requirements: 4.1, 4.3_
  
  - [x] 6.4 Implement diagnostics publishing
    - Write `publish_diagnostics()` to publish system status
    - Include primitive count, memory usage, sync rate
    - Publish diagnostic warnings when appropriate
    - _Requirements: 4.2, 4.5, 6.5_

- [x] 7. Implement main GaussianSplattingNode
  - [x] 7.1 Create node initialization
    - Initialize ROS2 node with parameters
    - Declare all configurable parameters
    - Create instances of all components (SensorSynchronizer, SplatGenerator, etc.)
    - Set up publishers for diagnostics and progress
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [x] 7.2 Implement synchronized callback
    - Write `synchronized_callback()` to process camera and LiDAR data
    - Extract camera_info for SplatGenerator
    - Call SplatGenerator to create primitives
    - Add primitives to ReconstructionManager
    - Update frame counter and publish progress
    - Handle processing errors gracefully
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 6.1, 6.4_
  
  - [x] 7.3 Implement save model service
    - Create ROS2 service for SaveSplatModel
    - Write `save_model_service()` callback
    - Call ReconstructionManager export methods (PLY or JSON)
    - Return success status and file location
    - _Requirements: 3.3, 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [x] 7.4 Implement clear model service
    - Create ROS2 service using std_srvs/Trigger
    - Write `clear_model_service()` callback
    - Call ReconstructionManager clear method
    - _Requirements: 3.4_
  
  - [x] 7.5 Implement get statistics service
    - Create ROS2 service for GetSplatStats
    - Write `get_stats_service()` callback
    - Query ReconstructionManager for statistics
    - Return primitive count, memory usage, bounds, frame count
    - _Requirements: 4.2_
  
  - [x] 7.6 Implement visualization timer callback
    - Write `publish_visualization()` method
    - Query primitives from ReconstructionManager
    - Call VisualizationPublisher to publish markers
    - Respect visualization_enabled parameter
    - _Requirements: 4.1, 4.3, 4.4_

- [x] 8. Create custom service definitions
  - [x] 8.1 Create SaveSplatModel.srv
    - Define request fields (filepath, format)
    - Define response fields (success, message, primitive_count)
    - Add to CMakeLists.txt for service generation
    - _Requirements: 5.4_
  
  - [x] 8.2 Create GetSplatStats.srv
    - Define response fields (primitive_count, memory_usage_mb, bounds, frames_processed)
    - Add to CMakeLists.txt for service generation
    - _Requirements: 4.2_

- [x] 9. Create configuration files
  - [x] 9.1 Create gaussian_splatting_params.yaml
    - Define all node parameters with default values
    - Include sync_tolerance, visualization settings, topic names
    - Document each parameter with comments
    - _Requirements: 1.3, 1.5, 3.5, 4.1, 4.4_
  
  - [x] 9.2 Create RViz configuration file
    - Set up MarkerArray display for Gaussian primitives
    - Configure camera and point cloud displays
    - Set appropriate visualization settings
    - _Requirements: 4.1_

- [x] 10. Create launch file
  - [x] 10.1 Create gaussian_splatting.launch.py
    - Launch GaussianSplattingNode with parameters from config file
    - Set up topic remappings for camera and LiDAR
    - Optionally launch RViz with visualization config
    - Add launch arguments for configuration flexibility
    - _Requirements: 1.1, 1.2, 1.5_

- [x] 11. Create documentation
  - [x] 11.1 Create package README.md
    - Document installation instructions
    - Explain usage and launch procedures
    - List dependencies and system requirements
    - Provide examples of service calls
    - Include troubleshooting section
    - _Requirements: All_
  
  - [x] 11.2 Create user guide documentation
    - Write docs/GAUSSIAN_SPLATTING_GUIDE.md
    - Explain Gaussian Splatting concepts
    - Document export formats and visualization
    - Provide performance tuning tips
    - _Requirements: All_

- [x] 12. Integration with existing robot system
  - [x] 12.1 Update main robot launch files
    - Add Gaussian Splatting launch to cutting_edge_features.launch.py
    - Configure topic remappings to match existing camera/LiDAR topics
    - _Requirements: 1.1, 1.2_
  
  - [x] 12.2 Update start_cutting_edge_robot.py
    - Add Gaussian Splatting node to startup sequence
    - Include in system health checks
    - _Requirements: All_
  
  - [x] 12.3 Create Python launcher alternative to bash script
    - Replace launch_robot.sh with Python-based launcher
    - Use subprocess or ROS2 launch API
    - Provide same functionality without bash dependency
    - _Requirements: All (addresses bash script removal request)_
