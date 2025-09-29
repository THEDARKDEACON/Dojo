"""
Common utilities for the robot_perception package.
"""
import numpy as np
import rclpy
from geometry_msgs.msg import Point, Quaternion, Vector3, Pose, PoseStamped
from std_msgs.msg import ColorRGBA, Header
from visualization_msgs.msg import Marker, MarkerArray
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2


def create_marker(header, ns, marker_id, marker_type, position, orientation=None,
                 scale=None, color=None, frame_locked=False, lifetime=None):
    """Create a visualization marker.
    
    Args:
        header: Header with frame_id and timestamp
        ns: Namespace for the marker
        marker_id: Unique ID for the marker
        marker_type: Type of marker (e.g., Marker.CUBE, Marker.SPHERE)
        position: Position as [x, y, z]
        orientation: Orientation as [x, y, z, w] (quaternion)
        scale: Scale as [x, y, z]
        color: Color as [r, g, b, a] (0-1.0)
        frame_locked: If True, marker will be fixed to the reference frame
        lifetime: Lifetime in seconds (None for infinite)
        
    Returns:
        visualization_msgs.msg.Marker
    """
    marker = Marker()
    marker.header = header
    marker.ns = ns
    marker.id = marker_id
    marker.type = marker_type
    
    marker.pose.position = Point(x=float(position[0]), 
                               y=float(position[1]), 
                               z=float(position[2]))
    
    if orientation is not None:
        marker.pose.orientation = Quaternion(x=float(orientation[0]),
                                           y=float(orientation[1]),
                                           z=float(orientation[2]),
                                           w=float(orientation[3]))
    else:
        marker.pose.orientation.w = 1.0
    
    if scale is not None:
        marker.scale = Vector3(x=float(scale[0]), 
                             y=float(scale[1]), 
                             z=float(scale[2]))
    
    if color is not None:
        marker.color = ColorRGBA(r=float(color[0]),
                               g=float(color[1]),
                               b=float(color[2]),
                               a=float(color[3]) if len(color) > 3 else 1.0)
    else:
        marker.color = ColorRGBA(r=1.0, g=0.0, b=0.0, a=1.0)
    
    if lifetime is not None:
        marker.lifetime = rclpy.duration.Duration(seconds=lifetime).to_msg()
    
    marker.frame_locked = frame_locked
    
    return marker


def create_point_cloud(points, frame_id, stamp=None, fields=None):
    """Create a PointCloud2 message from a numpy array of points.
    
    Args:
        points: Nx3 or Nx4 numpy array of points (x,y,z) or (x,y,z,intensity)
        frame_id: Frame ID for the point cloud
        stamp: Timestamp for the point cloud
        fields: List of PointField objects (default: x,y,z)
        
    Returns:
        sensor_msgs.msg.PointCloud2
    """
    if fields is None:
        if points.shape[1] == 3:
            fields = [
                PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
                PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
                PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1)
            ]
        else:
            fields = [
                PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
                PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
                PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
                PointField(name='intensity', offset=12, datatype=PointField.FLOAT32, count=1)
            ]
    
    header = Header()
    header.frame_id = frame_id
    if stamp is not None:
        header.stamp = stamp
    else:
        header.stamp = rclpy.time.Time().to_msg()
    
    return point_cloud2.create_cloud(header, fields, points)


def transform_pose(transform, pose_stamped):
    """Transform a pose using a transform from tf2_ros.
    
    Args:
        transform: The transform from tf2_ros.Buffer.lookup_transform()
        pose_stamped: The pose to transform (PoseStamped)
        
    Returns:
        geometry_msgs.msg.PoseStamped: The transformed pose
    """
    from geometry_msgs.msg import PoseStamped
    
    # Create a new PoseStamped with the same header as the input
    transformed_pose = PoseStamped()
    transformed_pose.header = pose_stamped.header
    
    # Transform the pose
    transformed_pose.pose.position.x = transform.transform.translation.x
    transformed_pose.pose.position.y = transform.transform.translation.y
    transformed_pose.pose.position.z = transform.transform.translation.z
    transformed_pose.pose.orientation = transform.transform.rotation
    
    return transformed_pose
