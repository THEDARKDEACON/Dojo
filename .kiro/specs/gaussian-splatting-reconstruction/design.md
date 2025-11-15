# Design Document: Gaussian Splatting Reconstruction

## Overview

This design implements a ROS2-based Gaussian Splatting reconstruction system that generates photorealistic 3D scene representations from synchronized camera and LiDAR data. The system integrates with the existing robot architecture to provide real-time 3D reconstruction capabilities during autonomous mapping operations.

The implementation uses a message-filter-based synchronization approach to align sensor data, processes the data into Gaussian primitives with position, color, covariance, and opacity attributes, and maintains an accumulated reconstruction model that can be exported in standard formats.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                  GaussianSplattingNode                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Sensor Synchronization Layer                │  │
│  │  - ApproximateTimeSynchronizer (camera + lidar)      │  │
│  │  - Temporal alignment (50ms tolerance)                │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Data Processing Layer                    │  │
│  │  - SplatGenerator: Creates Gaussian primitives        │  │
│  │  - Covariance computation from local geometry         │  │
│  │  - Color extraction and projection                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Reconstruction Management Layer             │  │
│  │  - ReconstructionManager: Accumulates primitives      │  │
│  │  - Spatial indexing (octree-based)                    │  │
│  │  - Downsampling for memory management                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Output & Visualization Layer             │  │
│  │  - Export services (PLY, JSON)                        │  │
│  │  - RViz visualization markers                         │  │
│  │  - Diagnostic publishers                              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Integration Points

- **Input Topics:**
  - `/camera/image_raw` (sensor_msgs/Image) - RGB camera feed
  - `/camera/camera_info` (sensor_msgs/CameraInfo) - Camera calibration
  - `/scan` or `/velodyne_points` (sensor_msgs/PointCloud2) - LiDAR data

- **Output Topics:**
  - `/gaussian_splat/visualization` (visualization_msgs/MarkerArray) - RViz markers
  - `/gaussian_splat/diagnostics` (diagnostic_msgs/DiagnosticArray) - System status
  - `/gaussian_splat/progress` (std_msgs/Float32) - Reconstruction progress

- **Services:**
  - `/gaussian_splat/save_model` (SaveSplatModel.srv) - Export reconstruction
  - `/gaussian_splat/clear_model` (std_srvs/Trigger) - Reset reconstruction
  - `/gaussian_splat/get_stats` (GetSplatStats.srv) - Query model statistics

## Components and Interfaces

### 1. GaussianSplattingNode (Main ROS2 Node)

**Responsibilities:**
- Initialize and manage all subsystems
- Handle ROS2 communication (subscribers, publishers, services)
- Coordinate data flow between components
- Manage node lifecycle and parameters

**Key Methods:**
```python
class GaussianSplattingNode(Node):
    def __init__(self)
    def synchronized_callback(self, image_msg, pointcloud_msg)
    def publish_visualization(self)
    def save_model_service(self, request, response)
    def clear_model_service(self, request, response)
    def get_stats_service(self, request, response)
```

**Parameters:**
- `sync_tolerance` (float, default: 0.05) - Time sync tolerance in seconds
- `visualization_enabled` (bool, default: true) - Enable real-time visualization
- `visualization_rate` (float, default: 1.0) - Visualization publish rate in Hz
- `max_primitives` (int, default: 1000000) - Maximum primitives before downsampling
- `visualization_limit` (int, default: 10000) - Max primitives to visualize
- `camera_topic` (string) - Camera image topic name
- `camera_info_topic` (string) - Camera info topic name
- `pointcloud_topic` (string) - LiDAR pointcloud topic name

### 2. SensorSynchronizer

**Responsibilities:**
- Synchronize camera and LiDAR data streams
- Validate data quality and timestamps
- Filter out invalid or misaligned data

**Key Methods:**
```python
class SensorSynchronizer:
    def __init__(self, node, sync_tolerance)
    def setup_subscribers(self, camera_topic, pointcloud_topic)
    def register_callback(self, callback_function)
    def validate_data(self, image_msg, pointcloud_msg) -> bool
```

**Implementation Details:**
- Uses `message_filters.ApproximateTimeSynchronizer` for temporal alignment
- Validates image encoding (RGB8, BGR8)
- Checks for NaN/Inf values in point clouds
- Logs synchronization statistics

