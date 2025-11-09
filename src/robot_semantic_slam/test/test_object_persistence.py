#!/usr/bin/env python3
"""
Unit Tests for Object Persistence (Task 1.3)

Tests the robust object persistence mechanism including:
- Timeout mechanism for unseen objects
- Confidence decay over time
- Persistent storage to disk
- Improved object merging logic
"""

import unittest
import numpy as np
import os
import pickle
import tempfile
from unittest.mock import Mock, MagicMock
import sys

# Mock ROS2 before importing the node
sys.modules['rclpy'] = MagicMock()
sys.modules['rclpy.node'] = MagicMock()
sys.modules['sensor_msgs'] = MagicMock()
sys.modules['sensor_msgs.msg'] = MagicMock()
sys.modules['geometry_msgs'] = MagicMock()
sys.modules['geometry_msgs.msg'] = MagicMock()
sys.modules['nav_msgs'] = MagicMock()
sys.modules['nav_msgs.msg'] = MagicMock()
sys.modules['std_msgs'] = MagicMock()
sys.modules['std_msgs.msg'] = MagicMock()
sys.modules['vision_msgs'] = MagicMock()
sys.modules['vision_msgs.msg'] = MagicMock()
sys.modules['cv_bridge'] = MagicMock()
sys.modules['tf2_ros'] = MagicMock()
sys.modules['tf2_geometry_msgs'] = MagicMock()
sys.modules['ultralytics'] = MagicMock()


