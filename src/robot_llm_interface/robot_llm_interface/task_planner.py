#!/usr/bin/env python3
"""
Task Planner - Hierarchical task decomposition and planning.

This module handles:
- Complex command decomposition into sub-tasks
- Hierarchical task representation
- Task validation and feasibility checking
- Task execution monitoring
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import json
import uuid


class TaskType(Enum):
    """Types of robot tasks"""
    NAVIGATE = "navigate"
    FIND_OBJECT = "find_object"
    GRASP_OBJECT = "grasp_object"
    RELEASE_OBJECT = "release_object"
    EXPLORE = "explore"
    WAIT = "wait"
    STOP = "stop"
    SEQUENCE = "sequence"  # Execute sub-tasks in order
    PARALLEL = "parallel"  # Execute sub-tasks in parallel


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Hierarchical task representation"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType = TaskType.NAVIGATE
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    sub_tasks: List['Task'] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    parent_task: Optional[str] = None
    priority: int = 0
    timeout: float = 300.0  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            'task_id': self.task_id,
            'task_type': self.task_type.value,
            'description': self.description,
            'parameters': self.parameters,
            'sub_tasks': [t.to_dict() for t in self.sub_tasks],
            'status': self.status.value,
            'parent_task': self.parent_task,
            'priority': self.priority,
            'timeout': self.timeout
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary"""
        task = cls(
            task_id=data.get('task_id', str(uuid.uuid4())),
            task_type=TaskType(data.get('task_type', 'navigate')),
            description=data.get('description', ''),
            parameters=data.get('parameters', {}),
            status=TaskStatus(data.get('status', 'pending')),
            parent_task=data.get('parent_task'),
            priority=data.get('priority', 0),
            timeout=data.get('timeout', 300.0)
        )
        task.sub_tasks = [cls.from_dict(st) for st in data.get('sub_tasks', [])]
        return task