### 3. SplatGenerator

**Responsibilities:**
- Generate Gaussian primitives from synchronized sensor data
- Compute covariance matrices from local point cloud geometry
- Project colors from camera images to 3D points
- Assign opacity based on point density

**Key Methods:**
```python
class SplatGenerator:
    def __init__(self, camera_info)
    def generate_splats(self, image, pointcloud) -> List[GaussianPrimitive]
    def compute_covariance(self, point, neighbors) -> np.ndarray
    def project_color(self, point_3d, image) -> Tuple[int, int, int]
    def compute_opacity(self, point, local_density) -> float
    def find_neighbors(self, point, pointcloud, radius) -> List[Point]
```

**Implementation Details:**
- Uses camera intrinsics for 3D-to-2D projection
- Computes covariance from k-nearest neighbors (k=10)
- Applies PCA to determine principal axes
- Opacity based on local point density (normalized)
- Filters points outside camera FOV

### 4. ReconstructionManager

**Responsibilities:**
- Maintain persistent collection of Gaussian primitives
- Implement spatial indexing for efficient queries
- Apply downsampling when memory limits are reached
- Manage model export operations

**Key Methods:**
```python
class ReconstructionManager:
    def __init__(self, max_primitives)
    def add_primitives(self, primitives: List[GaussianPrimitive])
    def get_primitive_count(self) -> int
    def get_primitives_for_visualization(self, limit: int) -> List[GaussianPrimitive]
    def downsample(self)
    def export_ply(self, filepath: str) -> bool
    def export_json(self, filepath: str) -> bool
    def clear(self)
    def get_statistics(self) -> Dict
```

**Implementation Details:**
- Uses octree spatial indexing for efficient spatial queries
- Downsampling via voxel grid filtering (adaptive voxel size)
- PLY export includes custom properties for Gaussian attributes
- JSON export for full parameter preservation
- Thread-safe operations for concurrent access

### 5. VisualizationPublisher

**Responsibilities:**
- Convert Gaussian primitives to RViz markers
- Manage visualization update rate
- Limit visualization data for performance

**Key Methods:**
```python
class VisualizationPublisher:
    def __init__(self, node, rate, limit)
    def publish_markers(self, primitives: List[GaussianPrimitive])
    def create_marker(self, primitive: GaussianPrimitive) -> Marker
    def publish_diagnostics(self, stats: Dict)
```

**Implementation Details:**
- Represents Gaussians as ellipsoid markers (SPHERE_LIST)
- Color encoding from primitive RGB values
- Scale based on covariance eigenvalues
- Publishes at configurable rate to avoid overwhelming RViz

## Data Models

### GaussianPrimitive

```python
@dataclass
class GaussianPrimitive:
    """Represents a single 3D Gaussian primitive"""
    position: np.ndarray  # [x, y, z] in meters
    covariance: np.ndarray  # 3x3 covariance matrix
    color: Tuple[int, int, int]  # RGB values [0-255]
    opacity: float  # [0.0-1.0]
    timestamp: float  # ROS time when created
    
    def to_dict(self) -> Dict
    def from_dict(cls, data: Dict) -> 'GaussianPrimitive'
    def to_ply_vertex(self) -> bytes
```

### SplatModel

```python
class SplatModel:
    """Container for the complete Gaussian Splat reconstruction"""
    def __init__(self):
        self.primitives: List[GaussianPrimitive] = []
        self.octree: Octree = Octree(max_depth=10)
        self.metadata: Dict = {
            'creation_time': None,
            'total_frames_processed': 0,
            'bounds': None
        }
    
    def add_primitive(self, primitive: GaussianPrimitive)
    def get_bounds(self) -> Tuple[np.ndarray, np.ndarray]
    def query_region(self, min_point, max_point) -> List[GaussianPrimitive]
```

### Custom Service Definitions

**SaveSplatModel.srv:**
```
string filepath
string format  # "ply" or "json"
---
bool success
string message
int64 primitive_count
```

**GetSplatStats.srv:**
```
---
int64 primitive_count
float64 memory_usage_mb
float64[] bounds_min
float64[] bounds_max
int64 frames_processed
```