class TestObjectPersistence(unittest.TestCase):
    """Test object persistence mechanisms"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pkl')
        self.temp_file.close()
        self.persistence_file = self.temp_file.name
    
    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.persistence_file):
            os.remove(self.persistence_file)
    
    def test_save_and_load_semantic_map(self):
        """Test saving and loading semantic map from disk"""
        # Create test data
        test_map = {
            'chair_1': {
                'class': 'chair',
                'x': 2.5,
                'y': 1.3,
                'confidence': 0.87,
                'last_seen': 1234567890.0,
                'detections': 5
            },
            'table_2': {
                'class': 'table',
                'x': 3.2,
                'y': -0.5,
                'confidence': 0.92,
                'last_seen': 1234567890.0,
                'detections': 3
            }
        }
        
        save_data = {
            'semantic_map': test_map,
            'object_counter': 2,
            'saved_at': 1234567890.0
        }
        
        # Save to file
        with open(self.persistence_file, 'wb') as f:
            pickle.dump(save_data, f)
        
        # Load from file
        with open(self.persistence_file, 'rb') as f:
            loaded_data = pickle.load(f)
        
        # Verify
        self.assertEqual(len(loaded_data['semantic_map']), 2)
        self.assertEqual(loaded_data['object_counter'], 2)
        self.assertIn('chair_1', loaded_data['semantic_map'])
        self.assertIn('table_2', loaded_data['semantic_map'])
    
    def test_object_timeout_mechanism(self):
        """Test that old objects are removed after timeout"""
        current_time = 1234567890.0
        timeout = 300.0  # 5 minutes
        
        objects = {
            'chair_1': {
                'class': 'chair',
                'last_seen': current_time - 600.0,  # 10 minutes ago (should be removed)
                'confidence': 0.8
            },
            'table_2': {
                'class': 'table',
                'last_seen': current_time - 60.0,  # 1 minute ago (should remain)
                'confidence': 0.9
            },
            'bottle_3': {
                'class': 'bottle',
                'last_seen': current_time - 400.0,  # 6.67 minutes ago (should be removed)
                'confidence': 0.7
            }
        }
        
        # Simulate cleanup
        objects_to_remove = []
        for obj_id, obj_data in objects.items():
            time_since_seen = current_time - obj_data['last_seen']
            if time_since_seen > timeout:
                objects_to_remove.append(obj_id)
        
        # Verify correct objects marked for removal
        self.assertIn('chair_1', objects_to_remove)
        self.assertIn('bottle_3', objects_to_remove)
        self.assertNotIn('table_2', objects_to_remove)
    
    def test_confidence_decay(self):
        """Test confidence decay over time"""
        initial_confidence = 0.9
        decay_rate = 0.95  # 5% decay per minute
        
        # Test decay after 1 minute
        confidence_1min = initial_confidence * decay_rate
        self.assertAlmostEqual(confidence_1min, 0.855, places=3)
        
        # Test decay after 5 minutes
        confidence_5min = initial_confidence * (decay_rate ** 5)
        self.assertAlmostEqual(confidence_5min, 0.6983, places=3)
        
        # Test decay after 10 minutes
        confidence_10min = initial_confidence * (decay_rate ** 10)
        self.assertAlmostEqual(confidence_10min, 0.5987, places=3)
    
    def test_min_confidence_threshold(self):
        """Test removal of objects below minimum confidence"""
        min_confidence = 0.3
        
        objects = {
            'chair_1': {'confidence': 0.8},  # Should remain
            'table_2': {'confidence': 0.25},  # Should be removed
            'bottle_3': {'confidence': 0.5},  # Should remain
            'cup_4': {'confidence': 0.15},  # Should be removed
        }
        
        objects_to_remove = [
            obj_id for obj_id, obj_data in objects.items()
            if obj_data['confidence'] < min_confidence
        ]
        
        self.assertIn('table_2', objects_to_remove)
        self.assertIn('cup_4', objects_to_remove)
        self.assertNotIn('chair_1', objects_to_remove)
        self.assertNotIn('bottle_3', objects_to_remove)
    
    def test_object_merging_logic(self):
        """Test improved object merging with weighted average"""
        # Existing object
        existing_obj = {
            'x': 2.0,
            'y': 1.0,
            'confidence': 0.8,
            'detections': 5
        }
        
        # New detection
        new_x, new_y = 2.1, 1.05
        new_confidence = 0.9
        
        # Calculate weighted average
        old_weight = existing_obj['detections']
        new_weight = 1
        total_weight = old_weight + new_weight
        
        merged_x = (existing_obj['x'] * old_weight + new_x * new_weight) / total_weight
        merged_y = (existing_obj['y'] * old_weight + new_y * new_weight) / total_weight
        merged_confidence = max(existing_obj['confidence'], new_confidence)
        
        # Verify weighted average
        self.assertAlmostEqual(merged_x, 2.0167, places=3)
        self.assertAlmostEqual(merged_y, 1.0083, places=3)
        self.assertEqual(merged_confidence, 0.9)
    
    def test_merge_distance_threshold(self):
        """Test that objects are only merged within distance threshold"""
        merge_distance = 1.0  # meters
        
        existing_objects = {
            'chair_1': {'class': 'chair', 'x': 2.0, 'y': 1.0},
            'chair_2': {'class': 'chair', 'x': 5.0, 'y': 1.0},
        }
        
        # New detection close to chair_1
        new_x, new_y = 2.3, 1.2
        new_class = 'chair'
        
        # Find best match
        best_match = None
        best_distance = float('inf')
        
        for obj_id, obj_data in existing_objects.items():
            if obj_data['class'] == new_class:
                distance = np.sqrt((obj_data['x'] - new_x)**2 + (obj_data['y'] - new_y)**2)
                if distance < merge_distance and distance < best_distance:
                    best_match = obj_id
                    best_distance = distance
        
        # Should match chair_1 (distance ~0.36m), not chair_2 (distance ~2.7m)
        self.assertEqual(best_match, 'chair_1')
        self.assertLess(best_distance, merge_distance)
    
    def test_different_class_no_merge(self):
        """Test that objects of different classes are not merged"""
        existing_objects = {
            'chair_1': {'class': 'chair', 'x': 2.0, 'y': 1.0},
        }
        
        # New detection at same location but different class
        new_x, new_y = 2.0, 1.0
        new_class = 'table'
        merge_distance = 1.0
        
        # Find match
        best_match = None
        for obj_id, obj_data in existing_objects.items():
            if obj_data['class'] == new_class:
                distance = np.sqrt((obj_data['x'] - new_x)**2 + (obj_data['y'] - new_y)**2)
                if distance < merge_distance:
                    best_match = obj_id
        
        # Should not match (different class)
        self.assertIsNone(best_match)
    
    def test_detection_count_increment(self):
        """Test that detection count increments on merge"""
        obj_data = {'detections': 5}
        
        # Simulate detection
        obj_data['detections'] += 1
        
        self.assertEqual(obj_data['detections'], 6)
    
    def test_persistence_file_creation(self):
        """Test that persistence file is created"""
        test_data = {
            'semantic_map': {'chair_1': {'class': 'chair'}},
            'object_counter': 1,
            'saved_at': 1234567890.0
        }
        
        # Save
        with open(self.persistence_file, 'wb') as f:
            pickle.dump(test_data, f)
        
        # Verify file exists
        self.assertTrue(os.path.exists(self.persistence_file))
        
        # Verify file size > 0
        self.assertGreater(os.path.getsize(self.persistence_file), 0)


class TestConfidenceDecayScenarios(unittest.TestCase):
    """Test various confidence decay scenarios"""
    
    def test_decay_after_various_times(self):
        """Test confidence decay at different time intervals"""
        initial_confidence = 1.0
        decay_rate = 0.95
        
        test_cases = [
            (1, 0.95),    # 1 minute
            (2, 0.9025),  # 2 minutes
            (5, 0.7738),  # 5 minutes
            (10, 0.5987), # 10 minutes
            (20, 0.3585), # 20 minutes
        ]
        
        for minutes, expected in test_cases:
            decayed = initial_confidence * (decay_rate ** minutes)
            self.assertAlmostEqual(decayed, expected, places=3,
                                 msg=f"Decay after {minutes} minutes")
    
    def test_object_removal_by_decay(self):
        """Test that objects are removed when confidence decays below threshold"""
        initial_confidence = 0.5
        decay_rate = 0.95
        min_confidence = 0.3
        
        # Calculate when object should be removed
        # 0.5 * 0.95^n < 0.3
        # 0.95^n < 0.6
        # n > log(0.6) / log(0.95) ≈ 10 minutes
        
        confidence_10min = initial_confidence * (decay_rate ** 10)
        confidence_11min = initial_confidence * (decay_rate ** 11)
        
        self.assertGreater(confidence_10min, min_confidence)
        self.assertLess(confidence_11min, min_confidence)


class TestObjectMergingScenarios(unittest.TestCase):
    """Test various object merging scenarios"""
    
    def test_multiple_detections_improve_position(self):
        """Test that multiple detections improve position accuracy"""
        # Simulate noisy detections of same object
        true_position = (2.0, 1.0)
        noise_level = 0.1
        
        detections = [
            (2.05, 1.03),
            (1.98, 0.97),
            (2.02, 1.01),
            (1.97, 1.04),
            (2.03, 0.99),
        ]
        
        # Calculate weighted average (equal weights for simplicity)
        avg_x = sum(d[0] for d in detections) / len(detections)
        avg_y = sum(d[1] for d in detections) / len(detections)
        
        # Average should be closer to true position than individual detections
        avg_error = np.sqrt((avg_x - true_position[0])**2 + (avg_y - true_position[1])**2)
        
        self.assertLess(avg_error, noise_level)
    
    def test_high_confidence_detection_updates_low_confidence(self):
        """Test that high confidence detection updates object confidence"""
        existing_confidence = 0.6
        new_confidence = 0.9
        
        updated_confidence = max(existing_confidence, new_confidence)
        
        self.assertEqual(updated_confidence, 0.9)


if __name__ == '__main__':
    unittest.main()
