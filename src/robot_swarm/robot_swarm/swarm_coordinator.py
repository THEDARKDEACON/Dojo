#!/usr/bin/env python3
"""
SwarmCoordinator: Distributed multi-robot coordination node

This node manages:
- Robot discovery and heartbeat monitoring
- Distributed task allocation using auction-based mechanism
- Task redistribution on robot failure
- Swarm-wide communication via DDS
"""

import time
import uuid
import json
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy

from std_msgs.msg import String
from geometry_msgs.msg import Point, PoseStamped
from nav_msgs.msg import Odometry


class TaskType(Enum):
    """Types of tasks that can be allocated."""
    EXPLORE = "explore"
    GOTO = "goto"
    PATROL = "patrol"
    SEARCH = "search"


class TaskStatus(Enum):
    """Status of a task."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SwarmTask:
    """Represents a task in the swarm."""
    task_id: str
    task_type: TaskType
    priority: int  # 0-10, higher is more important
    location: tuple  # (x, y)
    area: Optional[List[tuple]] = None  # Polygon for area-based tasks
    estimated_cost: float = 0.0
    assigned_robot: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    deadline: Optional[float] = None
    created_time: float = 0.0


@dataclass
class RobotInfo:
    """Information about a robot in the swarm."""
    robot_id: str
    position: tuple  # (x, y)
    status: str  # 'idle', 'busy', 'failed'
    current_task: Optional[str] = None
    last_heartbeat: float = 0.0
    capabilities: List[str] = None


@dataclass
class SwarmMessage:
    """Message format for swarm communication."""
    sender_id: str
    message_type: str  # 'heartbeat', 'task_bid', 'task_assign', 'task_complete', 'discovery'
    timestamp: float
    data: dict


class SwarmCoordinator(Node):
    """
    Distributed swarm coordination node.
    
    Features:
    - Robot discovery via heartbeat
    - Auction-based task allocation
    - Failure detection and recovery
    - DDS communication
    """
    
    def __init__(self):
        super().__init__('swarm_coordinator')
        
        # Declare parameters
        self.declare_parameter('robot_id', '')
        self.declare_parameter('namespace', '')
        self.declare_parameter('heartbeat_rate', 1.0)  # Hz
        self.declare_parameter('heartbeat_timeout', 5.0)  # seconds
        self.declare_parameter('auction_timeout', 2.0)  # seconds
        
        # Get parameters
        self.robot_id = self.get_parameter('robot_id').value
        if not self.robot_id:
            self.robot_id = f'robot_{uuid.uuid4().hex[:8]}'
        
        self.namespace = self.get_parameter('namespace').value
        self.heartbeat_rate = self.get_parameter('heartbeat_rate').value
        self.heartbeat_timeout = self.get_parameter('heartbeat_timeout').value
        self.auction_timeout = self.get_parameter('auction_timeout').value
        
        # Swarm state
        self.robots: Dict[str, RobotInfo] = {}
        self.tasks: Dict[str, SwarmTask] = {}
        self.my_position = (0.0, 0.0)
        self.my_status = 'idle'
        self.my_current_task = None
        
        # Auction state
        self.active_auctions: Dict[str, dict] = {}  # task_id -> auction_info
        self.my_bids: Dict[str, float] = {}  # task_id -> bid_value
        
        # QoS profile for swarm communication (transient local for discovery)
        swarm_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=100,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )
        
        # Publishers
        self.swarm_pub = self.create_publisher(
            String,
            '/swarm/messages',
            swarm_qos
        )
        
        self.task_status_pub = self.create_publisher(
            String,
            f'/{self.robot_id}/task_status',
            10
        )
        
        # Subscribers
        self.swarm_sub = self.create_subscription(
            String,
            '/swarm/messages',
            self.swarm_message_callback,
            swarm_qos
        )
        
        self.odom_sub = self.create_subscription(
            Odometry,
            f'/{self.robot_id}/odom',
            self.odom_callback,
            10
        )
        
        # Timers
        self.heartbeat_timer = self.create_timer(
            1.0 / self.heartbeat_rate,
            self.send_heartbeat
        )
        
        self.monitor_timer = self.create_timer(
            1.0,
            self.monitor_swarm
        )
        
        self.task_allocation_timer = self.create_timer(
            0.5,
            self.process_task_allocation
        )
        
        # Register this robot
        self.robots[self.robot_id] = RobotInfo(
            robot_id=self.robot_id,
            position=self.my_position,
            status=self.my_status,
            last_heartbeat=time.time(),
            capabilities=['navigate', 'explore', 'map']
        )
        
        # Send discovery message
        self.send_discovery()
        
        self.get_logger().info(f'SwarmCoordinator initialized for robot {self.robot_id}')
    
    def odom_callback(self, msg: Odometry):
        """Update robot position from odometry."""
        self.my_position = (
            msg.pose.pose.position.x,
            msg.pose.pose.position.y
        )
        
        # Update in robots dict
        if self.robot_id in self.robots:
            self.robots[self.robot_id].position = self.my_position
    
    def swarm_message_callback(self, msg: String):
        """Process incoming swarm messages."""
        try:
            data = json.loads(msg.data)
            swarm_msg = SwarmMessage(**data)
            
            # Ignore own messages
            if swarm_msg.sender_id == self.robot_id:
                return
            
            # Process message based on type
            if swarm_msg.message_type == 'heartbeat':
                self.handle_heartbeat(swarm_msg)
            elif swarm_msg.message_type == 'discovery':
                self.handle_discovery(swarm_msg)
            elif swarm_msg.message_type == 'task_announce':
                self.handle_task_announce(swarm_msg)
            elif swarm_msg.message_type == 'task_bid':
                self.handle_task_bid(swarm_msg)
            elif swarm_msg.message_type == 'task_assign':
                self.handle_task_assign(swarm_msg)
            elif swarm_msg.message_type == 'task_complete':
                self.handle_task_complete(swarm_msg)
            elif swarm_msg.message_type == 'task_failed':
                self.handle_task_failed(swarm_msg)
                
        except Exception as e:
            self.get_logger().error(f'Error processing swarm message: {e}')
    
    def send_swarm_message(self, message_type: str, data: dict):
        """Send a message to the swarm."""
        swarm_msg = SwarmMessage(
            sender_id=self.robot_id,
            message_type=message_type,
            timestamp=time.time(),
            data=data
        )
        
        msg = String()
        msg.data = json.dumps(asdict(swarm_msg))
        self.swarm_pub.publish(msg)
    
    def send_heartbeat(self):
        """Send periodic heartbeat to swarm."""
        self.send_swarm_message('heartbeat', {
            'position': self.my_position,
            'status': self.my_status,
            'current_task': self.my_current_task
        })
        
        # Update own heartbeat
        if self.robot_id in self.robots:
            self.robots[self.robot_id].last_heartbeat = time.time()
    
    def send_discovery(self):
        """Send discovery message to announce presence."""
        self.send_swarm_message('discovery', {
            'position': self.my_position,
            'capabilities': ['navigate', 'explore', 'map']
        })
        
        self.get_logger().info(f'Sent discovery message for {self.robot_id}')
    
    def handle_heartbeat(self, msg: SwarmMessage):
        """Handle heartbeat from another robot."""
        robot_id = msg.sender_id
        
        if robot_id not in self.robots:
            # New robot discovered
            self.robots[robot_id] = RobotInfo(
                robot_id=robot_id,
                position=msg.data.get('position', (0.0, 0.0)),
                status=msg.data.get('status', 'idle'),
                current_task=msg.data.get('current_task'),
                last_heartbeat=msg.timestamp
            )
            self.get_logger().info(f'Discovered new robot: {robot_id}')
        else:
            # Update existing robot
            robot = self.robots[robot_id]
            robot.position = msg.data.get('position', robot.position)
            robot.status = msg.data.get('status', robot.status)
            robot.current_task = msg.data.get('current_task')
            robot.last_heartbeat = msg.timestamp
    
    def handle_discovery(self, msg: SwarmMessage):
        """Handle discovery message from new robot."""
        robot_id = msg.sender_id
        
        if robot_id not in self.robots:
            self.robots[robot_id] = RobotInfo(
                robot_id=robot_id,
                position=msg.data.get('position', (0.0, 0.0)),
                status='idle',
                last_heartbeat=msg.timestamp,
                capabilities=msg.data.get('capabilities', [])
            )
            self.get_logger().info(f'Robot {robot_id} joined the swarm')
            
            # Send our own discovery in response
            self.send_discovery()
    
    def monitor_swarm(self):
        """Monitor swarm for failed robots."""
        current_time = time.time()
        failed_robots = []
        
        for robot_id, robot in self.robots.items():
            if robot_id == self.robot_id:
                continue
            
            # Check if heartbeat timeout
            if current_time - robot.last_heartbeat > self.heartbeat_timeout:
                if robot.status != 'failed':
                    robot.status = 'failed'
                    failed_robots.append(robot_id)
                    self.get_logger().warn(f'Robot {robot_id} failed (heartbeat timeout)')
        
        # Redistribute tasks from failed robots
        for robot_id in failed_robots:
            self.redistribute_tasks(robot_id)
    
    def redistribute_tasks(self, failed_robot_id: str):
        """Redistribute tasks from a failed robot."""
        tasks_to_redistribute = []
        
        for task_id, task in self.tasks.items():
            if task.assigned_robot == failed_robot_id and task.status != TaskStatus.COMPLETED:
                tasks_to_redistribute.append(task_id)
        
        if tasks_to_redistribute:
            self.get_logger().info(
                f'Redistributing {len(tasks_to_redistribute)} tasks from failed robot {failed_robot_id}'
            )
            
            for task_id in tasks_to_redistribute:
                task = self.tasks[task_id]
                task.status = TaskStatus.PENDING
                task.assigned_robot = None
                
                # Announce task for re-auction
                self.announce_task(task)
    
    def create_task(self, task_type: TaskType, location: tuple, priority: int = 5) -> SwarmTask:
        """Create a new task."""
        task = SwarmTask(
            task_id=f'task_{uuid.uuid4().hex[:8]}',
            task_type=task_type,
            priority=priority,
            location=location,
            created_time=time.time()
        )
        
        self.tasks[task.task_id] = task
        return task
    
    def announce_task(self, task: SwarmTask):
        """Announce a task for auction."""
        self.send_swarm_message('task_announce', {
            'task_id': task.task_id,
            'task_type': task.task_type.value,
            'priority': task.priority,
            'location': task.location,
            'estimated_cost': task.estimated_cost
        })
        
        # Start auction
        self.active_auctions[task.task_id] = {
            'start_time': time.time(),
            'bids': {},
            'task': task
        }
        
        self.get_logger().info(f'Announced task {task.task_id} for auction')
    
    def handle_task_announce(self, msg: SwarmMessage):
        """Handle task announcement and submit bid."""
        task_data = msg.data
        task_id = task_data['task_id']
        
        # Calculate bid based on distance and current load
        task_location = tuple(task_data['location'])
        distance = self.calculate_distance(self.my_position, task_location)
        
        # Bid is based on distance (lower is better)
        # Add penalty if already busy
        bid_value = distance
        if self.my_status == 'busy':
            bid_value += 10.0  # Penalty for being busy
        
        # Submit bid
        self.my_bids[task_id] = bid_value
        self.send_swarm_message('task_bid', {
            'task_id': task_id,
            'bid_value': bid_value
        })
        
        self.get_logger().info(f'Submitted bid {bid_value:.2f} for task {task_id}')
    
    def handle_task_bid(self, msg: SwarmMessage):
        """Handle bid from another robot."""
        task_id = msg.data['task_id']
        bid_value = msg.data['bid_value']
        robot_id = msg.sender_id
        
        if task_id in self.active_auctions:
            auction = self.active_auctions[task_id]
            auction['bids'][robot_id] = bid_value
    
    def process_task_allocation(self):
        """Process active auctions and allocate tasks."""
        current_time = time.time()
        completed_auctions = []
        
        for task_id, auction in self.active_auctions.items():
            # Check if auction timeout
            if current_time - auction['start_time'] > self.auction_timeout:
                # Find winner (lowest bid)
                if auction['bids']:
                    winner_id = min(auction['bids'], key=auction['bids'].get)
                    winning_bid = auction['bids'][winner_id]
                    
                    # Assign task to winner
                    task = auction['task']
                    task.assigned_robot = winner_id
                    task.status = TaskStatus.ASSIGNED
                    
                    # Announce assignment
                    self.send_swarm_message('task_assign', {
                        'task_id': task_id,
                        'assigned_robot': winner_id,
                        'winning_bid': winning_bid
                    })
                    
                    self.get_logger().info(
                        f'Task {task_id} assigned to {winner_id} (bid: {winning_bid:.2f})'
                    )
                
                completed_auctions.append(task_id)
        
        # Remove completed auctions
        for task_id in completed_auctions:
            del self.active_auctions[task_id]
    
    def handle_task_assign(self, msg: SwarmMessage):
        """Handle task assignment."""
        task_id = msg.data['task_id']
        assigned_robot = msg.data['assigned_robot']
        
        if assigned_robot == self.robot_id:
            # This task is assigned to us
            self.my_current_task = task_id
            self.my_status = 'busy'
            
            self.get_logger().info(f'Assigned task {task_id}')
            
            # Publish task status
            status_msg = String()
            status_msg.data = json.dumps({
                'task_id': task_id,
                'status': 'assigned'
            })
            self.task_status_pub.publish(status_msg)
    
    def handle_task_complete(self, msg: SwarmMessage):
        """Handle task completion."""
        task_id = msg.data['task_id']
        
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.COMPLETED
            self.get_logger().info(f'Task {task_id} completed by {msg.sender_id}')
    
    def handle_task_failed(self, msg: SwarmMessage):
        """Handle task failure."""
        task_id = msg.data['task_id']
        
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = TaskStatus.PENDING
            task.assigned_robot = None
            
            # Re-announce for auction
            self.announce_task(task)
            
            self.get_logger().warn(f'Task {task_id} failed, re-auctioning')
    
    def complete_task(self, task_id: str):
        """Mark a task as completed."""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.COMPLETED
            
            # Announce completion
            self.send_swarm_message('task_complete', {
                'task_id': task_id
            })
            
            # Update own status
            self.my_current_task = None
            self.my_status = 'idle'
            
            self.get_logger().info(f'Completed task {task_id}')
    
    def calculate_distance(self, pos1: tuple, pos2: tuple) -> float:
        """Calculate Euclidean distance between two positions."""
        return ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5
    
    def get_swarm_status(self) -> dict:
        """Get current swarm status."""
        return {
            'robot_id': self.robot_id,
            'num_robots': len(self.robots),
            'active_robots': sum(1 for r in self.robots.values() if r.status != 'failed'),
            'num_tasks': len(self.tasks),
            'pending_tasks': sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING),
            'active_tasks': sum(1 for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS),
            'completed_tasks': sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        }


def main(args=None):
    """Main function."""
    rclpy.init(args=args)
    
    try:
        node = SwarmCoordinator()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
