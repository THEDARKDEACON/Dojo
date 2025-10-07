import torch
import torch.nn as nn
import torchvision.models as models
from pathlib import Path
from PIL import Image
from rdj2025_potato_disease_detection.inference_engine import PotatoDiseaseModel

# Global index-to-class mapping
IDX_TO_CLASS = {0: "Early_blight", 1: "Late_blight", 2: "Healthy"}


# Try to import timm (third-party models)
try:
    import timm
    HAS_TIMM = True
except ImportError:
    HAS_TIMM = False
    print("⚠️ timm not installed. Install with: pip install timm")

# --- Flexible loader ---
def load_model(model_path):
    state_dict = torch.load(model_path, map_location="cpu")

    # 1. Try ResNet18
    try:
        model = models.resnet18(weights=None)
        num_ftrs = model.fc.in_features
        model.fc = nn.Linear(num_ftrs, 3)
        model.load_state_dict(state_dict)
        print(f"✅ Loaded {model_path} as ResNet18")
        return model
    except Exception:
        pass

    # 2. Try torchvision MobileNetV2
    try:
        model = models.mobilenet_v2(weights=None)
        num_ftrs = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(num_ftrs, 3)
        model.load_state_dict(state_dict)
        print(f"✅ Loaded {model_path} as torchvision MobileNetV2")
        return model
    except Exception:
        pass

    # 3. Try timm MobileNetV2 (if available)
    if HAS_TIMM:
        try:
            model = timm.create_model("mobilenetv2_100", pretrained=False, num_classes=3)
            model.load_state_dict(state_dict, strict=False)  # allow partial load
            print(f"✅ Loaded {model_path} as timm MobileNetV2")
            return model
        except Exception:
            pass

    print(f"❌ Could not load {model_path}")
    return None


def predict(model, image):
    transform = PotatoDiseaseModel().transform  # reuse same preprocessing
    x = transform(image).unsqueeze(0)
    with torch.no_grad():
        outputs = model(x)
        _, preds = torch.max(outputs, 1)
    return IDX_TO_CLASS[preds.item()]


if __name__ == "__main__":
    # Ground truth
    test_images = {
        "images/early.png": "Early_blight",
        "images/late.jpg": "Late_blight",
        "images/healthy.jpg": "Healthy",
    }

    # Load all .pth models
    models_dir = Path("models")
    model_files = list(models_dir.glob("*.pth"))
    models_dict = {f.name: load_model(str(f)) for f in model_files}

    print("\nTesting all models...\n")
    correct_counts = {name: 0 for name in models_dict if models_dict[name] is not None}
    total = len(test_images)

    # Test loop
    for img_path, true_label in test_images.items():
        img = Image.open(img_path).convert("RGB")
        print(f"{img_path}:")
        print(f"  True Label : {true_label}")

        for name, model in models_dict.items():
            if model is None:
                continue
            pred = predict(model, img)
            ok = (pred == true_label)
            print(f"  {name:25s} -> {pred} {'✅' if ok else '❌'}")
            if ok:
                correct_counts[name] += 1
        print()

    # Summary
    print("Summary:")
    for name, correct in correct_counts.items():
        print(f"  {name:25s} -> {correct}/{total} correct")