class TaskPlanner(Node):
    """
    Hierarchical task planner for complex command decomposition.
    
    Decomposes complex natural language commands into executable
    sub-tasks and manages their execution.
    """
    
    def __init__(self):
        super().__init__('task_planner')
        
        # Declare parameters
        self.declare_parameters(
            namespace='',
            parameters=[
                ('max_task_depth', 5),
                ('task_timeout', 300.0),
                ('enable_parallel_execution', False),
            ]
        )
        
        # Get parameters
        self.max_task_depth = self.get_parameter('max_task_depth').value
        self.default_timeout = self.get_parameter('task_timeout').value
        self.enable_parallel = self.get_parameter('enable_parallel_execution').value
        
        # Task queue and history
        self.current_task: Optional[Task] = None
        self.task_queue: List[Task] = []
        self.task_history: List[Task] = []
        
        # Publishers
        self.task_plan_pub = self.create_publisher(
            String, '/task_planner/plan', 10
        )
        self.task_status_pub = self.create_publisher(
            String, '/task_planner/status', 10
        )
        
        # Subscribers
        self.command_sub = self.create_subscription(
            String, '/task_planner/command', self.command_callback, 10
        )
        self.task_update_sub = self.create_subscription(
            String, '/task_planner/update', self.task_update_callback, 10
        )
        
        # Timer for task execution monitoring
        self.create_timer(1.0, self.monitor_tasks)
        
        self.get_logger().info('Task Planner initialized')
    
    def command_callback(self, msg: String):
        """Handle incoming task commands"""
        try:
            command_data = json.loads(msg.data)
            task = self.decompose_command(command_data)
            
            if task:
                self.task_queue.append(task)
                self._publish_task_plan(task)
                self.get_logger().info(f'Task added to queue: {task.description}')
        except json.JSONDecodeError:
            self.get_logger().error('Failed to parse command JSON')
        except Exception as e:
            self.get_logger().error(f'Error processing command: {e}')
    
    def task_update_callback(self, msg: String):
        """Handle task status updates"""
        try:
            update_data = json.loads(msg.data)
            task_id = update_data.get('task_id')
            new_status = TaskStatus(update_data.get('status', 'pending'))
            
            self._update_task_status(task_id, new_status)
        except Exception as e:
            self.get_logger().error(f'Error updating task status: {e}')
    
    def decompose_command(self, command_data: Dict[str, Any]) -> Optional[Task]:
        """
        Decompose a complex command into hierarchical sub-tasks.
        
        Args:
            command_data: Dictionary containing command information
            
        Returns:
            Root task with sub-tasks
        """
        command_type = command_data.get('task_type', 'unknown')
        target = command_data.get('target', '')
        description = command_data.get('description', '')
        
        # Create root task
        root_task = Task(
            task_type=TaskType.SEQUENCE,
            description=description or f'{command_type} {target}',
            parameters={'original_command': command_data}
        )
        
        # Decompose based on command type
        if command_type == 'navigate':
            root_task.sub_tasks = self._decompose_navigation(target)
        elif command_type == 'find_object':
            root_task.sub_tasks = self._decompose_find_object(target)
        elif command_type == 'retrieve_object':
            root_task.sub_tasks = self._decompose_retrieve_object(target, command_data)
        elif command_type == 'explore':
            root_task.sub_tasks = self._decompose_exploration(command_data)
        else:
            self.get_logger().warn(f'Unknown command type: {command_type}')
            return None
        
        # Validate task depth
        if self._get_task_depth(root_task) > self.max_task_depth:
            self.get_logger().error(f'Task depth exceeds maximum: {self.max_task_depth}')
            return None
        
        return root_task
    
    def _decompose_navigation(self, target: str) -> List[Task]:
        """Decompose navigation command"""
        return [
            Task(
                task_type=TaskType.NAVIGATE,
                description=f'Navigate to {target}',
                parameters={'target': target}
            )
        ]
    
    def _decompose_find_object(self, target: str) -> List[Task]:
        """Decompose object finding command"""
        return [
            Task(
                task_type=TaskType.EXPLORE,
                description='Explore environment',
                parameters={'mode': 'search', 'target': target}
            ),
            Task(
                task_type=TaskType.FIND_OBJECT,
                description=f'Find {target}',
                parameters={'object_class': target}
            )
        ]
    
    def _decompose_retrieve_object(self, target: str, command_data: Dict[str, Any]) -> List[Task]:
        """
        Decompose object retrieval command.
        
        Example: "Go to the kitchen and bring me a coffee mug"
        """
        location = command_data.get('location', 'unknown')
        
        return [
            Task(
                task_type=TaskType.NAVIGATE,
                description=f'Navigate to {location}',
                parameters={'target': location}
            ),
            Task(
                task_type=TaskType.FIND_OBJECT,
                description=f'Find {target}',
                parameters={'object_class': target}
            ),
            Task(
                task_type=TaskType.NAVIGATE,
                description=f'Approach {target}',
                parameters={'target': target, 'approach_distance': 0.5}
            ),
            Task(
                task_type=TaskType.GRASP_OBJECT,
                description=f'Grasp {target}',
                parameters={'object': target}
            ),
            Task(
                task_type=TaskType.NAVIGATE,
                description='Return to user',
                parameters={'target': 'user_location'}
            ),
            Task(
                task_type=TaskType.RELEASE_OBJECT,
                description=f'Release {target}',
                parameters={'object': target}
            )
        ]
    
    def _decompose_exploration(self, command_data: Dict[str, Any]) -> List[Task]:
        """Decompose exploration command"""
        area = command_data.get('area', 'full')
        
        return [
            Task(
                task_type=TaskType.EXPLORE,
                description=f'Explore {area} area',
                parameters={'area': area, 'coverage_target': 0.9}
            )
        ]
    
    def _get_task_depth(self, task: Task, current_depth: int = 0) -> int:
        """Calculate maximum depth of task hierarchy"""
        if not task.sub_tasks:
            return current_depth
        
        max_sub_depth = max(
            self._get_task_depth(st, current_depth + 1) 
            for st in task.sub_tasks
        )
        return max_sub_depth
    
    def _update_task_status(self, task_id: str, new_status: TaskStatus):
        """Update status of a task"""
        # Update current task
        if self.current_task and self.current_task.task_id == task_id:
            self.current_task.status = new_status
            self._publish_task_status(self.current_task)
            
            if new_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                self.task_history.append(self.current_task)
                self.current_task = None
            return
        
        # Update in queue
        for task in self.task_queue:
            if self._update_task_recursive(task, task_id, new_status):
                self._publish_task_status(task)
                return
    
    def _update_task_recursive(self, task: Task, task_id: str, new_status: TaskStatus) -> bool:
        """Recursively update task status"""
        if task.task_id == task_id:
            task.status = new_status
            return True
        
        for sub_task in task.sub_tasks:
            if self._update_task_recursive(sub_task, task_id, new_status):
                return True
        
        return False
    
    def monitor_tasks(self):
        """Monitor task execution and manage queue"""
        # Start next task if no current task
        if not self.current_task and self.task_queue:
            self.current_task = self.task_queue.pop(0)
            self.current_task.status = TaskStatus.IN_PROGRESS
            self._publish_task_status(self.current_task)
            self.get_logger().info(f'Started task: {self.current_task.description}')
    
    def _publish_task_plan(self, task: Task):
        """Publish task plan"""
        msg = String()
        msg.data = json.dumps(task.to_dict(), indent=2)
        self.task_plan_pub.publish(msg)
    
    def _publish_task_status(self, task: Task):
        """Publish task status update"""
        msg = String()
        status_data = {
            'task_id': task.task_id,
            'description': task.description,
            'status': task.status.value,
            'progress': self._calculate_progress(task)
        }
        msg.data = json.dumps(status_data)
        self.task_status_pub.publish(msg)
    
    def _calculate_progress(self, task: Task) -> float:
        """Calculate task completion progress (0.0 to 1.0)"""
        if not task.sub_tasks:
            return 1.0 if task.status == TaskStatus.COMPLETED else 0.0
        
        completed = sum(
            1 for st in task.sub_tasks 
            if st.status == TaskStatus.COMPLETED
        )
        return completed / len(task.sub_tasks)


def main(args=None):
    rclpy.init(args=args)
    node = TaskPlanner()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