## Error Handling

### Data Validation Errors
- **Invalid Image Data:** Log warning, skip frame, continue processing
- **Corrupted Point Cloud:** Filter invalid points (NaN/Inf), process remaining
- **Synchronization Failure:** Log diagnostic, track sync success rate
- **Empty Data:** Skip processing, publish diagnostic message

### Processing Errors
- **Projection Failures:** Skip points outside camera FOV
- **Covariance Computation Errors:** Use default covariance (identity matrix scaled)
- **Memory Limits:** Trigger automatic downsampling, log warning
- **Export Failures:** Return error status, preserve existing model

### Recovery Strategies
- Graceful degradation: Continue with partial data
- Automatic downsampling when approaching memory limits
- Diagnostic publishing for monitoring system health
- Service call error responses with descriptive messages

## Testing Strategy

### Unit Tests

1. **SplatGenerator Tests:**
   - Color projection accuracy with known camera parameters
   - Covariance computation with synthetic point clouds
   - Opacity calculation with varying densities
   - Edge cases: empty clouds, single points

2. **ReconstructionManager Tests:**
   - Primitive addition and retrieval
   - Downsampling correctness
   - Export format validation (PLY/JSON)
   - Spatial query accuracy

3. **SensorSynchronizer Tests:**
   - Timestamp alignment within tolerance
   - Data validation logic
   - Handling of misaligned data

### Integration Tests

1. **End-to-End Pipeline:**
   - Process synthetic camera + LiDAR data
   - Verify primitive generation
   - Validate export formats
   - Check visualization output

2. **ROS2 Integration:**
   - Topic subscription and publishing
   - Service call handling
   - Parameter loading and updates
   - Node lifecycle management

### Performance Tests

1. **Throughput:**
   - Process 10 Hz camera + LiDAR streams
   - Measure latency from input to primitive generation
   - Monitor memory usage over time

2. **Scalability:**
   - Test with 100K, 500K, 1M primitives
   - Verify downsampling triggers correctly
   - Measure visualization performance

## Performance Considerations

### Memory Management
- Octree spatial indexing reduces memory overhead
- Automatic downsampling at configurable thresholds
- Visualization limited to subset of primitives
- Efficient numpy array operations

### Computational Efficiency
- Vectorized operations for color projection
- KD-tree for neighbor searches
- Lazy evaluation for visualization
- Configurable processing rates

### Real-time Constraints
- Asynchronous processing pipeline
- Non-blocking service calls
- Separate threads for visualization
- Buffered message queues

## Dependencies

### ROS2 Packages
- `rclpy` - ROS2 Python client library
- `sensor_msgs` - Image and PointCloud2 messages
- `visualization_msgs` - Marker messages for RViz
- `diagnostic_msgs` - System diagnostics
- `message_filters` - Time synchronization
- `tf2_ros` - Transform handling

### Python Libraries
- `numpy` - Numerical operations
- `opencv-python` (cv2) - Image processing
- `scipy` - Spatial operations (KDTree)
- `open3d` - Point cloud processing utilities
- `plyfile` - PLY format export

### System Requirements
- ROS2 Humble or later
- Python 3.10+
- 8GB+ RAM recommended for large reconstructions
- GPU optional (CPU-based implementation)

## Configuration

### Launch File Structure
```python
# gaussian_splatting.launch.py
- GaussianSplattingNode
  - Parameters from config file
  - Remappings for topic names
- RViz (optional)
  - Load visualization config
```

### Configuration File
```yaml
# gaussian_splatting_params.yaml
gaussian_splatting:
  ros__parameters:
    sync_tolerance: 0.05
    visualization_enabled: true
    visualization_rate: 1.0
    max_primitives: 1000000
    visualization_limit: 10000
    camera_topic: "/camera/image_raw"
    camera_info_topic: "/camera/camera_info"
    pointcloud_topic: "/scan"
    output_directory: "~/gaussian_splats"
```

## Future Enhancements

- GPU acceleration using CUDA for primitive generation
- Neural network-based covariance estimation
- Real-time rendering using Gaussian Splatting viewer
- Multi-robot collaborative reconstruction
- Incremental model optimization
- Compression for efficient storage
