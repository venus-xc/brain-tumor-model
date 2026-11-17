import os
import json
import pytest
import torch
from app.models.cnn import BrainCNN
from app.models.efficientnet import build_efficientnet_b0
from app.models.unet import UNet
from app.models.attention_unet import AttentionUNet
from app.models.classical import extract_hog_features


def test_brain_cnn_custom():
    model = BrainCNN(n_classes=4, se=False, in_ch=1)
    x = torch.randn(2, 1, 128, 128)
    out = model(x)
    assert out.shape == (2, 4)
    params = sum(p.numel() for p in model.parameters())
    assert params == 1206052


def test_brain_cnn_secnn():
    model = BrainCNN(n_classes=4, se=True, in_ch=1)
    x = torch.randn(2, 1, 128, 128)
    out = model(x)
    assert out.shape == (2, 4)
    params = sum(p.numel() for p in model.parameters())
    assert params == 1228352


def test_efficientnet_b0():
    model = build_efficientnet_b0(n_classes=4, pretrained=False)
    x = torch.randn(2, 3, 160, 160)
    out = model(x)
    assert out.shape == (2, 4)
    params = sum(p.numel() for p in model.parameters())
    assert params == 4012672


def test_unet_output_shape():
    model = UNet(in_channels=1, out_channels=1)
    x = torch.randn(2, 1, 256, 256)
    out = model(x)
    assert out.shape == (2, 1, 256, 256)
    assert (out >= 0.0).all() and (out <= 1.0).all()


def test_attention_unet_output_shape():
    model = AttentionUNet(in_channels=1, out_channels=1)
    x = torch.randn(2, 1, 256, 256)
    out = model(x)
    assert out.shape == (2, 1, 256, 256)
    assert (out >= 0.0).all() and (out <= 1.0).all()


def test_hog_feature_dimension():
    import numpy as np
    dummy_img = (np.random.rand(128, 128) * 255).astype(np.uint8)
    feat = extract_hog_features(dummy_img, size=128)
    assert feat.shape == (1764,)
