import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
import matplotlib.cm as cm

class GradCAM:
    """
    Explainable AI (XAI) Engine using Gradient-weighted Class Activation Mapping (Grad-CAM).
    Identifies the discriminative regions in MRI scans influencing the neural network's
    classification decisions (Glioma, Meningioma, Pituitary, Normal).
    """
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        self._register_hooks()

    def _register_hooks(self):
        def forward_hook(module, input, output):
            self.activations = output.detach()

        def backward_hook(module, grad_in, grad_out):
            self.gradients = grad_out[0].detach()

        self.target_layer.register_forward_hook(forward_hook)
        self.target_layer.register_full_backward_hook(backward_hook)

    def generate_heatmap(self, input_tensor, target_class=None):
        """
        Generates 2D Grad-CAM heatmap normalized to [0, 1].
        input_tensor: shape (1, C, H, W)
        """
        self.model.eval()
        self.model.zero_grad()
        
        # Forward pass
        logits = self.model(input_tensor)
        
        if target_class is None:
            target_class = torch.argmax(logits, dim=1).item()
        
        # Target score for backprop
        score = logits[0, target_class]
        score.backward(retain_graph=True)
        
        # Global Average Pooling of gradients (neuron importance weights)
        # gradients: (1, C, H, W)
        weights = torch.mean(self.gradients, dim=(2, 3), keepdim=True)
        
        # Weighted combination of forward activation maps
        cam = torch.sum(weights * self.activations, dim=1, keepdim=True)
        
        # Apply ReLU to retain features that positively correlate with the target class
        cam = F.relu(cam)
        
        # Upsample to match original input size
        h, w = input_tensor.shape[2], input_tensor.shape[3]
        cam = F.interpolate(cam, size=(h, w), mode="bilinear", align_corners=False)
        
        cam = cam.squeeze().cpu().numpy()
        
        # Normalize between 0 and 1
        cam_min, cam_max = cam.min(), cam.max()
        if cam_max - cam_min > 1e-8:
            cam = (cam - cam_min) / (cam_max - cam_min)
        else:
            cam = np.zeros_like(cam)
            
        return cam, target_class

    @staticmethod
    def overlay_heatmap(original_image: Image.Image, heatmap: np.ndarray, alpha: float = 0.45, colormap_name: str = "jet") -> Image.Image:
        """
        Overlays the Grad-CAM heatmap onto the original MRI scan.
        original_image: PIL Image
        heatmap: 2D numpy array [0, 1]
        alpha: Blending weight of heatmap
        colormap_name: 'jet', 'inferno', 'turbo', 'viridis'
        """
        orig_w, orig_h = original_image.size
        # Resize heatmap if dimensions don't match
        if heatmap.shape[0] != orig_h or heatmap.shape[1] != orig_w:
            h_img = Image.fromarray((heatmap * 255).astype(np.uint8))
            h_img = h_img.resize((orig_w, orig_h), Image.Resampling.BILINEAR)
            heatmap = np.array(h_img) / 255.0

        # Apply colormap
        try:
            import matplotlib
            cmap = matplotlib.colormaps[colormap_name]
        except Exception:
            cmap = cm.get_cmap(colormap_name)
        colored_heatmap = cmap(heatmap)[:, :, :3]  # Drop alpha, get RGB in [0, 1]
        colored_heatmap = (colored_heatmap * 255).astype(np.uint8)
        
        orig_np = np.array(original_image.convert("RGB"))
        
        # Blended image
        blended = (orig_np * (1.0 - alpha) + colored_heatmap * alpha).astype(np.uint8)
        return Image.fromarray(blended)
