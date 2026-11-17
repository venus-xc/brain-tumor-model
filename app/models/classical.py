"""Classical ML model loader and HOG feature extraction.
Display name: "HOG + SVM"
Settings: 9 orientations, 16x16 cells, 2x2 blocks, L2-Hys block norm, 128x128 input.
Pipeline: StandardScaler -> PCA(150) -> SVC(probability=True, class_weight='balanced', random_state=42).
"""
import os
import joblib
import numpy as np
import cv2
from skimage.feature import hog

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_SVM_WEIGHTS = os.path.join(PROJECT_ROOT, "weights", "hog_svm.joblib")


def extract_hog_features(img: np.ndarray, size: int = 128, return_vis: bool = False):
    """Extracts HOG descriptor (dim=1764) from grayscale image.
    If return_vis=True, returns (features, hog_image).
    """
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    g = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)

    if return_vis:
        feat, vis = hog(
            g,
            orientations=9,
            pixels_per_cell=(16, 16),
            cells_per_block=(2, 2),
            block_norm="L2-Hys",
            visualize=True,
        )
        return feat, vis
    else:
        feat = hog(
            g,
            orientations=9,
            pixels_per_cell=(16, 16),
            cells_per_block=(2, 2),
            block_norm="L2-Hys",
            visualize=False,
        )
        return feat


class HOGSVMClassifier:
    """Wrapper around trained HOG + SVM scikit-learn pipeline."""

    def __init__(self, weights_path: str = None):
        if weights_path is None:
            weights_path = DEFAULT_SVM_WEIGHTS
        self.weights_path = weights_path
        self.pipeline = None
        if os.path.exists(weights_path):
            self.load()

    def load(self):
        self.pipeline = joblib.load(self.weights_path)

    @property
    def is_loaded(self) -> bool:
        return self.pipeline is not None

    def predict_proba(self, img: np.ndarray) -> np.ndarray:
        if self.pipeline is None:
            raise RuntimeError(f"HOG+SVM model not loaded. Missing weights at {self.weights_path}")
        feat = extract_hog_features(img, size=128, return_vis=False).reshape(1, -1)
        return self.pipeline.predict_proba(feat)[0]

    def get_hog_visualization(self, img: np.ndarray) -> np.ndarray:
        """Returns normalized [0, 255] uint8 HOG visualization image for explanation overlay."""
        _, vis = extract_hog_features(img, size=128, return_vis=True)
        vis_norm = ((vis - vis.min()) / (vis.max() - vis.min() + 1e-8) * 255.0).astype(np.uint8)
        return vis_norm
