#!/usr/bin/env python3
"""
Script to update imports and package structure for robot_perception.
"""
import os
import re
from pathlib import Path

# Define the package root and source directories
PACKAGE_ROOT = Path(__file__).parent.absolute()
SRC_DIR = PACKAGE_ROOT / "robot_perception"
NODES_DIR = SRC_DIR / "nodes"
UTILS_DIR = SRC_DIR / "utils"

# Create necessary directories
NODES_DIR.mkdir(exist_ok=True)
UTILS_DIR.mkdir(exist_ok=True)

# Create __init__.py files if they don't exist
for init_file in [SRC_DIR / "__init__.py", 
                 NODES_DIR / "__init__.py", 
                 UTILS_DIR / "__init__.py"]:
    if not init_file.exists():
        init_file.touch()

# Define file mappings (old_path -> new_path)
FILE_MAPPINGS = {
    SRC_DIR / "camera_processor.py": NODES_DIR / "camera_processor.py",
    SRC_DIR / "object_detector.py": NODES_DIR / "object_detector.py",
    SRC_DIR / "lidar_processor.py": NODES_DIR / "lidar_processor.py",
    SRC_DIR / "perception_integrator.py": NODES_DIR / "perception_integrator.py"
}

# Update import statements in files
IMPORT_UPDATES = {
    # Update imports from robot_perception to robot_perception.nodes
    r'from robot_perception\.(?!nodes|utils)(\w+)': r'from robot_perception.nodes.\1',
    # Update relative imports
    r'from \.(?!nodes|utils)(\w+)': r'from .nodes.\1',
}

def update_imports_in_file(file_path):
    """Update import statements in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        updated = False
        for pattern, replacement in IMPORT_UPDATES.items():
            new_content, num_subs = re.subn(pattern, replacement, content, flags=re.MULTILINE)
            if num_subs > 0:
                content = new_content
                updated = True
        
        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated imports in {file_path}")
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def main():
    # Move files to their new locations
    for src, dst in FILE_MAPPINGS.items():
        if src.exists() and not dst.exists():
            src.rename(dst)
            print(f"Moved {src} -> {dst}")
    
    # Update imports in all Python files
    for root, _, files in os.walk(SRC_DIR):
        for file in files:
            if file.endswith('.py'):
                update_imports_in_file(Path(root) / file)
    
    print("Import updates completed successfully!")

if __name__ == "__main__":
    main()
