import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
import matplotlib

class GradCAMPlusPlus:
    """
    Grad-CAM++: Generalized Gradient-Based Visual Explanations for Deep Convolutional Networks.
    IEEE Reference: Chattopadhyay et al., IEEE Transactions on Image Processing (TIP), 2018.
    
    Provides superior object localization and captures multi-focal lesions by using
    weighted combinations of positive partial gradients (second- and third-order approximations).
    """
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        self._register_hooks()

    def _register_hooks(self):
        def forward_hook(module, input, output):
            self.activations = output

        def backward_hook(module, grad_in, grad_out):
            self.gradients = grad_out[0]

        self.target_layer.register_forward_hook(forward_hook)
        self.target_layer.register_full_backward_hook(backward_hook)

    def generate_heatmap(self, input_tensor, target_class=None):
        """
        Computes Grad-CAM++ saliency heatmap normalized to [0, 1].
        input_tensor: [1, C, H, W]
        """
        self.model.eval()
        self.model.zero_grad()
        
        # Forward pass
        logits = self.model(input_tensor)
        
        if target_class is None:
            target_class = torch.argmax(logits, dim=1).item()
            
        score = logits[0, target_class]
        
        # Compute first gradients
        self.model.zero_grad()
        score.backward(retain_graph=True)
        
        grads_1 = self.gradients  # [1, C, H, W]
        acts = self.activations   # [1, C, H, W]
        
        # Grad-CAM++ formulation using second and third derivative approximations:
        # grads_2 ~ grads_1^2, grads_3 ~ grads_1^3
        grads_power_2 = grads_1.pow(2)
        grads_power_3 = grads_power_2 * grads_1
        
        # Denominator sum: 2 * g^2 + sum(A * g^3)
        sum_acts_grads3 = torch.sum(acts * grads_power_3, dim=(2, 3), keepdim=True)
        eps = 1e-7
        denom = 2.0 * grads_power_2 + sum_acts_grads3
        denom = torch.where(denom != 0.0, denom, torch.ones_like(denom) * eps)
        
        # Alpha coefficients
        alphas = grads_power_2 / denom
        
        # Relu on gradients
        rel_grads = F.relu(grads_1)
        
        # Weights w_k^c
        weights = torch.sum(alphas * rel_grads, dim=(2, 3), keepdim=True)
        
        # Heatmap = sum_k (w_k^c * A^k)
        cam = torch.sum(weights * acts, dim=1, keepdim=True)
        cam = F.relu(cam)
        
        # Interpolate to input resolution
        h, w = input_tensor.shape[2], input_tensor.shape[3]
        cam = F.interpolate(cam, size=(h, w), mode="bilinear", align_corners=False)
        cam = cam.squeeze().detach().cpu().numpy()
        
        # Normalize
        cam_min, cam_max = cam.min(), cam.max()
        if cam_max - cam_min > 1e-8:
            cam = (cam - cam_min) / (cam_max - cam_min)
        else:
            cam = np.zeros_like(cam)
            
        return cam, target_class

    @staticmethod
    def overlay_heatmap(original_image: Image.Image, heatmap: np.ndarray, alpha: float = 0.5, colormap_name: str = "inferno") -> Image.Image:
        """
        Blends heatmap on original MRI scan using Matplotlib colormaps.
        """
        orig_w, orig_h = original_image.size
        if heatmap.shape[0] != orig_h or heatmap.shape[1] != orig_w:
            h_img = Image.fromarray((heatmap * 255).astype(np.uint8))
            h_img = h_img.resize((orig_w, orig_h), Image.Resampling.BILINEAR)
            heatmap = np.array(h_img) / 255.0

        try:
            cmap = matplotlib.colormaps[colormap_name]
        except Exception:
            import matplotlib.cm as cm
            cmap = cm.get_cmap(colormap_name)

        colored_heatmap = (cmap(heatmap)[:, :, :3] * 255).astype(np.uint8)
        orig_np = np.array(original_image.convert("RGB"))
        blended = (orig_np * (1.0 - alpha) + colored_heatmap * alpha).astype(np.uint8)
        return Image.fromarray(blended)
