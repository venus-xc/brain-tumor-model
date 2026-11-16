import pytest
import torch
import numpy as np
from app.models.classifier import BrainTumorClassifier
from app.models.unet import UNet
from app.models.gradcam import GradCAM

def test_classifier_architecture():
    model = BrainTumorClassifier(num_classes=4, in_channels=3)
    dummy_input = torch.randn(2, 3, 224, 224)
    logits = model(dummy_input)
    assert logits.shape == (2, 4), f"Expected shape (2, 4), got {logits.shape}"
    
    probs = model.predict_probabilities(dummy_input)
    assert probs.shape == (2, 4)
    assert torch.allclose(probs.sum(dim=1), torch.ones(2), atol=1e-5)

def test_unet_segmentation_architecture():
    model = UNet(in_channels=3, out_channels=1)
    dummy_input = torch.randn(2, 3, 224, 224)
    pred = model(dummy_input)
    assert pred.shape == (2, 1, 224, 224), f"Expected shape (2, 1, 224, 224), got {pred.shape}"
    assert (pred >= 0.0).all() and (pred <= 1.0).all(), "U-Net predictions must be bounded in [0, 1]"

def test_gradcam_hook_and_generation():
    model = BrainTumorClassifier(num_classes=4, in_channels=3)
    gradcam = GradCAM(model, model.last_conv_layer)
    dummy_input = torch.randn(1, 3, 224, 224)
    heatmap, target_class = gradcam.generate_heatmap(dummy_input)
    assert heatmap.shape == (224, 224), f"Expected (224, 224), got {heatmap.shape}"
    assert heatmap.min() >= 0.0 and heatmap.max() <= 1.0, "GradCAM heatmap values must be normalized to [0, 1]"
