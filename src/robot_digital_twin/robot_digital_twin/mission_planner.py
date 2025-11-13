#!/usr/bin/env python3
"""
Mission Planner - Optimize mission plans using digital twin simulation.

Evaluates multiple mission scenarios and recommends optimal plans.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from typing import List, Dict, Any
import json


class MissionPlanner(Node):
    """
    Mission planner using digital twin for what-if analysis.
    
    Simulates multiple mission scenarios and recommends optimal plan.
    """
    
    def __init__(self):
        super().__init__('mission_planner')
        
        # Publishers
        self.plan_pub = self.create_publisher(
            String, '/mission/plan', 10
        )
        
        # Subscribers
        self.request_sub = self.create_subscription(
            String, '/mission/request', self.request_callback, 10
        )
        
        self.get_logger().info('Mission Planner initialized')
    
    def request_callback(self, msg: String):
        """Handle mission planning requests"""
        try:
            request = json.loads(msg.data)
            plan = self.plan_mission(request)
            self.publish_plan(plan)
        except Exception as e:
            self.get_logger().error(f'Error planning mission: {e}')
    
    def plan_mission(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Plan optimal mission using digital twin simulation.
        
        Args:
            request: Mission requirements
            
        Returns:
            Optimal mission plan
        """
        self.get_logger().info('Planning mission')
        
        # Generate alternative plans
        alternatives = self.generate_alternatives(request)
        
        # Simulate each alternative
        results = []
        for alt in alternatives:
            result = self.simulate_plan(alt)
            results.append(result)
        
        # Select best plan
        best_plan = self.select_best_plan(results)
        
        return best_plan
    
    def generate_alternatives(self, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate alternative mission plans"""
        alternatives = []
        
        # Direct path
        alternatives.append({
            'name': 'direct',
            'waypoints': request.get('waypoints', []),
            'speed': 'normal'
        })
        
        # Fast path
        alternatives.append({
            'name': 'fast',
            'waypoints': request.get('waypoints', []),
            'speed': 'fast'
        })
        
        # Safe path
        alternatives.append({
            'name': 'safe',
            'waypoints': request.get('waypoints', []),
            'speed': 'slow',
            'safety_margin': 2.0
        })
        
        return alternatives
    
    def simulate_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate a mission plan"""
        # Simplified simulation
        # In practice, use digital twin for detailed simulation
        
        speed_factors = {'slow': 0.5, 'normal': 1.0, 'fast': 1.5}
        speed_factor = speed_factors.get(plan.get('speed', 'normal'), 1.0)
        
        base_duration = 120.0  # seconds
        duration = base_duration / speed_factor
        
        return {
            'plan': plan,
            'duration': duration,
            'energy': duration * 0.01,  # kWh
            'safety_score': 1.0 / speed_factor,
            'success_probability': 0.95 if plan.get('speed') == 'slow' else 0.85
        }
    
    def select_best_plan(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select best plan based on multiple criteria"""
        # Score each plan
        for result in results:
            score = (
                result['success_probability'] * 0.5 +
                (1.0 / result['duration']) * 0.3 +
                result['safety_score'] * 0.2
            )
            result['score'] = score
        
        # Select highest scoring plan
        best = max(results, key=lambda r: r['score'])
        
        return best
    
    def publish_plan(self, plan: Dict[str, Any]):
        """Publish mission plan"""
        msg = String()
        msg.data = json.dumps(plan, indent=2)
        self.plan_pub.publish(msg)
        self.get_logger().info(f'Published mission plan: {plan["plan"]["name"]}')


def main(args=None):
    rclpy.init(args=args)
    node = MissionPlanner()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
