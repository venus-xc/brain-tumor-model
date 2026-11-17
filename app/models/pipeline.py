"""Unified Multi-Task Inference Pipeline.
Supports:
1. Classifiers:
   - "effb0": EfficientNet-B0 (transfer learning) [default]
   - "secnn": SE-CNN (Squeeze-and-Excitation CNN)
   - "cnn":   Custom CNN (Baseline 4-stage CNN)
   - "svm":   HOG + SVM (Classical ML baseline)
2. Segmenters:
   - "attunet": Attention U-Net [default]
   - "unet":    Biomedical U-Net
3. Explainable AI (XAI):
   - Grad-CAM and Grad-CAM++
   - Attention Gate activation maps (Attention U-Net)
4. Quantitative 2D planar morphometrics:
   - Area (mm² and cm²), d1 (mm), d2 (mm), product (mm²)
   - Zero hardcoded metrics.
"""
import io
import os
from pathlib import Path
from typing import Dict, Optional, Tuple, Union
import cv2
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F

from app.config import (
    CLASS_NAMES,
    CLASS_DESCRIPTIONS,
    WEIGHTS_DIR,
    PROJECT_ROOT,
    ACADEMIC_DISCLAIMER,
)
from app.models.cnn import BrainCNN
from app.models.efficientnet import build_efficientnet_b0
from app.models.classical import HOGSVMClassifier
from app.models.unet import UNet
from app.models.attention_unet import AttentionUNet
from app.models.gradcam import GradCAM
from app.models.gradcam_plus_plus import GradCAMPlusPlus
from app.services.preprocessor import MedicalImagePreprocessor
from app.services.quantitative import QuantitativeAnalyzer

MODEL_DISPLAY_NAMES = {
    "svm": "HOG + SVM",
    "cnn": "Custom CNN",
    "secnn": "SE-CNN",
    "effb0": "EfficientNet-B0 (transfer learning)",
}

SEG_DISPLAY_NAMES = {
    "unet": "U-Net",
    "attunet": "Attention U-Net",
}


def select_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


