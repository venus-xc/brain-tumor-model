import pytest
import torch
from app.models.attention_unet import AttentionUNet, AttentionGate
from app.models.se_resnet import SEResNetClassifier, SqueezeExcitation
from app.models.gradcam_plus_plus import GradCAMPlusPlus

def test_attention_gate_module():
    # Test Attention Gate: Gating signal [B, 64, 28, 28], Skip [B, 64, 28, 28]
    ag = AttentionGate(F_g=64, F_l=64, F_int=32)
    g = torch.randn(2, 64, 28, 28)
    x = torch.randn(2, 64, 28, 28)
    out, alpha = ag(g, x)
    assert out.shape == x.shape, f"Expected {x.shape}, got {out.shape}"
    assert alpha.shape == (2, 1, 28, 28)
    assert (alpha >= 0.0).all() and (alpha <= 1.0).all(), "Attention coefficients must be bounded in [0, 1]"

def test_attention_unet_architecture():
    model = AttentionUNet(in_channels=3, out_channels=1)
    x = torch.randn(2, 3, 224, 224)
    out = model(x)
    assert out.shape == (2, 1, 224, 224)
    assert (out >= 0.0).all() and (out <= 1.0).all()
    assert hasattr(model, 'latest_attention_maps')
    assert "ag1" in model.latest_attention_maps

def test_se_block_and_resnet():
    se = SqueezeExcitation(channels=64, reduction=16)
    x = torch.randn(2, 64, 28, 28)
    out = se(x)
    assert out.shape == x.shape

    classifier = SEResNetClassifier(num_classes=4, in_channels=3)
    dummy_input = torch.randn(2, 3, 224, 224)
    logits = classifier(dummy_input)
    assert logits.shape == (2, 4)
    probs = classifier.predict_probabilities(dummy_input)
    assert torch.allclose(probs.sum(dim=1), torch.ones(2), atol=1e-5)

def test_gradcam_plus_plus():
    classifier = SEResNetClassifier(num_classes=4, in_channels=3)
    gradcam_pp = GradCAMPlusPlus(classifier, classifier.last_conv_layer)
    dummy_input = torch.randn(1, 3, 224, 224)
    heatmap, pred_class = gradcam_pp.generate_heatmap(dummy_input)
    assert heatmap.shape == (224, 224)
    assert heatmap.min() >= 0.0 and heatmap.max() <= 1.0
