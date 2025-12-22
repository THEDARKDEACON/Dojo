#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from visualization_msgs.msg import MarkerArray
from sensor_msgs.msg import LaserScan
from rcl_interfaces.msg import Log
import curses
import time
import threading
import sys
import tf2_ros
from rclpy.duration import Duration
import math

class SystemDashboard(Node):
    def __init__(self):
        super().__init__('system_dashboard')
        
        # Data storage
        self.robot_pose = {'x': 0.0, 'y': 0.0, 'theta': 0.0}
        self.cmd_vel = {'linear': 0.0, 'angular': 0.0}
        self.cmd_vel_nav = {'linear': 0.0, 'angular': 0.0}
        self.odom_vel = {'linear': 0.0, 'angular': 0.0}
        self.frontiers = 0
        self.explorer_status = "Waiting..."
        self.nav_goal = {'x': 0.0, 'y': 0.0}
        self.last_update = time.time()
        self.last_log = ""
        self.last_log_time = 0
        self.scan_rate = 0.0
        self.last_scan_time = time.time()
        self.tf_status = "Unknown"
        self.map_status = "Unknown"
        
        # Subscribers
        self.create_subscription(Odometry, '/rosbot_xl_base_controller/odom', self.odom_callback, 10)
        self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.create_subscription(Twist, '/cmd_vel_nav', self.cmd_vel_nav_callback, 10)
        self.create_subscription(String, '/explorer_debug', self.explorer_callback, 10)
        self.create_subscription(MarkerArray, '/exploration_frontiers', self.frontier_callback, 10)
        self.create_subscription(PoseStamped, '/exploration_goal', self.goal_callback, 10)
        self.create_subscription(Log, '/rosout', self.log_callback, 10)
        self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        
        # TF Buffer
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        self.create_timer(1.0, self.check_system_status)

    def check_system_status(self):
        try:
            # Check Map -> Base Link
            if self.tf_buffer.can_transform('map', 'base_link', rclpy.time.Time()):
                self.tf_status = "OK"
            elif self.tf_buffer.can_transform('odom', 'base_link', rclpy.time.Time()):
                self.tf_status = "WARN (Odom Only)"
            else:
                self.tf_status = "FAIL"
        except Exception:
            self.tf_status = "FAIL"

    def log_callback(self, msg):
        if msg.name == "autonomous_explorer":
            self.last_log = msg.msg
            self.last_log_time = time.time()

    def odom_callback(self, msg):
        self.robot_pose['x'] = msg.pose.pose.position.x
        self.robot_pose['y'] = msg.pose.pose.position.y
        self.odom_vel['linear'] = msg.twist.twist.linear.x
        self.odom_vel['angular'] = msg.twist.twist.angular.z
        self.last_update = time.time()

    def cmd_vel_callback(self, msg):
        self.cmd_vel['linear'] = msg.linear.x
        self.cmd_vel['angular'] = msg.angular.z

    def cmd_vel_nav_callback(self, msg):
        self.cmd_vel_nav['linear'] = msg.linear.x
        self.cmd_vel_nav['angular'] = msg.angular.z

    def explorer_callback(self, msg):
        self.explorer_status = msg.data

    def frontier_callback(self, msg):
        self.frontiers = len(msg.markers)

    def goal_callback(self, msg):
        self.nav_goal['x'] = msg.pose.position.x
        self.nav_goal['y'] = msg.pose.position.y
        
    def scan_callback(self, msg):
        current_time = time.time()
        diff = current_time - self.last_scan_time
        if diff > 0:
            self.scan_rate = 1.0 / diff
        self.last_scan_time = current_time

def draw_box(stdscr, y, x, h, w, title, color_pair):
    try:
        # Draw border
        stdscr.attron(color_pair)
        for i in range(h):
            stdscr.addstr(y+i, x, "│")
            stdscr.addstr(y+i, x+w-1, "│")
        for j in range(w):
            stdscr.addstr(y, x+j, "─")
            stdscr.addstr(y+h-1, x+j, "─")
        
        # Corners
        stdscr.addstr(y, x, "╭")
        stdscr.addstr(y, x+w-1, "╮")
        stdscr.addstr(y+h-1, x, "╰")
        stdscr.addstr(y+h-1, x+w-1, "╯")
        
        # Title
        if title:
            stdscr.addstr(y, x+2, f" {title} ", curses.A_BOLD)
        stdscr.attroff(color_pair)
    except curses.error:
        pass

