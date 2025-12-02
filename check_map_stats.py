import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
import numpy as np
import sys

class MapStats(Node):
    def __init__(self):
        super().__init__('map_stats')
        self.subscription = self.create_subscription(
            OccupancyGrid,
            '/map',
            self.listener_callback,
            10)
        self.subscription  # prevent unused variable warning

    def listener_callback(self, msg):
        data = np.array(msg.data)
        unknown = np.sum(data == -1)
        free = np.sum(data == 0)
        occupied = np.sum(data == 100)
        total = len(data)
        
        self.get_logger().info(f"Map Stats: Size={msg.info.width}x{msg.info.height}")
        self.get_logger().info(f"Unknown: {unknown} ({unknown/total*100:.1f}%)")
        self.get_logger().info(f"Free: {free} ({free/total*100:.1f}%)")
        self.get_logger().info(f"Occupied: {occupied} ({occupied/total*100:.1f}%)")
        
        if free > 0 and unknown > 0:
            self.get_logger().info("✅ Map has frontiers potential (Free + Unknown)")
        else:
            self.get_logger().warn("❌ Map missing Free or Unknown space!")
            
        sys.exit(0)

def main(args=None):
    rclpy.init(args=args)
    map_stats = MapStats()
    rclpy.spin(map_stats)
    map_stats.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
