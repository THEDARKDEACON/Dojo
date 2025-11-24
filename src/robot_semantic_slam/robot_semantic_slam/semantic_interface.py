#!/usr/bin/env python3
"""
Semantic Interface - Natural language command processing for robot control
Enables human-like interaction with the robot using text commands
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped, Twist
import re
from typing import Dict, List, Tuple
import json

class SemanticInterface(Node):
    """Natural language interface for robot control"""
    
    def __init__(self):
        super().__init__('semantic_interface')
        
        # Command patterns and their handlers
        self.command_patterns = {
            r'go to (?:the )?(\w+)': self.handle_navigate_to_object,
            r'find (?:the )?(\w+)': self.handle_find_object,
            r'explore (?:the )?(\w+)': self.handle_explore_area,
            r'stop|halt|emergency stop': self.handle_emergency_stop,
            r'move (forward|backward|left|right)': self.handle_directional_move,
            r'turn (left|right)': self.handle_turn,
            r'list objects|what do you see': self.handle_list_objects,
            r'status|how are you': self.handle_status_request,
            r'map (?:the )?(\w+)': self.handle_mapping_command,
            r'follow (?:the )?(\w+)': self.handle_follow_object,
            r'patrol (?:the )?(\w+)': self.handle_patrol_area,
            r'return home|go home': self.handle_return_home,
            r'save map as (\w+)': self.handle_save_map,
            r'load map (\w+)': self.handle_load_map,
        }
        
        # Publishers
        self.semantic_command_pub = self.create_publisher(String, '/semantic_command', 10)
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.navigation_goal_pub = self.create_publisher(PoseStamped, '/navigate_to_object', 10)
        self.response_pub = self.create_publisher(String, '/semantic_response', 10)
        
        # Subscribers
        self.text_command_sub = self.create_subscription(String, '/text_command', self.text_command_callback, 10)
        self.semantic_map_sub = self.create_subscription(String, '/semantic_map', self.semantic_map_callback, 10)
        self.safety_status_sub = self.create_subscription(String, '/safety_status', self.safety_status_callback, 10)
        
        # State tracking
        self.semantic_objects = {}
        self.robot_status = "ready"
        self.safety_status = {}
        self.home_position = None
        
        # Movement parameters
        self.move_speed = 0.5  # m/s
        self.turn_speed = 0.5  # rad/s
        
        self.get_logger().info("🗣️ Semantic Interface initialized - Ready for natural language commands!")
        self.get_logger().info("💬 Try commands like: 'go to chair', 'find bottle', 'explore kitchen', 'stop'")
    
    def text_command_callback(self, msg: String):
        """Process incoming text commands"""
        command = msg.data.lower().strip()
        self.get_logger().info(f"📝 Received command: '{command}'")
        
        # Process the command
        response = self.process_command(command)
        
        # Send response
        response_msg = String()
        response_msg.data = response
        self.response_pub.publish(response_msg)
        
        self.get_logger().info(f"🤖 Response: {response}")
    
    def semantic_map_callback(self, msg: String):
        """Update semantic map data"""
        try:
            data = json.loads(msg.data)
            self.semantic_objects = data.get('objects', {})
        except json.JSONDecodeError:
            pass
    
    def safety_status_callback(self, msg: String):
        """Update safety status"""
        try:
            self.safety_status = eval(msg.data)  # Simple parsing - use json in production
        except:
            pass
    
    def process_command(self, command: str) -> str:
        """Process natural language command and return response"""
        # Check for pattern matches
        for pattern, handler in self.command_patterns.items():
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                try:
                    return handler(match)
                except Exception as e:
                    return f"Error processing command: {str(e)}"
        
        # No pattern matched
        return self.handle_unknown_command(command)
    
    def handle_navigate_to_object(self, match) -> str:
        """Handle 'go to object' commands"""
        object_name = match.group(1)
        
        # Send semantic command
        cmd_msg = String()
        cmd_msg.data = f"go to {object_name}"
        self.semantic_command_pub.publish(cmd_msg)
        
        # Check if object exists in semantic map
        found_objects = [obj for obj_id, obj in self.semantic_objects.items() 
                        if object_name.lower() in obj.get('class', '').lower()]
        
        if found_objects:
            return f"🎯 Navigating to {object_name}. I can see {len(found_objects)} {object_name}(s) in my map."
        else:
            return f"🔍 I don't see any {object_name} in my current map. I'll explore to find one."
    
    def handle_find_object(self, match) -> str:
        """Handle 'find object' commands"""
        object_name = match.group(1)
        
        # Send semantic command
        cmd_msg = String()
        cmd_msg.data = f"find {object_name}"
        self.semantic_command_pub.publish(cmd_msg)
        
        # Check current map
        found_objects = [obj for obj_id, obj in self.semantic_objects.items() 
                        if object_name.lower() in obj.get('class', '').lower()]
        
        if found_objects:
            locations = []
            for obj in found_objects:
                locations.append(f"({obj['x']:.1f}, {obj['y']:.1f})")
            return f"🔍 Found {len(found_objects)} {object_name}(s) at: {', '.join(locations)}"
        else:
            return f"🔍 No {object_name} found in current map. Starting exploration to find one."
    
    def handle_explore_area(self, match) -> str:
        """Handle area exploration commands"""
        area_name = match.group(1)
        
        # Start autonomous exploration
        cmd_msg = String()
        cmd_msg.data = f"explore {area_name}"
        self.semantic_command_pub.publish(cmd_msg)
        
        return f"🗺️ Starting exploration of {area_name} area. I'll map the space and identify objects."
    
    def handle_emergency_stop(self, match) -> str:
        """Handle emergency stop commands"""
        # Send stop command
        stop_cmd = Twist()
        self.cmd_vel_pub.publish(stop_cmd)
        
        return "🛑 Emergency stop activated. All movement halted."
    
    def handle_directional_move(self, match) -> str:
        """Handle directional movement commands"""
        direction = match.group(1)
        
        cmd_vel = Twist()
        
        if direction == "forward":
            cmd_vel.linear.x = self.move_speed
        elif direction == "backward":
            cmd_vel.linear.x = -self.move_speed
        elif direction == "left":
            cmd_vel.linear.y = self.move_speed
        elif direction == "right":
            cmd_vel.linear.y = -self.move_speed
        
        self.cmd_vel_pub.publish(cmd_vel)
        
        return f"🏃 Moving {direction} at {self.move_speed} m/s"
    
    def handle_turn(self, match) -> str:
        """Handle turning commands"""
        direction = match.group(1)
        
        cmd_vel = Twist()
        
        if direction == "left":
            cmd_vel.angular.z = self.turn_speed
        elif direction == "right":
            cmd_vel.angular.z = -self.turn_speed
        
        self.cmd_vel_pub.publish(cmd_vel)
        
        return f"🔄 Turning {direction} at {self.turn_speed} rad/s"
    
    def handle_list_objects(self, match) -> str:
        """Handle object listing commands"""
        if not self.semantic_objects:
            return "👀 I don't see any objects in my current map. Try exploring first."
        
        object_summary = {}
        for obj_id, obj in self.semantic_objects.items():
            class_name = obj.get('class', 'unknown')
            if class_name in object_summary:
                object_summary[class_name] += 1
            else:
                object_summary[class_name] = 1
        
        summary_text = []
        for obj_class, count in object_summary.items():
            summary_text.append(f"{count} {obj_class}{'s' if count > 1 else ''}")
        
        return f"👀 I can see: {', '.join(summary_text)} (total: {len(self.semantic_objects)} objects)"
    
    def handle_status_request(self, match) -> str:
        """Handle status request commands"""
        status_parts = []
        
        # Basic status
        status_parts.append(f"Status: {self.robot_status}")
        
        # Object count
        status_parts.append(f"Objects detected: {len(self.semantic_objects)}")
        
        # Safety status
        if self.safety_status:
            safety_level = self.safety_status.get('safety_level', 'unknown')
            active_threats = self.safety_status.get('active_threats', 0)
            status_parts.append(f"Safety: {safety_level} ({active_threats} threats)")
        
        return f"🤖 Robot Status - {', '.join(status_parts)}"
    
    def handle_mapping_command(self, match) -> str:
        """Handle mapping commands"""
        area_name = match.group(1)
        
        # Start mapping mode
        cmd_msg = String()
        cmd_msg.data = f"map {area_name}"
        self.semantic_command_pub.publish(cmd_msg)
        
        return f"🗺️ Starting detailed mapping of {area_name}. I'll create a comprehensive map with object locations."
    
    def handle_follow_object(self, match) -> str:
        """Handle object following commands"""
        object_name = match.group(1)
        
        cmd_msg = String()
        cmd_msg.data = f"follow {object_name}"
        self.semantic_command_pub.publish(cmd_msg)
        
        return f"👥 Starting to follow {object_name}. I'll maintain a safe distance and track movement."
    
    def handle_patrol_area(self, match) -> str:
        """Handle area patrol commands"""
        area_name = match.group(1)
        
        cmd_msg = String()
        cmd_msg.data = f"patrol {area_name}"
        self.semantic_command_pub.publish(cmd_msg)
        
        return f"🚶 Starting patrol of {area_name}. I'll continuously monitor the area for changes."
    
    def handle_return_home(self, match) -> str:
        """Handle return home commands"""
        if self.home_position:
            # Navigate to home position
            goal = PoseStamped()
            goal.header.frame_id = "map"
            goal.header.stamp = self.get_clock().now().to_msg()
            goal.pose.position.x = self.home_position[0]
            goal.pose.position.y = self.home_position[1]
            goal.pose.orientation.w = 1.0
            
            self.navigation_goal_pub.publish(goal)
            return f"🏠 Returning to home position at ({self.home_position[0]:.1f}, {self.home_position[1]:.1f})"
        else:
            return "🏠 Home position not set. Current location will be set as home."
    
    def handle_save_map(self, match) -> str:
        """Handle map saving commands"""
        map_name = match.group(1)
        
        cmd_msg = String()
        cmd_msg.data = f"save map {map_name}"
        self.semantic_command_pub.publish(cmd_msg)
        
        return f"💾 Saving current map as '{map_name}'. Map includes {len(self.semantic_objects)} semantic objects."
    
    def handle_load_map(self, match) -> str:
        """Handle map loading commands"""
        map_name = match.group(1)
        
        cmd_msg = String()
        cmd_msg.data = f"load map {map_name}"
        self.semantic_command_pub.publish(cmd_msg)
        
        return f"📂 Loading map '{map_name}'. Semantic objects will be restored."
    
    def handle_unknown_command(self, command: str) -> str:
        """Handle unrecognized commands"""
        suggestions = [
            "Try: 'go to chair', 'find bottle', 'explore kitchen'",
            "Movement: 'move forward', 'turn left', 'stop'",
            "Info: 'list objects', 'status', 'what do you see'",
            "Navigation: 'return home', 'patrol area', 'follow person'"
        ]
        
        return f"❓ I didn't understand '{command}'. {suggestions[len(command) % len(suggestions)]}"

def main(args=None):
    rclpy.init(args=args)
    node = SemanticInterface()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down semantic interface...')
    except Exception as e:
        node.get_logger().error(f'Error in semantic interface: {e}')
    finally:
        node.destroy_node()
        # Don't call rclpy.shutdown() - let launch system handle it

if __name__ == '__main__':
    main()