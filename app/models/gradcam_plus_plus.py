"""Explainable AI (XAI) Engine: Grad-CAM++ (Chattopadhay et al., IEEE ISM).
Higher-order gradient weighting matching reference_code/exp/gradcam.py.
Supports EfficientNet-B0 and BrainCNN architectures.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import cv2
from app.models.gradcam import get_target_conv_layer


class GradCAMPlusPlus:
    """Higher-order Grad-CAM++ engine."""

    def __init__(self, model: nn.Module, target_layer: nn.Module = None):
        self.model = model
        self.target_layer = target_layer or get_target_conv_layer(model)
        self.activations = None
        self._hook = self.target_layer.register_forward_hook(self._forward_hook)

    def _forward_hook(self, module, inp, out):
        self.activations = out

    def generate_heatmap(self, input_tensor: torch.Tensor, target_class: int = None) -> np.ndarray:
        """Generates 2D Grad-CAM++ heatmap in [0, 1] matching input shape [H, W]."""
        self.model.eval()
        self.activations = None

        out = self.model(input_tensor)
        if target_class is None:
            target_class = int(out.argmax(1).item())

        A = self.activations
        score = out[0, target_class]
        grads = torch.autograd.grad(score, A, retain_graph=True)[0][0]
        A = A[0].detach()

        # Grad-CAM++ (exp-score closed form): w_ij = g^2 / (2 g^2 + sum_ab A_ab g^3)
        g2, g3 = grads ** 2, grads ** 3
        denom = 2 * g2 + A.sum((1, 2), keepdim=True) * g3
        alpha = g2 / torch.where(denom != 0, denom, torch.ones_like(denom))
        wpp = (alpha * F.relu(grads)).sum((1, 2))
        gcpp = F.relu((wpp[:, None, None] * A).sum(0)).detach().cpu().numpy()

        h, w_in = input_tensor.shape[2], input_tensor.shape[3]
        gcpp = cv2.resize(gcpp, (w_in, h), interpolation=cv2.INTER_CUBIC)
        gcpp = np.maximum(gcpp, 0)
        max_val = gcpp.max()
        if max_val > 1e-8:
            gcpp = gcpp / max_val
        else:
            gcpp = np.zeros_like(gcpp)

        return gcpp

    @staticmethod
    def overlay_heatmap(pil_image, heatmap: np.ndarray, alpha: float = 0.45, colormap_name: str = "inferno"):
        """Overlays a 2D heatmap [0, 1] onto a PIL image with alpha blending."""
        from PIL import Image
        w, h = pil_image.size
        hm_u8 = (np.clip(heatmap, 0, 1) * 255).astype(np.uint8)
        hm_resized = cv2.resize(hm_u8, (w, h), interpolation=cv2.INTER_LINEAR)
        cm_code = cv2.COLORMAP_INFERNO
        if colormap_name.lower() == "jet":
            cm_code = cv2.COLORMAP_JET
        elif colormap_name.lower() == "magma":
            cm_code = cv2.COLORMAP_MAGMA
        color_map = cv2.applyColorMap(hm_resized, cm_code)
        color_map = cv2.cvtColor(color_map, cv2.COLOR_BGR2RGB)
        img_rgb = np.array(pil_image.convert("RGB"))
        blended = cv2.addWeighted(img_rgb, 1.0 - alpha, color_map, alpha, 0)
        return Image.fromarray(blended)

