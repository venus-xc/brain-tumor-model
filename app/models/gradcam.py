"""Explainable AI (XAI) Engine: Gradient-weighted Class Activation Mapping (Grad-CAM).
Uses exact autograd gradients matching reference_code/exp/gradcam.py.
Supports EfficientNet-B0 and BrainCNN architectures.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import cv2


def get_target_conv_layer(model: nn.Module) -> nn.Module:
    """Finds the last convolutional layer in the feature extractor."""
    if hasattr(model, "conv_head"):
        return model.conv_head
    if hasattr(model, "features"):
        for block in reversed(model.features):
            for layer in reversed(block):
                if isinstance(layer, nn.Conv2d):
                    return layer
    last_conv = None
    for module in model.modules():
        if isinstance(module, nn.Conv2d):
            last_conv = module
    if last_conv is not None:
        return last_conv
    raise ValueError(f"Could not automatically identify last Conv2d layer in {type(model)}")


class GradCAM:
    """First-order Grad-CAM engine."""

    def __init__(self, model: nn.Module, target_layer: nn.Module = None):
        self.model = model
        self.target_layer = target_layer or get_target_conv_layer(model)
        self.activations = None
        self._hook = self.target_layer.register_forward_hook(self._forward_hook)

    def _forward_hook(self, module, inp, out):
        self.activations = out

    def generate_heatmap(self, input_tensor: torch.Tensor, target_class: int = None) -> np.ndarray:
        """Generates 2D Grad-CAM heatmap in [0, 1] matching input shape [H, W]."""
        self.model.eval()
        self.activations = None

        out = self.model(input_tensor)
        if target_class is None:
            target_class = int(out.argmax(1).item())

        A = self.activations
        score = out[0, target_class]
        grads = torch.autograd.grad(score, A, retain_graph=True)[0][0]
        A = A[0].detach()

        # Grad-CAM: alpha_k = mean_ij dY/dA ; L = ReLU(sum_k alpha_k A_k)
        w = grads.mean((1, 2))
        gc = F.relu((w[:, None, None] * A).sum(0)).detach().cpu().numpy()

        h, w_in = input_tensor.shape[2], input_tensor.shape[3]
        gc = cv2.resize(gc, (w_in, h), interpolation=cv2.INTER_CUBIC)
        gc = np.maximum(gc, 0)
        max_val = gc.max()
        if max_val > 1e-8:
            gc = gc / max_val
        else:
            gc = np.zeros_like(gc)

        return gc

    @staticmethod
    def overlay_heatmap(pil_image, heatmap: np.ndarray, alpha: float = 0.45, colormap_name: str = "jet"):
        """Overlays a 2D heatmap [0, 1] onto a PIL image with alpha blending."""
        from PIL import Image
        w, h = pil_image.size
        hm_u8 = (np.clip(heatmap, 0, 1) * 255).astype(np.uint8)
        hm_resized = cv2.resize(hm_u8, (w, h), interpolation=cv2.INTER_LINEAR)
        cm_code = cv2.COLORMAP_JET
        if colormap_name.lower() == "inferno":
            cm_code = cv2.COLORMAP_INFERNO
        elif colormap_name.lower() == "magma":
            cm_code = cv2.COLORMAP_MAGMA
        color_map = cv2.applyColorMap(hm_resized, cm_code)
        color_map = cv2.cvtColor(color_map, cv2.COLOR_BGR2RGB)
        img_rgb = np.array(pil_image.convert("RGB"))
        blended = cv2.addWeighted(img_rgb, 1.0 - alpha, color_map, alpha, 0)
        return Image.fromarray(blended)

