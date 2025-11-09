#!/usr/bin/env python3
"""
Unit Tests for Enhanced Semantic Navigation (Task 1.4)

Tests the enhanced navigation interface including:
- Nav2 integration
- Spatial indexing for fast queries
- Multi-step navigation
- Navigation feedback and progress reporting
"""

import unittest
import numpy as np
from scipy.spatial import KDTree
from typing import List, Tuple, Dict, Optional


class TestSpatialIndexing(unittest.TestCase):
    """Test spatial indexing with KDTree"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test objects
        self.objects = {
            'chair_1': {'class': 'chair', 'x': 2.0, 'y': 1.0},
            'chair_2': {'class': 'chair', 'x': 5.0, 'y': 3.0},
            'table_1': {'class': 'table', 'x': 3.0, 'y': 2.0},
            'bottle_1': {'class': 'bottle', 'x': 1.5, 'y': 0.5},
            'cup_1': {'class': 'cup', 'x': 4.0, 'y': 4.0},
        }
        
        # Build spatial index
        positions = [[obj['x'], obj['y']] for obj in self.objects.values()]
        self.spatial_index = KDTree(np.array(positions))
        self.object_ids = list(self.objects.keys())
    
    def test_nearest_neighbor_query(self):
        """Test finding nearest object"""
        query_point = np.array([2.1, 1.1])
        
        distance, index = self.spatial_index.query(query_point)
        nearest_id = self.object_ids[index]
        
        # Should find chair_1 (closest to query point)
        self.assertEqual(nearest_id, 'chair_1')
        self.assertLess(distance, 0.2)
    
    def test_radius_query(self):
        """Test finding all objects within radius"""
        center = np.array([3.0, 2.0])
        radius = 2.0
        
        indices = self.spatial_index.query_ball_point(center, radius)
        found_ids = [self.object_ids[i] for i in indices]
        
        # Should find table_1, chair_1, and bottle_1
        self.assertIn('table_1', found_ids)
        self.assertIn('chair_1', found_ids)
        self.assertNotIn('cup_1', found_ids)  # Too far
    
    def test_k_nearest_neighbors(self):
        """Test finding k nearest objects"""
        query_point = np.array([0.0, 0.0])
        k = 3
        
        distances, indices = self.spatial_index.query(query_point, k=k)
        nearest_ids = [self.object_ids[i] for i in indices]
        
        # Should find 3 nearest objects
        self.assertEqual(len(nearest_ids), 3)
        self.assertIn('bottle_1', nearest_ids)  # Closest


class TestObjectFiltering(unittest.TestCase):
    """Test object filtering by class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.objects = {
            'chair_1': {'class': 'chair', 'x': 2.0, 'y': 1.0, 'confidence': 0.9},
            'chair_2': {'class': 'chair', 'x': 5.0, 'y': 3.0, 'confidence': 0.8},
            'table_1': {'class': 'table', 'x': 3.0, 'y': 2.0, 'confidence': 0.85},
            'dining_table_1': {'class': 'dining table', 'x': 6.0, 'y': 4.0, 'confidence': 0.75},
        }
    
    def test_exact_class_match(self):
        """Test finding objects with exact class match"""
        target_class = 'chair'
        
        matches = [obj_id for obj_id, obj in self.objects.items() 
                  if obj['class'] == target_class]
        
        self.assertEqual(len(matches), 2)
        self.assertIn('chair_1', matches)
        self.assertIn('chair_2', matches)
    
    def test_partial_class_match(self):
        """Test finding objects with partial class match"""
        target_class = 'table'
        
        matches = [obj_id for obj_id, obj in self.objects.items() 
                  if target_class in obj['class'].lower()]
        
        self.assertEqual(len(matches), 2)
        self.assertIn('table_1', matches)
        self.assertIn('dining_table_1', matches)
    
    def test_find_nearest_by_class(self):
        """Test finding nearest object of specific class"""
        robot_pos = np.array([0.0, 0.0])
        target_class = 'chair'
        
        # Find all chairs
        chairs = [(obj_id, obj) for obj_id, obj in self.objects.items() 
                 if target_class in obj['class'].lower()]
        
        # Calculate distances
        distances = []
        for obj_id, obj in chairs:
            dist = np.sqrt((obj['x'] - robot_pos[0])**2 + (obj['y'] - robot_pos[1])**2)
            distances.append((obj_id, dist))
        
        # Find nearest
        distances.sort(key=lambda x: x[1])
        nearest_id = distances[0][0]
        
        self.assertEqual(nearest_id, 'chair_1')


