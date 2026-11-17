"""EfficientNet-B0 transfer learning architecture for 4-class brain tumor classification.
Display name: "EfficientNet-B0 (transfer learning)"
"""
import os
import torch
import torch.nn as nn
import timm

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_EFFB0_WEIGHTS = os.path.join(PROJECT_ROOT, "weights", "effb0.pth")
OFFLINE_URL = "https://github.com/rwightman/pytorch-image-models/releases/download/v0.1-weights/efficientnet_b0_ra-3dd342df.pth"


def build_efficientnet_b0(n_classes: int = 4, weights: str = None, pretrained: bool = True) -> nn.Module:
    """Builds EfficientNet-B0 classifier.
    Loads ImageNet weights from timm or local release file, then replaces classifier head with n_classes.
    """
    if weights is None and os.path.exists(DEFAULT_EFFB0_WEIGHTS):
        weights = DEFAULT_EFFB0_WEIGHTS

    m = None
    if weights and os.path.exists(weights):
        m = timm.create_model("efficientnet_b0", pretrained=False, num_classes=1000)
        sd = torch.load(weights, map_location="cpu")
        m.load_state_dict(sd, strict=False)
    else:
        try:
            m = timm.create_model("efficientnet_b0", pretrained=pretrained, num_classes=1000)
        except Exception:
            m = timm.create_model("efficientnet_b0", pretrained=False, num_classes=1000)
            if weights and os.path.exists(weights):
                sd = torch.load(weights, map_location="cpu")
                m.load_state_dict(sd, strict=False)

    m.reset_classifier(n_classes)
    return m


def efficientnet_b0(n_classes: int = 4, weights: str = None) -> nn.Module:
    """Matches reference_code/exp/models.py signature."""
    return build_efficientnet_b0(n_classes=n_classes, weights=weights)
