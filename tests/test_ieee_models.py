import pytest
import torch
from app.models.attention_unet import AttentionUNet, AttentionGate
from app.models.cnn import BrainCNN, SEBlock


def test_attention_gate_module():
    ag = AttentionGate(F_g=64, F_l=64, F_int=32)
    g = torch.randn(2, 64, 28, 28)
    x = torch.randn(2, 64, 28, 28)
    out, alpha = ag(g, x)
    assert out.shape == x.shape, f"Expected {x.shape}, got {out.shape}"
    assert alpha.shape == (2, 1, 28, 28)
    assert (alpha >= 0.0).all() and (alpha <= 1.0).all(), "Attention coefficients must be bounded in [0, 1]"


def test_attention_unet_architecture():
    model = AttentionUNet(in_channels=1, out_channels=1)
    x = torch.randn(2, 1, 256, 256)
    out = model(x)
    assert out.shape == (2, 1, 256, 256)
    assert (out >= 0.0).all() and (out <= 1.0).all()
    assert hasattr(model, "latest_attention_maps")
    assert "ag1" in model.latest_attention_maps


def test_se_block_and_secnn():
    se = SEBlock(c=64, r=8)
    x = torch.randn(2, 64, 28, 28)
    out = se(x)
    assert out.shape == x.shape

    classifier = BrainCNN(n_classes=4, se=True, in_ch=1)
    dummy_input = torch.randn(2, 1, 128, 128)
    logits = classifier(dummy_input)
    assert logits.shape == (2, 4)