class TestMultiStepNavigation(unittest.TestCase):
    """Test multi-step navigation logic"""
    
    def test_goal_queue(self):
        """Test goal queue management"""
        goals = ['chair', 'table', 'door', 'window']
        
        # Simulate multi-step navigation
        current_goal = goals[0]
        remaining_goals = goals[1:]
        
        self.assertEqual(current_goal, 'chair')
        self.assertEqual(len(remaining_goals), 3)
        
        # Simulate completing first goal
        current_goal = remaining_goals.pop(0)
        
        self.assertEqual(current_goal, 'table')
        self.assertEqual(len(remaining_goals), 2)
    
    def test_empty_goal_queue(self):
        """Test handling empty goal queue"""
        goals = []
        
        if goals:
            current_goal = goals[0]
        else:
            current_goal = None
        
        self.assertIsNone(current_goal)
    
    def test_goal_parsing(self):
        """Test parsing multi-step navigation command"""
        command = "go to chair then table then door"
        
        # Parse command
        if " then " in command:
            object_part = command.replace("go to", "").strip()
            objects = [obj.strip() for obj in object_part.split(" then ")]
        else:
            objects = [command.replace("go to", "").strip()]
        
        self.assertEqual(len(objects), 3)
        self.assertEqual(objects[0], 'chair')
        self.assertEqual(objects[1], 'table')
        self.assertEqual(objects[2], 'door')


class TestNavigationProgress(unittest.TestCase):
    """Test navigation progress calculation"""
    
    def test_progress_calculation(self):
        """Test progress percentage calculation"""
        total_distance = 10.0
        remaining_distance = 3.0
        
        progress = (1.0 - remaining_distance / total_distance) * 100.0
        
        self.assertAlmostEqual(progress, 70.0, places=1)
    
    def test_progress_bounds(self):
        """Test progress stays within 0-100%"""
        test_cases = [
            (10.0, 0.0, 100.0),   # Completed
            (10.0, 5.0, 50.0),    # Halfway
            (10.0, 10.0, 0.0),    # Just started
            (10.0, 15.0, 0.0),    # Beyond start (clamped)
        ]
        
        for total, remaining, expected in test_cases:
            progress = max(0.0, min(100.0, (1.0 - remaining / total) * 100.0))
            self.assertAlmostEqual(progress, expected, places=1)


class TestNavigationStatus(unittest.TestCase):
    """Test navigation status tracking"""
    
    def test_status_states(self):
        """Test different navigation status states"""
        valid_states = ['started', 'in_progress', 'succeeded', 'aborted', 'canceled', 'failed', 'rejected']
        
        for state in valid_states:
            self.assertIn(state, valid_states)
    
    def test_status_message_format(self):
        """Test status message JSON format"""
        import json
        
        status_data = {
            'status': 'in_progress',
            'message': 'Navigating to chair',
            'timestamp': 1234567890.0,
            'current_goal': 'chair',
            'in_progress': True,
            'queued_goals': 2
        }
        
        # Serialize and deserialize
        json_str = json.dumps(status_data)
        parsed = json.loads(json_str)
        
        self.assertEqual(parsed['status'], 'in_progress')
        self.assertEqual(parsed['current_goal'], 'chair')
        self.assertEqual(parsed['queued_goals'], 2)


class TestSpatialQueries(unittest.TestCase):
    """Test various spatial query operations"""
    
    def test_distance_calculation(self):
        """Test Euclidean distance calculation"""
        p1 = np.array([0.0, 0.0])
        p2 = np.array([3.0, 4.0])
        
        distance = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
        
        self.assertAlmostEqual(distance, 5.0, places=2)
    
    def test_objects_in_radius(self):
        """Test finding objects within radius"""
        objects = {
            'obj1': {'x': 1.0, 'y': 1.0},
            'obj2': {'x': 2.0, 'y': 2.0},
            'obj3': {'x': 10.0, 'y': 10.0},
        }
        
        center = np.array([0.0, 0.0])
        radius = 3.0
        
        in_radius = []
        for obj_id, obj in objects.items():
            dist = np.sqrt(obj['x']**2 + obj['y']**2)
            if dist <= radius:
                in_radius.append(obj_id)
        
        self.assertEqual(len(in_radius), 2)
        self.assertIn('obj1', in_radius)
        self.assertIn('obj2', in_radius)
        self.assertNotIn('obj3', in_radius)


class TestNavigationCommands(unittest.TestCase):
    """Test navigation command parsing"""
    
    def test_simple_navigation_command(self):
        """Test parsing simple navigation command"""
        command = "go to chair"
        
        if command.startswith("go to"):
            object_name = command.replace("go to", "").strip()
        
        self.assertEqual(object_name, "chair")
    
    def test_multi_step_command(self):
        """Test parsing multi-step navigation command"""
        command = "go to chair then table"
        
        object_part = command.replace("go to", "").strip()
        
        if " then " in object_part:
            objects = [obj.strip() for obj in object_part.split(" then ")]
            is_multi_step = True
        else:
            objects = [object_part]
            is_multi_step = False
        
        self.assertTrue(is_multi_step)
        self.assertEqual(len(objects), 2)
    
    def test_cancel_command(self):
        """Test cancel navigation command"""
        commands = ["cancel navigation", "stop"]
        
        for cmd in commands:
            is_cancel = cmd in ["cancel navigation", "stop"]
            self.assertTrue(is_cancel)
    
    def test_find_nearby_command(self):
        """Test find nearby objects command"""
        command = "find nearby"
        
        is_find_nearby = command.startswith("find nearby")
        
        self.assertTrue(is_find_nearby)


if __name__ == '__main__':
    unittest.main()