def draw_dashboard(stdscr, node):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(100)

    # Colors
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)   # OK
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # WARN
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)     # FAIL
    curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)    # INFO
    curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # HEADER
    curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLUE)    # BOX HEADER

    while rclpy.ok():
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        if height < 24 or width < 100:
            stdscr.addstr(0, 0, "Terminal too small! Resize to at least 100x24")
            stdscr.refresh()
            rclpy.spin_once(node, timeout_sec=0.1)
            continue

        try:
            # === HEADER ===
            title = " 🚀 DOJO ROBOT - AUTONOMOUS EXPLORATION DASHBOARD 🚀 "
            stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD | curses.color_pair(6))

            # === SIGNAL FLOW DIAGRAM ===
            # [Lidar] -> [SLAM] -> [Map] -> [Planner] -> [Control] -> [Wheels]
            
            flow_y = 2
            margin = 4
            
            # Helper to draw node
            def draw_node(x, label, status):
                color = curses.color_pair(1) if status else curses.color_pair(3)
                stdscr.addstr(flow_y, x, "[", curses.A_BOLD)
                stdscr.addstr(flow_y, x+1, label, color | curses.A_BOLD)
                stdscr.addstr(flow_y, x+1+len(label), "]", curses.A_BOLD)
                return x + len(label) + 4

            # Determine statuses
            lidar_ok = node.scan_rate > 1.0
            slam_ok = "OK" in node.tf_status
            map_ok = node.frontiers > 0 # Rough proxy
            planner_ok = abs(node.cmd_vel_nav['linear']) > 0 or abs(node.cmd_vel_nav['angular']) > 0
            control_ok = abs(node.cmd_vel['linear']) > 0
            wheels_ok = abs(node.odom_vel['linear']) > 0.01

            x = margin
            x = draw_node(x, "LIDAR", lidar_ok)
            stdscr.addstr(flow_y, x-2, "→")
            x = draw_node(x, "SLAM", slam_ok)
            stdscr.addstr(flow_y, x-2, "→")
            x = draw_node(x, "MAP", map_ok)
            stdscr.addstr(flow_y, x-2, "→")
            x = draw_node(x, "PLANNER", planner_ok)
            stdscr.addstr(flow_y, x-2, "→")
            x = draw_node(x, "CONTROL", control_ok)
            stdscr.addstr(flow_y, x-2, "→")
            x = draw_node(x, "WHEELS", wheels_ok)

            # === LEFT COLUMN: ROBOT STATE ===
            draw_box(stdscr, 4, 2, 8, 45, "ROBOT STATE", curses.color_pair(4))
            stdscr.addstr(5, 4, f"Position: X={node.robot_pose['x']:.2f}, Y={node.robot_pose['y']:.2f}")
            stdscr.addstr(6, 4, f"Heading:  {node.robot_pose['theta']:.2f} rad")
            
            tf_color = curses.color_pair(1) if "OK" in node.tf_status else curses.color_pair(3)
            stdscr.addstr(7, 4, f"TF Status: {node.tf_status}", tf_color)
            
            odom_status = "OK" if (time.time() - node.last_update) < 1.0 else "LAGGING"
            odom_color = curses.color_pair(1) if odom_status == "OK" else curses.color_pair(3)
            stdscr.addstr(8, 4, f"Odom Rate: {odom_status}", odom_color)
            
            scan_color = curses.color_pair(1) if lidar_ok else curses.color_pair(3)
            stdscr.addstr(9, 4, f"Lidar Rate: {node.scan_rate:.1f} Hz", scan_color)

            # === RIGHT COLUMN: EXPLORATION ===
            draw_box(stdscr, 4, 50, 8, 45, "EXPLORATION STATUS", curses.color_pair(5))
            stdscr.addstr(5, 52, f"Frontiers Found: {node.frontiers}")
            stdscr.addstr(6, 52, f"Current Goal:    ({node.nav_goal['x']:.2f}, {node.nav_goal['y']:.2f})")
            
            # Parse debug info for cleaner display
            # Expected format: "State: IDLE | Pose: YES | Map: YES | Frontiers: 5 | Saturation: 0.85 | Status: ..."
            status_parts = node.explorer_status.split('|')
            status_text = "Unknown"
            saturation_val = 0.0
            
            for part in status_parts:
                part = part.strip()
                if part.startswith("Status:"):
                    status_text = part.replace("Status:", "").strip()
                if part.startswith("Saturation:"):
                    try:
                        saturation_val = float(part.replace("Saturation:", "").strip())
                    except:
                        pass
            
            # Display Saturation
            sat_color = curses.color_pair(1) # Green
            if saturation_val < 0.80:
                sat_color = curses.color_pair(3) # Red
            elif saturation_val < 0.90:
                sat_color = curses.color_pair(2) # Yellow
                
            stdscr.addstr(7, 52, f"Map Quality:     {saturation_val*100:.1f}%", sat_color)
            
            status_color = curses.color_pair(2) if "IDLE" in node.explorer_status else curses.color_pair(1)
            stdscr.addstr(8, 52, f"Action: {status_text}", status_color | curses.A_BOLD)

            # === BOTTOM ROW: VELOCITY & LOGS ===
            draw_box(stdscr, 13, 2, 8, 93, "VELOCITY MONITOR", curses.color_pair(4))
            
            # Velocity Bars
            def draw_bar(y, x, label, value, max_val=0.5):
                bars = int((abs(value) / max_val) * 20)
                bars = min(bars, 20)
                bar_str = "█" * bars
                color = curses.color_pair(1) if value > 0 else curses.color_pair(3)
                stdscr.addstr(y, x, f"{label}: {value:+.2f} ", curses.A_BOLD)
                stdscr.addstr(y, x+15, f"[{bar_str:<20}]", color)

            draw_bar(14, 4, "Nav2 Cmd", node.cmd_vel_nav['linear'])
            draw_bar(15, 4, "Final Cmd", node.cmd_vel['linear'])
            draw_bar(16, 4, "Actual Vel", node.odom_vel['linear'])
            
            stdscr.addstr(14, 50, f"Ang: {node.cmd_vel_nav['angular']:+.2f} rad/s")
            stdscr.addstr(15, 50, f"Ang: {node.cmd_vel['angular']:+.2f} rad/s")
            stdscr.addstr(16, 50, f"Ang: {node.odom_vel['angular']:+.2f} rad/s")

            # === LOG WINDOW ===
            stdscr.addstr(22, 2, "LATEST LOG:", curses.A_BOLD)
            stdscr.addstr(22, 14, f"{node.last_log[:80]}", curses.color_pair(2))

            # Footer
            stdscr.addstr(height - 1, 2, "Press Ctrl+C to exit", curses.A_DIM)

        except curses.error:
            pass

        stdscr.refresh()
        
        # Handle input
        try:
            c = stdscr.getch()
            if c == ord('q'):
                break
        except:
            pass
            
        rclpy.spin_once(node, timeout_sec=0.1)

def main():
    rclpy.init()
    node = SystemDashboard()
    try:
        curses.wrapper(draw_dashboard, node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
