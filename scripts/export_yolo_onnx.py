#!/usr/bin/env python3
import argparse
from ultralytics import YOLO
import sys
import os

def export_model(model_path, format='onnx'):
    """
    Export a YOLOv8 model to the specified format.
    """
    print(f"🚀 Loading model: {model_path}")
    try:
        model = YOLO(model_path)
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return False

    print(f"🔄 Exporting to {format}...")
    try:
        # Export the model
        # opset=12 is widely supported by ONNX Runtime
        path = model.export(format=format, opset=12, dynamic=False) 
        print(f"✅ Export success! Saved to: {path}")
        return True
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export YOLOv8 models to ONNX")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Path to .pt model file")
    args = parser.parse_args()

    if not os.path.exists(args.model):
        # Try to download if it doesn't exist (basic yolov8n.pt)
        if args.model == "yolov8n.pt":
            print("⚠️ Model not found locally. Ultralytics will attempt to download it.")
        else:
            print(f"❌ Model file not found: {args.model}")
            sys.exit(1)

    success = export_model(args.model)
    if not success:
        sys.exit(1)