class BrainTumorInferencePipeline:
    """Unified inference engine managing classifiers, segmenters, XAI, and quantitative metrics."""

    def __init__(self, device: Optional[torch.device] = None):
        self.device = device or select_device()
        self.preprocessor = MedicalImagePreprocessor()

        # Weight file paths
        self.weights = {
            "effb0": Path(WEIGHTS_DIR) / "effb0_clean.pth",
            "secnn": Path(WEIGHTS_DIR) / "secnn_clean.pth",
            "cnn": Path(WEIGHTS_DIR) / "cnn_clean.pth",
            "svm": Path(WEIGHTS_DIR) / "hog_svm.joblib",
            "unet": Path(WEIGHTS_DIR) / "unet.pth",
            "attunet": Path(WEIGHTS_DIR) / "attunet.pth",
        }
        # Backward compatibility fallback for attunet
        if not self.weights["attunet"].exists() and (Path(WEIGHTS_DIR) / "att_unet.pth").exists():
            self.weights["attunet"] = Path(WEIGHTS_DIR) / "att_unet.pth"

        # Model cache
        self.models: Dict[str, object] = {}
        self._load_available_models()

    def _load_available_models(self):
        """Loads available model weights into memory; missing weights are loaded lazily or flagged."""
        # 1. HOG + SVM
        if self.weights["svm"].exists():
            try:
                svm_model = HOGSVMClassifier(str(self.weights["svm"]))
                self.models["svm"] = svm_model
            except Exception as e:
                print(f"Warning: Failed to load HOG+SVM weights: {e}")

        # 2. Custom CNN
        if self.weights["cnn"].exists():
            try:
                cnn_model = BrainCNN(n_classes=4, se=False, in_ch=1).to(self.device)
                cnn_model.load_state_dict(torch.load(self.weights["cnn"], map_location=self.device))
                cnn_model.eval()
                self.models["cnn"] = cnn_model
            except Exception as e:
                print(f"Warning: Failed to load Custom CNN weights: {e}")

        # 3. SE-CNN
        if self.weights["secnn"].exists():
            try:
                secnn_model = BrainCNN(n_classes=4, se=True, in_ch=1).to(self.device)
                secnn_model.load_state_dict(torch.load(self.weights["secnn"], map_location=self.device))
                secnn_model.eval()
                self.models["secnn"] = secnn_model
            except Exception as e:
                print(f"Warning: Failed to load SE-CNN weights: {e}")

        # 4. EfficientNet-B0
        if self.weights["effb0"].exists():
            try:
                eff_model = build_efficientnet_b0(n_classes=4, pretrained=False).to(self.device)
                eff_model.load_state_dict(torch.load(self.weights["effb0"], map_location=self.device))
                eff_model.eval()
                self.models["effb0"] = eff_model
            except Exception as e:
                print(f"Warning: Failed to load EfficientNet-B0 weights: {e}")

        # 5. U-Net
        if self.weights["unet"].exists():
            try:
                unet_model = UNet(in_channels=1, out_channels=1).to(self.device)
                state = torch.load(self.weights["unet"], map_location=self.device)
                if "inc.double_conv.0.weight" in state and state["inc.double_conv.0.weight"].shape[1] == 3:
                    state["inc.double_conv.0.weight"] = state["inc.double_conv.0.weight"].mean(dim=1, keepdim=True)
                unet_model.load_state_dict(state)
                unet_model.eval()
                self.models["unet"] = unet_model
            except Exception as e:
                print(f"Warning: Failed to load U-Net weights: {e}")

        # 6. Attention U-Net
        att_path = self.weights["attunet"]
        if att_path.exists():
            try:
                att_model = AttentionUNet(in_channels=1, out_channels=1).to(self.device)
                state = torch.load(att_path, map_location=self.device)
                if "conv1.conv.0.weight" in state and state["conv1.conv.0.weight"].shape[1] == 3:
                    state["conv1.conv.0.weight"] = state["conv1.conv.0.weight"].mean(dim=1, keepdim=True)
                att_model.load_state_dict(state)
                att_model.eval()
                self.models["attunet"] = att_model
            except Exception as e:
                print(f"Warning: Failed to load Attention U-Net weights: {e}")

    def get_loaded_models(self) -> Dict[str, bool]:
        """Returns the readiness status of each supported architecture."""
        return {
            "classifiers": {k: (k in self.models) for k in ["effb0", "secnn", "cnn", "svm"]},
            "segmenters": {k: (k in self.models) for k in ["attunet", "unet"]},
            "device": self.device.type,
        }

    def _ensure_model(self, key: str):
        """Ensures the specified model is loaded; raises FileNotFoundError/RuntimeError if missing."""
        if key not in self.models:
            path = self.weights.get(key)
            if path is None or not path.exists():
                raise FileNotFoundError(
                    f"Model weights for '{key}' not found at {path}. Train the model before inference."
                )
            # Re-attempt load
            self._load_available_models()
            if key not in self.models:
                raise RuntimeError(f"Could not load weights for model '{key}' from {path}.")
        return self.models[key]

    def run_full_inference(
        self,
        file_source,
        classifier: str = "effb0",
        seg_architecture: str = "attunet",
        mask_threshold: float = 0.5,
        gradcam_alpha: float = 0.45,
        pixel_spacing_mm: Optional[Union[float, Tuple[float, float]]] = None,
        spacing_source: Optional[str] = None,
    ) -> dict:
        """Executes end-to-end inference for a given MRI scan slice."""
        classifier_key = classifier.lower()
        if classifier_key not in MODEL_DISPLAY_NAMES:
            classifier_key = "effb0"

        seg_key = seg_architecture.lower()
        if seg_key not in SEG_DISPLAY_NAMES:
            seg_key = "attunet"

        # Load image
        pil_orig = self.preprocessor.load_image(file_source)
        gray_pil = pil_orig.convert("L")
        gray_np = np.array(gray_pil)
        orig_w, orig_h = pil_orig.size

        # -------------------------------------------------------------
        # 1. Classification
        # -------------------------------------------------------------
        cls_model = self._ensure_model(classifier_key)

        if classifier_key == "svm":
            probs = cls_model.predict_proba(gray_np)
            gradcam_tensor = None
        elif classifier_key == "effb0":
            # 160x160 RGB, ImageNet normalized
            g160 = cv2.resize(gray_np, (160, 160), interpolation=cv2.INTER_AREA)
            t = torch.from_numpy(g160).float().div(255.0).unsqueeze(0).unsqueeze(0)
            t = t.repeat(1, 3, 1, 1)
            mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
            std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
            t = (t - mean) / std
            gradcam_tensor = t.to(self.device)
            with torch.no_grad():
                logits = cls_model(gradcam_tensor)
                probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
        else:
            # cnn or secnn: 128x128 1-ch, (t - 0.5) / 0.25
            g128 = cv2.resize(gray_np, (128, 128), interpolation=cv2.INTER_AREA)
            t = torch.from_numpy(g128).float().div(255.0).unsqueeze(0).unsqueeze(0)
            t = (t - 0.5) / 0.25
            gradcam_tensor = t.to(self.device)
            with torch.no_grad():
                logits = cls_model(gradcam_tensor)
                probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

        pred_idx = int(np.argmax(probs))
        pred_label = CLASS_NAMES[pred_idx]
        pred_conf = float(probs[pred_idx])
        is_tumor = (pred_idx != 0)

        distribution = {
            CLASS_NAMES[i]: round(float(probs[i]) * 100.0, 2)
            for i in range(len(CLASS_NAMES))
        }

        # -------------------------------------------------------------
        # 2. Segmentation
        # -------------------------------------------------------------
        seg_model = self._ensure_model(seg_key)
        # 256x256 grayscale, [0, 1]
        g256 = cv2.resize(gray_np, (256, 256), interpolation=cv2.INTER_AREA)
        t_seg = torch.from_numpy(g256).float().div(255.0).unsqueeze(0).unsqueeze(0).to(self.device)

        with torch.no_grad():
            seg_logits = seg_model(t_seg, return_logits=True)
            prob_map_256 = torch.sigmoid(seg_logits).cpu().numpy()[0, 0]

        # Resize probability map back to original image size
        prob_map_orig = cv2.resize(prob_map_256, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)

        if not is_tumor:
            # If the classifier predicts No tumor, suppress background false-positive noise
            prob_map_orig = prob_map_orig * 0.05

        binary_mask = (prob_map_orig >= mask_threshold).astype(np.float32)

        # -------------------------------------------------------------
        # 3. Explainable AI (Grad-CAM & Grad-CAM++)
        # -------------------------------------------------------------
        if gradcam_tensor is not None:
            # Standard Grad-CAM
            try:
                gcam = GradCAM(cls_model)
                hm_cam = gcam.generate_heatmap(gradcam_tensor, target_class=pred_idx)
                gradcam_overlay = GradCAM.overlay_heatmap(pil_orig, hm_cam, alpha=gradcam_alpha, colormap_name="jet")
            except Exception as e:
                print(f"Warning: Grad-CAM failed: {e}")
                gradcam_overlay = pil_orig.copy()

            # Grad-CAM++
            try:
                gcam_pp = GradCAMPlusPlus(cls_model)
                hm_cam_pp = gcam_pp.generate_heatmap(gradcam_tensor, target_class=pred_idx)
                gradcam_pp_overlay = GradCAMPlusPlus.overlay_heatmap(pil_orig, hm_cam_pp, alpha=gradcam_alpha, colormap_name="inferno")
            except Exception as e:
                print(f"Warning: Grad-CAM++ failed: {e}")
                gradcam_pp_overlay = pil_orig.copy()
        else:
            # Classical ML (HOG+SVM): provide HOG feature visualization as interpretability
            feat_img = cls_model.get_hog_visualization(gray_np)
            gradcam_overlay = Image.fromarray(feat_img).convert("RGB").resize((orig_w, orig_h))
            gradcam_pp_overlay = gradcam_overlay

        # Attention Gate Focus Map (for Attention U-Net)
        att_gate_overlay = None
        if seg_key == "attunet" and hasattr(seg_model, "latest_attention_maps") and seg_model.latest_attention_maps:
            if "ag1" in seg_model.latest_attention_maps:
                ag_tensor = seg_model.latest_attention_maps["ag1"].squeeze().cpu().numpy()
                if ag_tensor.ndim == 2:
                    ag_norm = (ag_tensor - ag_tensor.min()) / (ag_tensor.max() - ag_tensor.min() + 1e-8)
                    att_gate_overlay = GradCAM.overlay_heatmap(pil_orig, ag_norm, alpha=0.5, colormap_name="magma")
        if att_gate_overlay is None:
            att_gate_overlay = gradcam_pp_overlay

        # -------------------------------------------------------------
        # 4. Delineation / Segmentation Overlay
        # -------------------------------------------------------------
        mask_rgba = np.zeros((orig_h, orig_w, 4), dtype=np.uint8)
        mask_bool = binary_mask > 0.5
        mask_rgba[mask_bool] = [14, 165, 233, 140]  # Translucent Sky Blue

        # Red boundary contour
        from scipy import ndimage
        eroded = ndimage.binary_erosion(mask_bool)
        edge = mask_bool ^ eroded
        mask_rgba[edge] = [239, 68, 68, 240]

        mask_overlay_pil = Image.fromarray(mask_rgba, mode="RGBA")
        seg_composite = pil_orig.copy().convert("RGBA")
        seg_composite.paste(mask_overlay_pil, (0, 0), mask_overlay_pil)

        # -------------------------------------------------------------
        # 5. Quantitative 2D Measurements (No 3D / No volume)
        # -------------------------------------------------------------
        analyzer = QuantitativeAnalyzer(pixel_spacing=pixel_spacing_mm, spacing_source=spacing_source)
        morphometrics = analyzer.compute_morphometrics(binary_mask, gray_np)
        morphometrics["tumor_detected"] = is_tumor and morphometrics["tumor_detected"]

        return {
            "prediction": {
                "class_index": pred_idx,
                "label": pred_label,
                "confidence_percent": round(pred_conf * 100.0, 2),
                "is_tumor_detected": is_tumor,
                "clinical_description": CLASS_DESCRIPTIONS.get(pred_label, ""),
                "distribution": distribution,
                "model_name": MODEL_DISPLAY_NAMES.get(classifier_key, classifier_key),
                "classifier_key": classifier_key,
            },
            "segmentation": {
                "architecture_used": SEG_DISPLAY_NAMES.get(seg_key, seg_key),
                "seg_key": seg_key,
                "threshold_used": mask_threshold,
                "pixel_count": int(np.sum(binary_mask)),
                "raw_mask": binary_mask.tolist(),
                "prob_map": prob_map_orig.tolist(),
            },
            "quantitative_metrics": morphometrics,
            "visualizations": {
                "original_base64": MedicalImagePreprocessor.pil_to_base64(pil_orig),
                "gradcam_base64": MedicalImagePreprocessor.pil_to_base64(gradcam_overlay),
                "gradcam_pp_base64": MedicalImagePreprocessor.pil_to_base64(gradcam_pp_overlay),
                "attention_gate_base64": MedicalImagePreprocessor.pil_to_base64(att_gate_overlay),
                "segmentation_overlay_base64": MedicalImagePreprocessor.pil_to_base64(seg_composite.convert("RGB")),
                "mask_base64": MedicalImagePreprocessor.pil_to_base64(Image.fromarray((binary_mask * 255).astype(np.uint8))),
            },
            "disclaimer": ACADEMIC_DISCLAIMER,
        }
