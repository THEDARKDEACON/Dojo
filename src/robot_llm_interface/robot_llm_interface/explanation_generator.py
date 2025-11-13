#!/usr/bin/env python3
"""
Explanation Generator - Generate human-readable explanations of robot actions.

This module handles:
- Action explanation generation
- Reasoning transparency
- Progress updates during execution
- Failure explanations
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from typing import Dict, Any, List
import json
from enum import Enum


class ExplanationVerbosity(Enum):
    """Verbosity levels for explanations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ExplanationGenerator(Node):
    """
    Generate human-readable explanations of robot actions.
    
    Provides transparency into robot decision-making and actions.
    """
    
    def __init__(self):
        super().__init__('explanation_generator')
        
        # Declare parameters
        self.declare_parameters(
            namespace='',
            parameters=[
                ('verbosity', 'medium'),
                ('include_reasoning', True),
                ('include_alternatives', False),
            ]
        )
        
        # Get parameters
        verbosity_str = self.get_parameter('verbosity').value
        self.verbosity = ExplanationVerbosity(verbosity_str)
        self.include_reasoning = self.get_parameter('include_reasoning').value
        self.include_alternatives = self.get_parameter('include_alternatives').value
        
        # Publishers
        self.explanation_pub = self.create_publisher(
            String, '/explanation/output', 10
        )
        
        # Subscribers
        self.action_sub = self.create_subscription(
            String, '/explanation/action', self.action_callback, 10
        )
        self.task_status_sub = self.create_subscription(
            String, '/task_planner/status', self.task_status_callback, 10
        )
        
        # Explanation templates
        self.templates = self._initialize_templates()
        
        self.get_logger().info(
            f'Explanation Generator initialized with verbosity: {self.verbosity.value}'
        )
    
    def _initialize_templates(self) -> Dict[str, Dict[str, str]]:
        """Initialize explanation templates for different actions"""
        return {
            'navigate': {
                'low': "Moving to {target}.",
                'medium': "I'm navigating to {target} using the planned path.",
                'high': "I'm navigating to {target}. I've planned a path that avoids obstacles and maintains safety distances. The estimated time of arrival is {eta} seconds."
            },
            'find_object': {
                'low': "Searching for {object}.",
                'medium': "I'm searching for {object} by exploring the environment and using object detection.",
                'high': "I'm searching for {object}. My strategy is to systematically explore the environment while continuously running object detection. I'll check areas where {object} is typically found first."
            },
            'grasp_object': {
                'low': "Grasping {object}.",
                'medium': "I'm approaching {object} and preparing to grasp it.",
                'high': "I'm approaching {object} at position ({x}, {y}). I'll align my gripper with the object and execute a grasp with appropriate force."
            },
            'explore': {
                'low': "Exploring area.",
                'medium': "I'm exploring the environment to build a map and detect objects.",
                'high': "I'm exploring the environment using frontier-based exploration. I'll systematically visit unexplored areas while building a detailed map and detecting objects."
            },
            'wait': {
                'low': "Waiting.",
                'medium': "I'm waiting for {duration} seconds before continuing.",
                'high': "I'm pausing execution for {duration} seconds. This allows time for {reason}."
            },
            'stop': {
                'low': "Stopped.",
                'medium': "I've stopped all motion as requested.",
                'high': "I've executed an emergency stop. All motors are disabled and the robot is stationary."
            },
            'failure': {
                'low': "Task failed.",
                'medium': "I couldn't complete the task because: {reason}",
                'high': "I couldn't complete the task. Reason: {reason}. I attempted {attempts} times. Possible solutions: {solutions}"
            }
        }
    
    def action_callback(self, msg: String):
        """Handle action explanation requests"""
        try:
            action_data = json.loads(msg.data)
            explanation = self.generate_explanation(action_data)
            self._publish_explanation(explanation)
        except json.JSONDecodeError:
            self.get_logger().error('Failed to parse action JSON')
        except Exception as e:
            self.get_logger().error(f'Error generating explanation: {e}')
    
    def task_status_callback(self, msg: String):
        """Handle task status updates and generate progress explanations"""
        try:
            status_data = json.loads(msg.data)
            explanation = self.generate_progress_explanation(status_data)
            if explanation:
                self._publish_explanation(explanation)
        except json.JSONDecodeError:
            self.get_logger().error('Failed to parse task status JSON')
        except Exception as e:
            self.get_logger().error(f'Error generating progress explanation: {e}')
    
    def generate_explanation(self, action_data: Dict[str, Any]) -> str:
        """
        Generate explanation for an action.
        
        Args:
            action_data: Dictionary containing action information
            
        Returns:
            Human-readable explanation string
        """
        action_type = action_data.get('action_type', 'unknown')
        parameters = action_data.get('parameters', {})
        
        # Get template for action type
        templates = self.templates.get(action_type, {})
        template = templates.get(self.verbosity.value, "Executing {action_type}.")
        
        # Format template with parameters
        try:
            explanation = template.format(**parameters, action_type=action_type)
        except KeyError as e:
            self.get_logger().warn(f'Missing parameter for template: {e}')
            explanation = f"Executing {action_type}."
        
        # Add reasoning if enabled
        if self.include_reasoning and 'reasoning' in action_data:
            explanation += f"\n\nReasoning: {action_data['reasoning']}"
        
        # Add alternatives if enabled
        if self.include_alternatives and 'alternatives' in action_data:
            alternatives = action_data['alternatives']
            explanation += f"\n\nAlternative approaches considered: {', '.join(alternatives)}"
        
        return explanation
    
    def generate_progress_explanation(self, status_data: Dict[str, Any]) -> str:
        """
        Generate progress explanation for task execution.
        
        Args:
            status_data: Dictionary containing task status information
            
        Returns:
            Progress explanation string or empty string if no explanation needed
        """
        status = status_data.get('status', 'unknown')
        description = status_data.get('description', 'task')
        progress = status_data.get('progress', 0.0)
        
        # Only generate explanations for certain status changes
        if status == 'in_progress':
            if self.verbosity == ExplanationVerbosity.HIGH:
                return f"Started: {description}"
            return ""
        elif status == 'completed':
            return f"Completed: {description}"
        elif status == 'failed':
            reason = status_data.get('reason', 'unknown error')
            return f"Failed: {description}. Reason: {reason}"
        elif status == 'cancelled':
            return f"Cancelled: {description}"
        
        # Progress updates for long-running tasks
        if self.verbosity == ExplanationVerbosity.HIGH and progress > 0:
            return f"Progress on {description}: {int(progress * 100)}%"
        
        return ""
    
    def generate_failure_explanation(
        self, 
        task: str, 
        reason: str, 
        attempts: int = 1,
        solutions: List[str] = None
    ) -> str:
        """
        Generate detailed failure explanation.
        
        Args:
            task: Task that failed
            reason: Reason for failure
            attempts: Number of attempts made
            solutions: Possible solutions
            
        Returns:
            Detailed failure explanation
        """
        templates = self.templates.get('failure', {})
        template = templates.get(self.verbosity.value, "Task failed: {reason}")
        
        solutions_str = ', '.join(solutions) if solutions else 'Try again or rephrase command'
        
        explanation = template.format(
            reason=reason,
            attempts=attempts,
            solutions=solutions_str
        )
        
        return explanation
    
    def generate_clarification_explanation(
        self, 
        ambiguity: str, 
        options: List[str]
    ) -> str:
        """
        Generate explanation for why clarification is needed.
        
        Args:
            ambiguity: What is ambiguous
            options: Possible interpretations
            
        Returns:
            Clarification explanation
        """
        if self.verbosity == ExplanationVerbosity.LOW:
            return f"Please clarify: {ambiguity}"
        elif self.verbosity == ExplanationVerbosity.MEDIUM:
            return f"I need clarification about {ambiguity}. Did you mean: {', '.join(options)}?"
        else:  # HIGH
            return (
                f"I detected ambiguity in your command regarding {ambiguity}. "
                f"There are multiple possible interpretations: {', '.join(options)}. "
                f"Please specify which one you intended."
            )
    
    def generate_reasoning_explanation(
        self, 
        decision: str, 
        factors: Dict[str, Any]
    ) -> str:
        """
        Generate explanation of reasoning behind a decision.
        
        Args:
            decision: Decision made
            factors: Factors that influenced the decision
            
        Returns:
            Reasoning explanation
        """
        if self.verbosity == ExplanationVerbosity.LOW:
            return f"Decision: {decision}"
        
        explanation = f"I decided to {decision} based on the following factors:\n"
        
        for factor, value in factors.items():
            explanation += f"- {factor}: {value}\n"
        
        if self.verbosity == ExplanationVerbosity.HIGH:
            explanation += "\nThis decision optimizes for safety, efficiency, and task completion."
        
        return explanation
    
    def _publish_explanation(self, explanation: str):
        """Publish explanation"""
        if not explanation:
            return
        
        msg = String()
        msg.data = explanation
        self.explanation_pub.publish(msg)
        self.get_logger().info(f'Explanation: {explanation}')


def main(args=None):
    rclpy.init(args=args)
    node = ExplanationGenerator()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
