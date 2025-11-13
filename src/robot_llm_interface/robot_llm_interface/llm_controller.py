#!/usr/bin/env python3
"""
LLM Controller Node - Main interface for LLM-powered robot control.

This node handles:
- Natural language command parsing
- LLM API integration
- Prompt engineering for robot control
- Response parsing and action generation
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LLAMA = "llama"


@dataclass
class RobotContext:
    """Current robot context for LLM"""
    position: Optional[Dict[str, float]] = None
    semantic_map: Optional[Dict[str, Any]] = None
    capabilities: List[str] = None
    current_task: Optional[str] = None


class LLMController(Node):
    """
    LLM Controller for natural language robot control.
    
    Integrates with various LLM providers to understand and execute
    natural language commands.
    """
    
    def __init__(self):
        super().__init__('llm_controller')
        
        # Declare parameters
        self.declare_parameters(
            namespace='',
            parameters=[
                ('llm_provider', 'ollama'),
                ('openai_model', 'gpt-4'),
                ('anthropic_model', 'claude-3-sonnet-20240229'),
                ('ollama_base_url', 'http://localhost:11434'),
                ('ollama_model', 'llama2'),
                ('response_timeout', 10.0),
                ('generate_explanations', True),
                ('require_confirmation', True),
                ('log_llm_requests', True),
            ]
        )
        
        # Get parameters
        self.llm_provider = LLMProvider(
            self.get_parameter('llm_provider').value
        )
        self.response_timeout = self.get_parameter('response_timeout').value
        self.generate_explanations = self.get_parameter('generate_explanations').value
        self.require_confirmation = self.get_parameter('require_confirmation').value
        self.log_requests = self.get_parameter('log_llm_requests').value
        
        # Initialize robot context
        self.robot_context = RobotContext(
            capabilities=[
                "navigate to locations",
                "detect and identify objects",
                "avoid obstacles",
                "follow paths",
                "explore environments",
                "maintain safety distances"
            ]
        )
        
        # Initialize LLM client
        self.llm_client = self._initialize_llm_client()
        
        # Publishers
        self.explanation_pub = self.create_publisher(
            String, '/llm/explanation', 10
        )
        self.clarification_pub = self.create_publisher(
            String, '/llm/clarification_request', 10
        )
        self.task_status_pub = self.create_publisher(
            String, '/llm/task_status', 10
        )
        self.nav_goal_pub = self.create_publisher(
            PoseStamped, '/navigate_to_object', 10
        )
        
        # Subscribers
        self.command_sub = self.create_subscription(
            String, '/llm/command', self.command_callback, 10
        )
        self.semantic_map_sub = self.create_subscription(
            String, '/semantic_map', self.semantic_map_callback, 10
        )
        self.robot_pose_sub = self.create_subscription(
            PoseStamped, '/robot_pose', self.robot_pose_callback, 10
        )
        self.clarification_response_sub = self.create_subscription(
            String, '/llm/clarification_response', 
            self.clarification_response_callback, 10
        )
        
        # State
        self.pending_clarification = False
        self.pending_command = None
        
        self.get_logger().info(
            f'LLM Controller initialized with provider: {self.llm_provider.value}'
        )
    
    def _initialize_llm_client(self):
        """Initialize the appropriate LLM client based on provider"""
        if self.llm_provider == LLMProvider.OPENAI:
            return self._init_openai_client()
        elif self.llm_provider == LLMProvider.ANTHROPIC:
            return self._init_anthropic_client()
        elif self.llm_provider == LLMProvider.OLLAMA:
            return self._init_ollama_client()
        elif self.llm_provider == LLMProvider.LLAMA:
            return self._init_llama_client()
        else:
            self.get_logger().error(f'Unsupported LLM provider: {self.llm_provider}')
            return None
    
    def _init_openai_client(self):
        """Initialize OpenAI client"""
        try:
            import openai
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                self.get_logger().warn('OPENAI_API_KEY not set')
                return None
            openai.api_key = api_key
            self.openai_model = self.get_parameter('openai_model').value
            self.get_logger().info(f'OpenAI client initialized with model: {self.openai_model}')
            return openai
        except ImportError:
            self.get_logger().error('openai package not installed. Run: pip install openai')
            return None
    
    def _init_anthropic_client(self):
        """Initialize Anthropic client"""
        try:
            import anthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                self.get_logger().warn('ANTHROPIC_API_KEY not set')
                return None
            client = anthropic.Anthropic(api_key=api_key)
            self.anthropic_model = self.get_parameter('anthropic_model').value
            self.get_logger().info(f'Anthropic client initialized with model: {self.anthropic_model}')
            return client
        except ImportError:
            self.get_logger().error('anthropic package not installed. Run: pip install anthropic')
            return None
    
    def _init_ollama_client(self):
        """Initialize Ollama client"""
        try:
            import ollama
            self.ollama_model = self.get_parameter('ollama_model').value
            self.ollama_base_url = self.get_parameter('ollama_base_url').value
            self.get_logger().info(
                f'Ollama client initialized with model: {self.ollama_model} '
                f'at {self.ollama_base_url}'
            )
            return ollama
        except ImportError:
            self.get_logger().error('ollama package not installed. Run: pip install ollama')
            return None
    
    def _init_llama_client(self):
        """Initialize local LLaMA client"""
        try:
            from llama_cpp import Llama
            model_path = self.get_parameter('llama_model_path').value
            if not model_path or not os.path.exists(model_path):
                self.get_logger().error(f'LLaMA model not found at: {model_path}')
                return None
            llm = Llama(model_path=model_path)
            self.get_logger().info(f'LLaMA client initialized with model: {model_path}')
            return llm
        except ImportError:
            self.get_logger().error('llama-cpp-python not installed. Run: pip install llama-cpp-python')
            return None
    
    def command_callback(self, msg: String):
        """Handle incoming natural language commands"""
        command = msg.data
        self.get_logger().info(f'Received command: {command}')
        
        if self.pending_clarification:
            self.get_logger().warn('Clarification pending, ignoring new command')
            return
        
        # Process command with LLM
        self.process_command(command)
    
    def semantic_map_callback(self, msg: String):
        """Update semantic map context"""
        try:
            self.robot_context.semantic_map = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().warn('Failed to parse semantic map')
    
    def robot_pose_callback(self, msg: PoseStamped):
        """Update robot position context"""
        self.robot_context.position = {
            'x': msg.pose.position.x,
            'y': msg.pose.position.y,
            'z': msg.pose.position.z
        }
    
    def clarification_response_callback(self, msg: String):
        """Handle user response to clarification request"""
        if not self.pending_clarification:
            return
        
        response = msg.data
        self.get_logger().info(f'Received clarification: {response}')
        
        # Process original command with clarification
        if self.pending_command:
            self.process_command(self.pending_command, clarification=response)
        
        self.pending_clarification = False
        self.pending_command = None
    
    def process_command(self, command: str, clarification: Optional[str] = None):
        """Process command using LLM"""
        if not self.llm_client:
            self.get_logger().error('LLM client not initialized')
            return
        
        # Build prompt with robot context
        prompt = self._build_prompt(command, clarification)
        
        if self.log_requests:
            self.get_logger().info(f'LLM Prompt: {prompt}')
        
        # Get LLM response
        try:
            response = self._query_llm(prompt)
            
            if self.log_requests:
                self.get_logger().info(f'LLM Response: {response}')
            
            # Parse and execute response
            self._execute_llm_response(response, command)
            
        except Exception as e:
            self.get_logger().error(f'Error processing command: {str(e)}')
            self._publish_explanation(f'Sorry, I encountered an error: {str(e)}')
    
    def _build_prompt(self, command: str, clarification: Optional[str] = None) -> str:
        """Build prompt for LLM with robot context"""
        prompt = f"""You are an AI assistant controlling a mobile robot. 

