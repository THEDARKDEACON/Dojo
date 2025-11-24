#!/usr/bin/env python3
import subprocess
import time
import os

# Configuration
ROBOT_IP = "192.168.0.100" # Example IP
ROBOT_USER = "husarion"
DATA_DIR_ROBOT = "/home/husarion/rosbags/room_1"
DATA_DIR_LOCAL = "./data/room_1"

def run_remote_command(command):
    """Runs a command on the robot via SSH."""
    ssh_cmd = f"ssh {ROBOT_USER}@{ROBOT_IP} '{command}'"
    print(f"Executing: {ssh_cmd}")
    # subprocess.run(ssh_cmd, shell=True) # Uncomment to run

def trigger_survey():
    print("Stage 1: Triggering Robot Survey...")
    # Call the ROS 2 service/action on the robot
    # run_remote_command("ros2 run dojo_navigation survey_planner")
    time.sleep(5) # Simulate work
    print("Survey Complete.")

def transfer_data():
    print("Stage 2: Transferring Data...")
    if not os.path.exists(DATA_DIR_LOCAL):
        os.makedirs(DATA_DIR_LOCAL)
    
    rsync_cmd = f"rsync -avz {ROBOT_USER}@{ROBOT_IP}:{DATA_DIR_ROBOT} {DATA_DIR_LOCAL}"
    print(f"Executing: {rsync_cmd}")
    # subprocess.run(rsync_cmd, shell=True)
    print("Transfer Complete.")

def train_gsplat():
    print("Stage 3: Training Gaussian Splat...")
    # Resize images first
    # subprocess.run("mogrify -resize 848x480 ...", shell=True)
    
    # Launch gsplat
    print("Launching gsplat training...")
    # subprocess.run("python3 train.py ...", shell=True)
    print("Training Complete.")

def main():
    print("Starting Splat Pipeline Manager...")
    
    # Room 1 Workflow
    trigger_survey()
    transfer_data()
    train_gsplat()
    
    print("Pipeline Finished for Room 1. Ready for Room 2.")

if __name__ == "__main__":
    main()
