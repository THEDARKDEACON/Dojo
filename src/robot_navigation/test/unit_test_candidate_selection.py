import sys
import unittest
from unittest.mock import MagicMock

# Mock generated action
mock_action = MagicMock()
sys.modules['robot_navigation.action'] = mock_action
sys.modules['robot_navigation.action.NavigateToObject'] = MagicMock()

# Mock ament_index_python
mock_ament = MagicMock()
mock_ament.get_package_share_directory.return_value = '/tmp'
sys.modules['ament_index_python'] = mock_ament
sys.modules['ament_index_python.packages'] = mock_ament

# Mock ActionServer
sys.modules['rclpy.action'] = MagicMock()

import numpy as np
from nav_msgs.msg import OccupancyGrid
# Now import the node
from robot_navigation.semantic_navigator import SemanticNavigator

import rclpy

class TestCandidateSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        # Mock the node
        self.node = SemanticNavigator()
        self.node.get_logger = MagicMock()
        
        # Mock Costmap
        self.costmap = OccupancyGrid()
        self.costmap.info.resolution = 0.1
        self.costmap.info.width = 100
        self.costmap.info.height = 100
        self.costmap.info.origin.position.x = 0.0
        self.costmap.info.origin.position.y = 0.0
        # Create a flat list of 0s (free space)
        self.costmap.data = [0] * (100 * 100)
        
        self.node.costmap = self.costmap

    def test_generate_candidates(self):
        centroid = {'x': 5.0, 'y': 5.0}
        radius = 0.5
        candidates = self.node.generate_candidates(centroid, radius)
        
        self.assertEqual(len(candidates), 8)
        # Check radius
        for x, y, theta in candidates:
            dist = np.hypot(x - 5.0, y - 5.0)
            self.assertAlmostEqual(dist, 1.5, places=5) # 0.5 + 1.0

    def test_validate_candidates_obstacle(self):
        centroid = {'x': 5.0, 'y': 5.0}
        radius = 0.5
        candidates = self.node.generate_candidates(centroid, radius)
        
        # Place obstacle at one candidate
        # Candidate 0 is at angle 0: x = 6.5, y = 5.0
        # Grid index: 65, 50 -> 50 * 100 + 65 = 5065
        idx = 50 * 100 + 65
        self.costmap.data[idx] = 100 # Lethal obstacle
        
        valid = self.node.validate_candidates(candidates)
        
        # Should have 7 valid candidates
        self.assertEqual(len(valid), 7)

    def test_select_best_candidate(self):
        candidates = [
            (1.0, 1.0, 0.0),
            (10.0, 10.0, 0.0)
        ]
        # Robot at 0,0 (default in code)
        best = self.node.select_best_candidate(candidates)
        
        self.assertEqual(best.pose.position.x, 1.0)
        self.assertEqual(best.pose.position.y, 1.0)

if __name__ == '__main__':
    unittest.main()