Robot Capabilities:
{chr(10).join(f'- {cap}' for cap in self.robot_context.capabilities)}

Current Robot State:
- Position: {self.robot_context.position if self.robot_context.position else 'Unknown'}
- Semantic Map: {len(self.robot_context.semantic_map.get('objects', [])) if self.robot_context.semantic_map else 0} objects detected

User Command: {command}
"""
        
        if clarification:
            prompt += f"\nUser Clarification: {clarification}\n"
        
        prompt += """
Please analyze this command and respond with a JSON object containing:
{
  "understood": true/false,
  "needs_clarification": true/false,
  "clarification_question": "question if needed",
  "task_type": "navigate|find_object|explore|stop|unknown",
  "target": "target object or location",
  "sub_tasks": ["list of sub-tasks"],
  "explanation": "human-readable explanation of what you'll do"
}

Respond ONLY with the JSON object, no additional text.
"""
        return prompt
    
    def _query_llm(self, prompt: str) -> str:
        """Query the LLM and return response"""
        if self.llm_provider == LLMProvider.OPENAI:
            return self._query_openai(prompt)
        elif self.llm_provider == LLMProvider.ANTHROPIC:
            return self._query_anthropic(prompt)
        elif self.llm_provider == LLMProvider.OLLAMA:
            return self._query_ollama(prompt)
        elif self.llm_provider == LLMProvider.LLAMA:
            return self._query_llama(prompt)
        else:
            raise ValueError(f'Unsupported provider: {self.llm_provider}')
    
    def _query_openai(self, prompt: str) -> str:
        """Query OpenAI API"""
        response = self.llm_client.ChatCompletion.create(
            model=self.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    
    def _query_anthropic(self, prompt: str) -> str:
        """Query Anthropic API"""
        message = self.llm_client.messages.create(
            model=self.anthropic_model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    
    def _query_ollama(self, prompt: str) -> str:
        """Query Ollama API"""
        response = self.llm_client.chat(
            model=self.ollama_model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response['message']['content']
    
    def _query_llama(self, prompt: str) -> str:
        """Query local LLaMA model"""
        response = self.llm_client(prompt, max_tokens=1000, temperature=0.7)
        return response['choices'][0]['text']
    
    def _execute_llm_response(self, response: str, original_command: str):
        """Parse LLM response and execute actions"""
        try:
            # Extract JSON from response (handle markdown code blocks)
            response_text = response.strip()
            if response_text.startswith('```'):
                # Remove markdown code block markers
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1])
            
            parsed = json.loads(response_text)
            
            # Check if clarification needed
            if parsed.get('needs_clarification', False):
                question = parsed.get('clarification_question', 'Could you please clarify?')
                self._request_clarification(question, original_command)
                return
            
            # Check if command understood
            if not parsed.get('understood', False):
                self._publish_explanation(
                    "I'm sorry, I didn't understand that command. Could you rephrase it?"
                )
                return
            
            # Publish explanation
            if self.generate_explanations and 'explanation' in parsed:
                self._publish_explanation(parsed['explanation'])
            
            # Execute task based on type
            task_type = parsed.get('task_type', 'unknown')
            target = parsed.get('target', '')
            
            if task_type == 'navigate':
                self._execute_navigation(target)
            elif task_type == 'find_object':
                self._execute_find_object(target)
            elif task_type == 'explore':
                self._execute_exploration()
            elif task_type == 'stop':
                self._execute_stop()
            else:
                self.get_logger().warn(f'Unknown task type: {task_type}')
            
        except json.JSONDecodeError as e:
            self.get_logger().error(f'Failed to parse LLM response as JSON: {e}')
            self.get_logger().error(f'Response was: {response}')
            self._publish_explanation('Sorry, I had trouble understanding how to execute that command.')
        except Exception as e:
            self.get_logger().error(f'Error executing LLM response: {e}')
            self._publish_explanation(f'Sorry, I encountered an error: {str(e)}')
    
    def _request_clarification(self, question: str, original_command: str):
        """Request clarification from user"""
        self.pending_clarification = True
        self.pending_command = original_command
        
        msg = String()
        msg.data = question
        self.clarification_pub.publish(msg)
        
        self.get_logger().info(f'Requesting clarification: {question}')
    
    def _publish_explanation(self, explanation: str):
        """Publish explanation to user"""
        msg = String()
        msg.data = explanation
        self.explanation_pub.publish(msg)
        self.get_logger().info(f'Explanation: {explanation}')
    
    def _execute_navigation(self, target: str):
        """Execute navigation to target"""
        self.get_logger().info(f'Executing navigation to: {target}')
        
        # Find target in semantic map
        if self.robot_context.semantic_map:
            objects = self.robot_context.semantic_map.get('objects', [])
            for obj in objects:
                if target.lower() in obj.get('class', '').lower():
                    # Publish navigation goal
                    goal = PoseStamped()
                    goal.header.frame_id = 'map'
                    goal.header.stamp = self.get_clock().now().to_msg()
                    goal.pose.position.x = obj.get('x', 0.0)
                    goal.pose.position.y = obj.get('y', 0.0)
                    goal.pose.orientation.w = 1.0
                    
                    self.nav_goal_pub.publish(goal)
                    self._publish_explanation(f'Navigating to {target} at ({obj.get("x")}, {obj.get("y")})')
                    return
        
        self._publish_explanation(f'Sorry, I could not find {target} in the semantic map.')
    
    def _execute_find_object(self, target: str):
        """Execute object finding"""
        self.get_logger().info(f'Executing find object: {target}')
        self._publish_explanation(f'Searching for {target}...')
        # This would integrate with exploration and object detection
    
    def _execute_exploration(self):
        """Execute exploration"""
        self.get_logger().info('Executing exploration')
        self._publish_explanation('Starting exploration of the environment...')
        # This would integrate with autonomous exploration
    
    def _execute_stop(self):
        """Execute stop command"""
        self.get_logger().info('Executing stop')
        self._publish_explanation('Stopping all motion.')
        # Publish zero velocity or trigger emergency stop


def main(args=None):
    rclpy.init(args=args)
    node = LLMController()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
