import os
import pytest
import torch
import numpy as np
from app.models.efficientnet import build_efficientnet_b0
from app.models.gradcam import GradCAM
from app.models.gradcam_plus_plus import GradCAMPlusPlus

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGHT_PATH = os.path.join(PROJECT_ROOT, "weights", "effb0_clean.pth")


def test_gradcam_and_gradcam_plus_plus():
    if not os.path.exists(WEIGHT_PATH):
        pytest.skip("weights/effb0_clean.pth not yet available")

    model = build_efficientnet_b0(n_classes=4, pretrained=False)
    model.load_state_dict(torch.load(WEIGHT_PATH, map_location="cpu"))
    model.eval()

    gcam = GradCAM(model)
    gcam_pp = GradCAMPlusPlus(model)

    # Input tensor
    x = torch.randn(1, 3, 160, 160)
    map1 = gcam.generate_heatmap(x)
    map2 = gcam_pp.generate_heatmap(x)

    assert map1.shape == (160, 160), f"Expected (160, 160), got {map1.shape}"
    assert map2.shape == (160, 160), f"Expected (160, 160), got {map2.shape}"

    assert map1.min() >= 0.0 and map1.max() <= 1.0, "GradCAM not in [0, 1]"
    assert map2.min() >= 0.0 and map2.max() <= 1.0, "GradCAM++ not in [0, 1]"

    assert not np.allclose(map1, 0.0), "GradCAM is all zeros"
    assert not np.allclose(map2, 0.0), "GradCAM++ is all zeros"
